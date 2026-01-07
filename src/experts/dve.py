import json
import torch
from datetime import datetime
from transformers import TextStreamer
from peft import PeftModel
import re

from ..rag_service import rag_engine
from ..config import DVE_ADAPTER_PATH, DVE_PROMPT_TEMPLATE, DVE_INSTRUCTION, DEVICE
from .base import BaseExpert

class DVE_Expert(BaseExpert):
    """
    DVE: 資料查核專家 (Ultimate Robust Version)
    特色: 
    1. Regex JSON 提取 (防止字串內括號干擾)
    2. 自動清洗 Hallucination
    3. 動態存檔 (修復寫死欄位的 Bug)
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

        print("🛡️ DVE 啟動 AI 查核模式 (Loading from Metadata)...")

        # --- 2. 準備 RAG 資料 (Context) ---
        user_id = profile.get("id", "UNKNOWN")
        user_name = profile.get("name", "Guest")
        
        # 從 MongoDB 撈取
        history_records = rag_engine.get_user_history_by_id(user_id)
        
        rag_context = {}
        
        if history_records:
            print(f"🔍 發現歷史紀錄，正在組裝 Context...")
            latest_record = history_records[-1] # 取最新
            meta = latest_record.get("metadata", {})
            
            # 直接從 Metadata 對應到 DVE 需要的 Key
            rag_context = {
                "檔案中紀錄職業": meta.get("hist_job", "無紀錄"),
                "上次貸款資金用途": meta.get("hist_purpose", "無紀錄"),
                "檔案中聯絡電話": meta.get("hist_phone", "無紀錄"),
                "歷史違約紀錄": meta.get("default_record", "無"),
                "檔案中服務公司名稱": meta.get("hist_company", "無紀錄"),
                "檔案中年薪/月薪": str(meta.get("hist_income", "0")),
                "信用報告查詢次數": str(meta.get("inquiry_count", "0")),
                "地址變動次數": str(meta.get("addr_change_count", "0"))
            }
        else:
            print("⚠️ 新用戶 (無歷史紀錄)")
            rag_context = {
                "檔案中紀錄職業": "無紀錄 (新戶)",
                "上次貸款資金用途": "無紀錄",
                "檔案中聯絡電話": "無紀錄",
                "歷史違約紀錄": "無",
                "檔案中服務公司名稱": "無紀錄",
                "檔案中年薪/月薪": "0",
                "信用報告查詢次數": "0",
                "地址變動次數": "0"
            }

        # --- 3. 組建 Input JSON ---
        # 為了存檔時能拿到正確資料，我們先把變數提取出來
        q_job = profile.get("job", "待業中")
        q_purpose = profile.get("purpose", "一般週轉") # 嘗試從 profile 抓，沒有則預設
        q_phone = profile.get("phone", "09xx-xxx-xxx") # 嘗試從 profile 抓
        q_company = profile.get("company", "未提供")
        q_income = str(profile.get("income", "0"))

        dve_input_data = {
            "核心識別資訊": {
                "申請人姓名": user_name,
                "身分證字號": user_id
            },
            "最新口述資訊 (Query) 擷取": {
                "職業": q_job,
                "資金用途": q_purpose,
                "聯絡電話": q_phone,
                "服務公司名稱": q_company,
                "月薪": q_income
            },
            "RAG 檢索的歷史數據 (Context) 擷取": rag_context
        }
        
        input_json_str = json.dumps(dve_input_data, ensure_ascii=False)

        # --- Debug ---
        print("\n" + "="*50)
        print("📝 DVE 最終組裝的 Input JSON:")
        print(json.dumps(dve_input_data, indent=2, ensure_ascii=False))
        print("="*50 + "\n")

        # --- 4. 呼叫 LLM (Stream Mode) ---
        streamer = TextStreamer(self.llm._tokenizer, skip_prompt=True)
        print(f"🌊 Input JSON 已構建，長度: {len(input_json_str)} chars")
        print("🌊 開始生成 (Stream Mode)... 請看下方輸出 👇")

        model = self.llm._base_model
        tokenizer = self.llm._tokenizer
        
        model = PeftModel.from_pretrained(model, DVE_ADAPTER_PATH)
        model.eval()

        prompt = DVE_PROMPT_TEMPLATE.format(DVE_INSTRUCTION, input_json_str)
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=512,
                temperature=0.1,
                repetition_penalty=1.2,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # --- 5. 解析與策略分流 ---
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=False) # 改成 False 以便我們偵測特殊符號
        
        try:
            # Step A: 粗略切割
            if "<|end_of_text|>" in full_text: full_text = full_text.split("<|end_of_text|>")[0]
            # 切割鬼打牆
            # if "<|end_of_text|>" in full_text: full_text = full_text.split("<|end_of_text|>")[0]
            # if "<|begin_of_text|>" in full_text: full_text = full_text.split("<|begin_of_text|>")[1]
            # if "<|begin_of_text|>" in full_text: full_text = full_text.split("<|begin_of_text|>")[0]
            if "### Output:" in full_text: generated_text = full_text.split("### Output:")[1].strip()
            else: generated_text = full_text
            
            # Step B: 清洗已知的怪異 Token
            generated_text = generated_text.replace("Portály", "")

            # Step C: JSON 提取 (優先使用 Regex，它能處理字串內的括號)
            # 這個 Regex 尋找最外層的 { ... }，re.DOTALL 讓點號匹配換行符
            match = re.search(r"(\{.*\})", generated_text, re.DOTALL)
            
            json_str = ""
            if match:
                json_str = match.group(1)
            else:
                # Fallback: 如果 Regex 失敗，使用最簡單的 find/rfind
                # 這種方式比手動計數迴圈更不容易被字串內的符號干擾
                start_idx = generated_text.find("{")
                end_idx = generated_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_str = generated_text[start_idx : end_idx+1]

            if not json_str:
                raise ValueError("無法提取 JSON 結構")

            # Step D: JSON 載入與修復嘗試
            try:
                report = json.loads(json_str)
            except json.JSONDecodeError:
                # 嘗試常見修復：補齊結尾引號 (針對 'Expecting , delimiter' 錯誤)
                if json_str.count('"') % 2 != 0:
                    json_str = json_str.replace('"}', '"}') # 嘗試修復
                # 最後再試一次，失敗就拋出
                report = json.loads(json_str)

            print(f"\n🔍 最終解析成功 JSON: {str(report)[:100]}...")
            
            # --- 讀取結果 ---
            # 注意：您的測試資料輸出 "MISMATCH_FOUND"，但之前的程式碼只看 "HIGH"
            # 這裡我們要調整邏輯，讓 MISMATCH_FOUND 對應到 HIGH/MEDIUM  風險
            check_status = report.get("核實狀態", "UNKNOWN")
            risk_level = report.get("風險標記", "MEDIUM")
            
            # 強制邏輯：如果有 MISMATCH_FOUND，風險絕對不可能是 LOW
            if check_status == "MISMATCH_FOUND" and risk_level == "LOW":
                 risk_level = "MEDIUM"
            
            # ==========================================
            # 🟢 [優化] 自動存檔機制 (Auto-Write Back)
            # ==========================================
            print(f"💾 正在封存本次申請資料至 MongoDB ({user_name})...")
            archive_content = (
                f"【銀行內部存檔】\n"
                f"存檔時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"客戶姓名：{user_name} ({user_id})。\n"
                f"職業紀錄：任職於「{q_company}」，職稱為「{q_job}」。\n"
                f"財務紀錄：口述月薪 {q_income} 元。\n"
                f"查核結果：本次 DVE 查核風險為 {risk_level}。"
            )
            
            # Metadata 必須動態寫入
            archive_meta = {
                "name": user_name,
                "hist_job": q_job,
                "hist_company": q_company,
                "hist_income": q_income,
                "hist_phone": q_phone,       # <--- 現在是動態的了
                "hist_purpose": q_purpose,   # <--- 現在是動態的了
                "default_record": "無",      # 新申請假設無違約 (或可保留舊紀錄)
                "inquiry_count": str(int(rag_context.get("信用報告查詢次數", "0")) + 1), # 查詢次數+1
                "last_risk_level": risk_level
            }
            
            # 3. 寫入資料庫
            rag_engine.add_document(user_id, archive_content, metadata=archive_meta)
            print("✅ 資料封存完成！已成為新的歷史紀錄。")
            # ==========================================
            
            # 回傳結果
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
            return {
                "expert": "DVE (Error)",
                "response": "系統忙碌中，請稍後。",
                "next_step": "HUMAN_HANDOVER"
            }