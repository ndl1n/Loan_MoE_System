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
            }

        # --- 3. 組建 Input JSON (Query vs Context) ---
        dve_input_data = {
            "核心識別資訊": {
                "申請人姓名": user_name,
                "身分證字號": user_id
            },
            "最新口述資訊 (Query) 擷取": {
                "職業": profile.get("job", "待業中"),
                "資金用途": "個人進修", # 範例寫死，實務應從 profile 抓
                "聯絡電話": "0910-111-888", # 範例寫死，實務應從 profile 抓
                "服務公司名稱": profile.get("company", "未提供"),
                "月薪": str(profile.get("income", "0"))
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
            # 切割鬼打牆
            if "<|end_of_text|>" in full_text: full_text = full_text.split("<|end_of_text|>")[0]
            if "<|begin_of_text|>" in full_text: full_text = full_text.split("<|begin_of_text|>")[1]
            if "<|begin_of_text|>" in full_text: full_text = full_text.split("<|begin_of_text|>")[0]

            if "### Output:" in full_text: generated_text = full_text.split("### Output:")[1].strip()
            else: generated_text = full_text

            # JSON 清洗
            start_idx = generated_text.find("{")
            if start_idx != -1:
                brace_count = 0
                end_idx = -1
                for i, char in enumerate(generated_text[start_idx:], start=start_idx):
                    if char == "{": brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                if end_idx != -1: generated_text = generated_text[start_idx : end_idx+1]
                else: generated_text = generated_text[start_idx : generated_text.rfind("}")+1]

            print(f"\n🔍 擷取到的最終 JSON: {generated_text[:100]}...") 

            report = json.loads(generated_text)
            risk_level = report.get("風險標記", "MEDIUM")
            
            # ==========================================
            # 🟢 [新增] 自動存檔機制 (Auto-Write Back)
            # ==========================================
            print(f"💾 正在封存本次申請資料至 MongoDB ({user_name})...")
            
            # 1. 建立 Content (人類可讀的銀行存檔格式)
            archive_content = (
                f"【銀行內部存檔】\n"
                f"存檔時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"客戶姓名：{user_name} ({user_id})。\n"
                f"職業紀錄：任職於「{profile.get('company', '未提供')}」，職稱為「{profile.get('job', '待業')}」。\n"
                f"財務紀錄：口述月薪 {profile.get('income', 0)} 元。\n"
                f"查核結果：本次 DVE 查核風險為 {risk_level}。"
            )
            
            # 2. 建立 Metadata (機器可讀，供下次 DVE 使用)
            # 這裡的 Key 必須跟上面 "Rag Context" 讀取的 Key 對應
            archive_meta = {
                "name": user_name,
                "hist_job": profile.get("job"),
                "hist_company": profile.get("company"),
                "hist_income": str(profile.get("income")),
                "hist_phone": "0910-111-888",         # 暫時寫死，實務應從 profile 抓
                "hist_purpose": "個人進修",           # 暫時寫死
                "default_record": "無",               # 新申請假設無違約
                "inquiry_count": "1",                 # 假設查詢一次
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