import json
import torch
from transformers import TextStreamer
from ..config import DVE_ADAPTER_PATH, DVE_PROMPT_TEMPLATE, DVE_INSTRUCTION, DEVICE
from .base import BaseExpert

class DVE_Expert(BaseExpert):
    """
    DVE: 資料查核專家 (Schema Fix Version)
    """
    def process(self, task_data, history=[]):
        query = task_data.get("user_query", "")
        profile = task_data.get("profile_state", {})
        
        # 1. 技術障礙攔截 (Rule-based)
        tech_keywords = ["傳不上", "失敗", "格式錯誤", "太慢", "當機", "無法"]
        if any(k in query for k in tech_keywords):
            return {
                "expert": "DVE (Tech Support)",
                "response": "偵測到技術問題。請確認圖片格式為 JPG/PNG 且小於 5MB。",
                "next_step": "等待技術排除"
            }

        # 2. 準備比對資料
        # 為了不讓模型當機，我們必須「湊齊」訓練資料裡的所有欄位
        print("🛡️ DVE 啟動 AI 查核模式 (Schema Aligned)...")
        
        # [模擬 RAG]：這裡要把所有訓練資料有的 key 都補上，沒有的就填 "無"
        mock_rag_context = {
            "檔案中紀錄職業": "公立高中教師",   # 模擬歷史資料
            "上次貸款資金用途": "房屋修繕",     # (補)
            "檔案中聯絡電話": "0920-987-654",
            "歷史違約紀錄": "無",
            "檔案中服務公司名稱": "XX市立高中",
            "檔案中年薪/月薪": "60000",
            "信用報告查詢次數": "1",           # (補)
            "地址變動次數": "0"                # (補)
        }
        
        # [組建 Input]：這裡的 Key 必須跟訓練資料一模一樣！
        dve_input_data = {
            "核心識別資訊": {
                "申請人姓名": profile.get("name", "測試人員"),
                "身分證字號": profile.get("id", "A123456789")
            },
            "最新口述資訊 (Query) 擷取": {
                "職業": profile.get("job", "待業中"),  # 從 Profile 拿，沒有就填預設
                "資金用途": "週轉金",                  # (寫死) 暫時填入，之後可從對話分析
                "聯絡電話": "0912-345-678",            # (寫死) 
                "服務公司名稱": "未提供",              # (寫死)
                "月薪": str(profile.get("income", "0"))
            },
            "RAG 檢索的歷史數據 (Context) 擷取": mock_rag_context
        }
        
        input_json_str = json.dumps(dve_input_data, ensure_ascii=False)

        # 3. 呼叫 LLM (加入 Streamer 監控)
        # 設定 Streamer，讓它即時印出文字，這樣你就知道它有沒有在跑
        streamer = TextStreamer(self.llm._tokenizer, skip_prompt=True)
        
        print(f"🌊 Input JSON 已構建，長度: {len(input_json_str)} chars")
        print("🌊 開始生成 (Stream Mode)... 請看下方輸出 👇")

        # 使用 llm_utils 的底層 generate (為了傳入 streamer)
        # 這裡我們稍微繞過 get_expert_response 的封裝，直接調用以確保能看到 Stream
        
        model = self.llm._base_model
        tokenizer = self.llm._tokenizer
        
        # 載入 Adapter
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, DVE_ADAPTER_PATH)
        model.eval()

        # 格式化 Prompt
        prompt = DVE_PROMPT_TEMPLATE.format(DVE_INSTRUCTION, input_json_str)
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,            # <--- 關鍵：即時顯示
                max_new_tokens=512,
                temperature=0.1,              # DVE 需要低溫
                repetition_penalty=1.2,       # 防止鬼打牆
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 4. 解析與策略分流 (修正版：強力防鬼打牆)
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=False) # 改成 False 以便我們偵測特殊符號
        
        try:
            # === [新增] 強力切割邏輯 ===
            # 1. 如果出現結束符號，直接切斷
            if "<|end_of_text|>" in full_text:
                full_text = full_text.split("<|end_of_text|>")[0]
            
            # 2. 如果出現下一個指令的開頭，直接切斷
            if "<|begin_of_text|>" in full_text:
                full_text = full_text.split("<|begin_of_text|>")[1] # 取中間那段
                if "<|begin_of_text|>" in full_text: # 如果還有第二個
                     full_text = full_text.split("<|begin_of_text|>")[0]

            # 3. 抓取 Output 之後的 JSON
            if "### Output:" in full_text:
                generated_text = full_text.split("### Output:")[1].strip()
            else:
                generated_text = full_text

            # 4. JSON 清洗 (只抓取第一個完整的 {} 物件)
            # 這是防止後面重複出現 {"核實狀態"...} 的關鍵
            start_idx = generated_text.find("{")
            
            # 我們利用計數器來找對應的結束括號，而不是用 rfind
            # 這樣就算後面有重複的 JSON，我們也只會抓第一個
            if start_idx != -1:
                brace_count = 0
                end_idx = -1
                for i, char in enumerate(generated_text[start_idx:], start=start_idx):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                
                if end_idx != -1:
                    generated_text = generated_text[start_idx : end_idx+1]
                else:
                    # 萬一沒找到結尾，就用舊方法兜底
                    generated_text = generated_text[start_idx : generated_text.rfind("}")+1]

            print(f"\n🔍 擷取到的最終 JSON: {generated_text[:100]}...") # Debug 用

            report = json.loads(generated_text)
            
            # --- 讀取結果 (保持不變) ---
            risk_level = report.get("風險標記", "MEDIUM")
            
            if risk_level == "LOW":
                user_res = "資料驗證無誤，正在為您進行試算。"
                next_step = "TRANSFER_TO_FRE"
            elif risk_level == "HIGH":
                user_res = "系統偵測到您的資料與紀錄有出入，請說明目前狀況。"
                next_step = "FORCE_LDE_CLARIFY"
            else:
                user_res = "資料已受理，將轉由人工覆核。"
                next_step = "TRANSFER_TO_FRE"

            return {
                "expert": f"DVE ({risk_level})",
                "response": user_res,
                "dve_raw_report": report,
                "next_step": next_step
            }

        except Exception as e:
            print(f"\n❌ DVE 解析失敗: {e}")
            # 如果解析失敗，印出原文讓我們除錯
            # print(f"Raw Text: {full_text}") 
            return {
                "expert": "DVE (Error)",
                "response": "系統忙碌中，請稍後。",
                "next_step": "HUMAN_HANDOVER"
            }