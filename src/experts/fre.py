import json
import torch
import time
from datetime import datetime
from transformers import TextStreamer
from peft import PeftModel
from ..config import FRE_ADAPTER_PATH, FRE_PROMPT_TEMPLATE, FRE_INSTRUCTION, DEVICE
from .base import BaseExpert

class FRE_Expert(BaseExpert):
    """
    FRE: 最終風控專家 (Streamer + Schema Matching + Safety Guard)
    """
    
    def process(self, task_data, history=[]):
        profile = task_data.get("profile_state", {})
        dve_result = task_data.get("dve_result", {})
        
        # --- 1. 輔助函數：處理 Null 與型別轉換 ---
        def safe_int(val, default=0):
            try:
                if val in [None, "null", "資料不足", "", "None"]: return default
                return int(float(val))
            except: return default

        def safe_str(val, default="資料不足"):
            if val in [None, "null", "", "None"]: return default
            return str(val)

        # --- 2. 準備數據 & 數學計算 (Python Layer) ---
        p_income = safe_int(profile.get("income"))
        p_amount = safe_int(profile.get("amount"))
        p_job = safe_str(profile.get("job"))
        
        # 假設歷史薪資 (若無則用口述)
        h_income = p_income if p_income > 0 else 60000 
        calc_base_income = p_income if p_income > 0 else h_income
        
        # 計算 DBR
        if p_amount > 0:
            monthly_pay = int((p_amount * 1.03) / 84) 
        else:
            monthly_pay = 0
        
        dbr = (monthly_pay / calc_base_income * 100) if calc_base_income > 0 else 0
        
        # 模擬信用評分 (簡單規則：薪資高分就高)
        credit_score = 700 if calc_base_income > 40000 else 600

        # --- 3. 構建 Input JSON (Schema 對齊訓練資料) ---
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        fre_input_data = {
            "caseId": f"CASE_{int(time.time())}",
            "creationDate": current_time,
            "scenarioType": "REAL_TIME_INFERENCE",
            "customerIdentity": {
                "身分證字號": safe_str(profile.get("id"), "UNKNOWN"),
                "申請人姓名": safe_str(profile.get("name"), "Guest")
            },
            "applicationData": {
                "申請金額": p_amount,
                "申請用途_官方": "週轉金"
            },
            "creditReportData": {
                "系統原始信用評分": credit_score,
                "現有總負債金額": 0,
                "歷史違約紀錄": "無" if credit_score >= 650 else "有",
                "信用報告查詢次數_近3月": 1
            },
            "providedData": {
                "口述月薪": profile.get("income"), # 保留 None 讓模型看
                "口述職業": p_job,
                "口述公司名稱": safe_str(profile.get("company")),
                "口述聯絡電話": "09xx-xxx-xxx",
                "口述資金用途": "週轉金"
            },
            "historicalData": {
                "歷史月薪": h_income, 
                "歷史職業": "資料庫紀錄"
            },
            "system_hint": {
                "dve_risk_label": dve_result.get("risk_level", "LOW"),
                "calculated_dbr": f"{dbr:.1f}%"
            }
        }
        
        input_json_str = json.dumps(fre_input_data, ensure_ascii=False)
        print(f"💰 FRE Input 構建完成 (DBR: {dbr:.1f}%, Score: {credit_score})")

        # --- 4. 呼叫 LLM (Stream Mode) ---
        print("🌊 開始生成決策 (Stream Mode)... 👇")
        
        # 這裡不使用 get_expert_response，而是直接調用以啟用 Streamer
        streamer = TextStreamer(self.llm._tokenizer, skip_prompt=True)
        model = self.llm._base_model
        tokenizer = self.llm._tokenizer
        
        # 掛載 Adapter
        model = PeftModel.from_pretrained(model, FRE_ADAPTER_PATH)
        model.eval()

        # 準備 Prompt
        prompt = FRE_PROMPT_TEMPLATE.format(FRE_INSTRUCTION, input_json_str)
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,            # <--- 關鍵：啟用直播
                max_new_tokens=512,
                temperature=0.1,
                repetition_penalty=1.2,       # <--- 關鍵：防止重複
                eos_token_id=tokenizer.eos_token_id
            )

        # --- 5. 解析與強力邏輯矯正 (Safety Guard) ---
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        try:
            # 切割鬼打牆文字
            if "<|end_of_text|>" in full_text: full_text = full_text.split("<|end_of_text|>")[0]
            if "### Output:" in full_text: generated_text = full_text.split("### Output:")[1].strip()
            else: generated_text = full_text

            # JSON 清洗 (只抓取第一個完整的 {} 物件)
            if "{" in generated_text:
                generated_text = generated_text[generated_text.find("{"):generated_text.rfind("}")+1]

            report = json.loads(generated_text)
            
            # 取得決策
            # 嘗試適應不同的 JSON 結構 (有些訓練資料有 "最終決策報告" 層級，有些直接是根目錄)
            final_block = report.get("最終決策報告", report)
            decision = final_block.get("最終決策") or report.get("最終決策") or "轉介審核_ESCALATE"
            
            # === 安全鎖 (Logic Override) ===
            override_msg = ""
            
            # 1. 關鍵資料缺失 -> 強制轉人工
            missing_critical = (p_income == 0) or (p_job == "資料不足")
            if missing_critical and ("PASS" in decision or "核准" in decision):
                decision = "轉介審核_ESCALATE"
                override_msg = "(系統修正: 關鍵資料缺失)"
                print("⚠️ FRE Guard: 攔截到資料缺失")

            # 2. DBR 過高 -> 強制拒絕
            if dbr > 60 and ("PASS" in decision):
                decision = "拒絕_REJECT"
                override_msg = f"(系統修正: DBR {dbr:.1f}% 過高)"
                print("⚠️ FRE Guard: 攔截到高負債比")
            
            # 3. 信用分過低 -> 強制拒絕
            if credit_score < 650 and ("PASS" in decision):
                decision = "拒絕_REJECT"
                override_msg = "(系統修正: 信用分不足)"

            # --- 回應生成 ---
            if "PASS" in decision or "核准" in decision:
                user_msg = f"恭喜！您的信用評分 ({credit_score}分) 符合標準。\n初審額度: {p_amount:,} 元"
                next_step = "CASE_CLOSED_SUCCESS"
            elif "REJECT" in decision or "拒絕" in decision:
                user_msg = "感謝申請。經綜合評估，暫時無法核貸。"
                next_step = "CASE_CLOSED_REJECT"
            else:
                user_msg = "申請已受理，將轉由人工覆核。"
                next_step = "HUMAN_HANDOVER"

            return {
                "expert": f"FRE ({decision}) {override_msg}",
                "response": user_msg,
                "fre_raw_report": report,
                "financial_metrics": {"dbr": dbr, "score": credit_score},
                "next_step": next_step
            }

        except Exception as e:
            print(f"\n❌ FRE 解析失敗: {e}")
            return {
                "expert": "FRE (Error)",
                "response": "系統忙碌中。",
                "next_step": "HUMAN_HANDOVER"
            }