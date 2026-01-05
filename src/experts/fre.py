import json
import time
from datetime import datetime
from ..config import FRE_ADAPTER_PATH, FRE_PROMPT_TEMPLATE, FRE_INSTRUCTION
from .base import BaseExpert

class FRE_Expert(BaseExpert):
    """
    FRE: 最終風控專家 (針對訓練資料格式優化版)
    策略: 
    1. 模擬訓練資料的 Input 結構 (Schema Matching)
    2. Python 處理 Null 值與數學計算
    3. 強制邏輯覆寫 (防止模型學到髒資料的幻覺)
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

        # --- 2. 準備數據 ---
        # 取得 Provided Data (口述)
        p_income = safe_int(profile.get("income"))
        p_amount = safe_int(profile.get("amount"))
        p_job = safe_str(profile.get("job"))
        
        # 取得 Historical Data (模擬 RAG，或從 Profile 拿舊資料)
        # 實務上這裡應該接 DB，這裡我們先用 "若口述是空，就用歷史補" 的邏輯
        h_income = p_income if p_income > 0 else 60000 # 預設/歷史薪資
        
        # [數學層] 計算 DBR
        # 訓練資料顯示：如果口述薪資是 Null，它會拿歷史薪資去算 DBR
        calc_base_income = p_income if p_income > 0 else h_income
        
        if p_amount > 0:
            monthly_pay = int((p_amount * 1.03) / 84) # 簡易本息攤還
        else:
            monthly_pay = 0
            
        dbr = (monthly_pay / calc_base_income * 100) if calc_base_income > 0 else 0
        
        # [模擬] 信用評分
        credit_score = 700 if calc_base_income > 40000 else 600

        # --- 3. 構建 Input JSON (完全對齊訓練資料 Schema) ---
        # 您的訓練資料有 caseId, creationDate 等欄位，雖然對決策沒用，
        # 但為了讓模型覺得"環境熟悉"，我們最好還是加上去。
        
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        fre_input_data = {
            "caseId": f"CASE_{int(time.time())}",
            "creationDate": current_time,
            "scenarioType": "REAL_TIME_INFERENCE", # 標記這是即時推論
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
                "現有總負債金額": 0, # 簡化
                "歷史違約紀錄": "無" if credit_score >= 650 else "有",
                "信用報告查詢次數_近3月": 1
            },
            "providedData": {
                "口述月薪": profile.get("income"), # 保留原始 None/Null 狀態給模型看
                "口述職業": p_job,
                "口述公司名稱": safe_str(profile.get("company")),
                "口述聯絡電話": "09xx-xxx-xxx",
                "口述資金用途": "週轉金"
            },
            # 訓練資料裡有 historicalData，我們也補上，避免模型困惑
            "historicalData": {
                "歷史月薪": h_income, 
                "歷史職業": "資料庫紀錄"
            },
            # 這是我們為了修正邏輯，額外給模型的提示 (Prompt Engineering)
            "system_hint": {
                "dve_risk_label": dve_result.get("risk_level", "LOW"),
                "calculated_dbr": f"{dbr:.1f}%"
            }
        }
        
        input_json_str = json.dumps(fre_input_data, ensure_ascii=False)
        print(f"💰 FRE Input 組建完成 (DBR: {dbr:.1f}%)")

        # --- 4. 呼叫 LLM ---
        raw_response = self.llm.get_expert_response(
            adapter_path=FRE_ADAPTER_PATH,
            instruction=FRE_INSTRUCTION,
            user_input=input_json_str,
            template=FRE_PROMPT_TEMPLATE,
            temperature=0.1,
            max_new_tokens=512
        )

        # --- 5. 解析與強力邏輯矯正 (Hard Logic Override) ---
        try:
            # JSON 擷取與修復
            json_str = raw_response
            if "{" in json_str:
                json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]
            
            report = json.loads(json_str)
            
            # 取得 LLM 的決策
            # 訓練資料的 key 可能是 "最終決策報告" -> "最終決策"
            final_decision_block = report.get("最終決策報告", {})
            decision = final_decision_block.get("最終決策") or report.get("最終決策") or "轉介審核_ESCALATE"
            
            # === [核心優化] 強制邏輯矯正 ===
            # 因為訓練資料有髒數據 (Input Null 但 Output PASS)，我們必須在 Python 層擋下來
            override_msg = ""
            
            # 規則 A: 如果關鍵資料是 "資料不足" 或 None，絕對不能 PASS
            missing_critical_data = (p_income == 0) or (p_job == "資料不足")
            if missing_critical_data and ("PASS" in decision or "核准" in decision):
                decision = "轉介審核_ESCALATE"
                override_msg = "(系統修正: 關鍵資料缺失，強制轉人工)"
                print("⚠️ FRE Guard: 攔截到缺失資料卻核准的幻覺")

            # 規則 B: DBR > 45% 絕對拒絕
            if dbr > 45 and ("PASS" in decision):
                decision = "拒絕_REJECT"
                override_msg = "(系統修正: DBR 過高)"
            
            # 規則 C: 信用分 < 650 絕對拒絕
            if credit_score < 650 and ("PASS" in decision):
                decision = "拒絕_REJECT"
                override_msg = "(系統修正: 信用分不足)"

            # --- 6. 產生回應 ---
            user_msg = ""
            next_step = ""
            
            if "PASS" in decision or "核准" in decision:
                user_msg = f"恭喜您！您的信用評分 ({credit_score}分) 符合標準。\n系統初審額度: {p_amount:,} 元\n(專員將於 24 小時內與您聯繫)"
                next_step = "CASE_CLOSED_SUCCESS"
            elif "REJECT" in decision or "拒絕" in decision:
                user_msg = f"感謝您的申請。經綜合評估，暫時無法核貸。\n建議您 3 個月後信用狀況改善再行申請。"
                next_step = "CASE_CLOSED_REJECT"
            else: # ESCALATE / 條件式核准 / 轉介
                user_msg = "您的申請已受理。由於部分資料（如財力證明）需要進一步人工覆核，我們將盡快通知您結果。"
                next_step = "HUMAN_HANDOVER"

            return {
                "expert": f"FRE ({decision}) {override_msg}",
                "response": user_msg,
                "fre_raw_report": report,
                "financial_metrics": {"dbr": dbr, "score": credit_score},
                "next_step": next_step
            }

        except Exception as e:
            print(f"❌ FRE Error: {e}")
            return {
                "expert": "FRE (Error)",
                "response": "系統決策忙碌中，轉由人工處理。",
                "next_step": "HUMAN_HANDOVER"
            }