"""
FRE Expert (Financial Risk Expert) - 最終風控專家

負責：
- 綜合評估申請人的信用與財務狀況
- 🔍 使用 RAG 搜尋相似案例輔助決策
- 生成最終決策 (核准/拒絕/轉介)
- 應用安全鎖防止邏輯錯誤
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

import sys
import os

# 確保可以正確 import 專案模組
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 延遲 import torch (可能不存在)
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import (
    FRE_ADAPTER_PATH,
    FRE_PROMPT_TEMPLATE,
    FRE_INSTRUCTION,
    DEVICE,
    ENABLE_FINETUNED_MODELS
)

# 使用絕對路徑 import BaseExpert
from experts.base import BaseExpert

# 🔍 導入 RAG Service
from services.rag_service import rag_engine

logger = logging.getLogger(__name__)


class FREExpert(BaseExpert):
    """
    FRE: 最終風控專家 (Streamer + Schema Matching + Safety Guard)
    """
    
    def __init__(self):
        """初始化 FRE Expert"""
        if ENABLE_FINETUNED_MODELS:
            super().__init__()
            logger.info("✅ FRE Expert 初始化完成 (含 Fine-tuned Model)")
        else:
            logger.warning("⚠️ FRE Expert: Fine-tuned Model 未啟用")
            self.llm = None
        
        logger.info("✅ FRE Expert 就緒")
    
    def process(self, task_data: Dict, history: List = None) -> Dict[str, Any]:
        """處理風控決策任務"""
        if history is None:
            history = []
            
        profile = task_data.get("profile_state", {})
        dve_result = task_data.get("dve_result", {})
        
        def safe_int(val, default=0):
            try:
                if val in [None, "null", "資料不足", "", "None"]:
                    return default
                return int(float(val))
            except (ValueError, TypeError):
                return default

        def safe_str(val, default="資料不足"):
            if val in [None, "null", "", "None"]:
                return default
            return str(val)

        p_income = safe_int(profile.get("income"))
        p_amount = safe_int(profile.get("amount"))
        p_job = safe_str(profile.get("job"))
        
        h_income = p_income if p_income > 0 else 60000 
        calc_base_income = p_income if p_income > 0 else h_income
        
        monthly_pay = int((p_amount * 1.03) / 84) if p_amount > 0 else 0
        dbr = (monthly_pay / calc_base_income * 100) if calc_base_income > 0 else 0
        
        credit_score = 700 if calc_base_income > 40000 else 600

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
                "口述月薪": profile.get("income"),
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
        logger.info(f"💰 FRE Input 構建完成 (DBR: {dbr:.1f}%, Score: {credit_score})")

        if not ENABLE_FINETUNED_MODELS or self.llm is None:
            logger.warning("⚠️ Fine-tuned Model 未啟用，使用規則式決策")
            return self._rule_based_decision(
                p_income, p_job, p_amount, dbr, credit_score, dve_result,
                profile=profile
            )
        
        try:
            return self._ai_decision(
                input_json_str, p_income, p_job, p_amount, dbr, credit_score
            )
        except Exception as e:
            logger.error(f"❌ FRE AI 決策失敗: {e}", exc_info=True)
            return self._rule_based_decision(
                p_income, p_job, p_amount, dbr, credit_score, dve_result,
                profile=profile
            )
    
    def _ai_decision(
        self,
        input_json_str: str,
        p_income: int,
        p_job: str,
        p_amount: int,
        dbr: float,
        credit_score: int
    ) -> Dict[str, Any]:
        """AI 模型決策"""
        from transformers import TextStreamer
        from peft import PeftModel
        
        logger.info("🌊 開始生成決策 (Stream Mode)...")
        
        streamer = TextStreamer(self.llm._tokenizer, skip_prompt=True)
        model = self.llm._base_model
        tokenizer = self.llm._tokenizer
        
        model = PeftModel.from_pretrained(model, FRE_ADAPTER_PATH)
        model.eval()

        prompt = FRE_PROMPT_TEMPLATE.format(
            instruction=FRE_INSTRUCTION,
            input_text=input_json_str
        )
        inputs = tokenizer(prompt, return_tensors="pt")
        
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=512,
                temperature=0.1,
                repetition_penalty=1.2,
                eos_token_id=tokenizer.eos_token_id
            )

        full_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
        generated_text = self._parse_output(full_text)
        report = self._extract_json(generated_text)
        
        final_block = report.get("最終決策報告", report)
        decision = final_block.get("最終決策") or report.get("最終決策") or "轉介審核_ESCALATE"
        
        decision, override_msg = self._apply_safety_guard(
            decision, p_income, p_job, dbr, credit_score
        )
        
        user_msg, next_step = self._generate_response(decision, credit_score, p_amount)

        return {
            "expert": f"FRE ({decision}) {override_msg}",
            "mode": "ai_decision",
            "response": user_msg,
            "fre_raw_report": report,
            "financial_metrics": {"dbr": dbr, "score": credit_score},
            "next_step": next_step
        }

    def _parse_output(self, full_text: str) -> str:
        if "<|end_of_text|>" in full_text:
            full_text = full_text.split("<|end_of_text|>")[0]
        if "### Output:" in full_text:
            return full_text.split("### Output:")[1].strip()
        return full_text

    def _extract_json(self, text: str) -> Dict:
        if "{" not in text:
            return {}
        try:
            json_str = text[text.find("{"):text.rfind("}")+1]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {}

    def _apply_safety_guard(
        self, decision: str, p_income: int, p_job: str, dbr: float, credit_score: int
    ) -> Tuple[str, str]:
        override_msg = ""
        
        missing_critical = (p_income == 0) or (p_job == "資料不足")
        if missing_critical and ("PASS" in decision or "核准" in decision):
            decision = "轉介審核_ESCALATE"
            override_msg = "(系統修正: 關鍵資料缺失)"
            logger.warning("⚠️ FRE Guard: 攔截到資料缺失")

        elif dbr > 60 and ("PASS" in decision or "核准" in decision):
            decision = "拒絕_REJECT"
            override_msg = f"(系統修正: DBR {dbr:.1f}% 過高)"
            logger.warning("⚠️ FRE Guard: 攔截到高負債比")
        
        elif credit_score < 650 and ("PASS" in decision or "核准" in decision):
            decision = "拒絕_REJECT"
            override_msg = "(系統修正: 信用分不足)"
            logger.warning("⚠️ FRE Guard: 攔截到低信用分")

        return decision, override_msg

    def _generate_response(
        self, decision: str, credit_score: int, p_amount: int
    ) -> Tuple[str, str]:
        if "PASS" in decision or "核准" in decision:
            user_msg = f"恭喜！您的信用評分 ({credit_score}分) 符合標準。\n初審額度: {p_amount:,} 元"
            next_step = "CASE_CLOSED_SUCCESS"
        elif "REJECT" in decision or "拒絕" in decision:
            user_msg = "感謝申請。經綜合評估，暫時無法核貸。"
            next_step = "CASE_CLOSED_REJECT"
        else:
            user_msg = "申請已受理，將轉由人工覆核。"
            next_step = "HUMAN_HANDOVER"
        return user_msg, next_step
    
    def _rule_based_decision(
        self, p_income: int, p_job: str, p_amount: int,
        dbr: float, credit_score: int, dve_result: Dict,
        profile: Dict = None
    ) -> Dict[str, Any]:
        """
        規則式決策 (Fallback)
        
        🔍 加入 RAG: 搜尋 case_library 中的相似案例作為參考
        """
        logger.info("🔧 FRE 規則式決策模式 (Fallback) + RAG")
        
        dve_risk = dve_result.get("risk_level", "MEDIUM")
        
        # === 🔍 RAG: 搜尋相似案例 ===
        rag_reference = None
        if profile:
            try:
                rag_reference = rag_engine.get_reference_for_decision(
                    profile=profile,
                    dve_risk_level=dve_risk,
                    top_k=3
                )
                if rag_reference.get("similar_cases"):
                    logger.info(f"📚 RAG: 找到 {len(rag_reference['similar_cases'])} 筆相似案例")
                    logger.info(f"📚 RAG 建議: {rag_reference.get('recommendation')}")
            except Exception as e:
                logger.warning(f"⚠️ RAG 查詢失敗: {e}")
        
        # === 決策邏輯 ===
        # 優先使用硬規則
        if dve_risk == "HIGH" or credit_score < 650 or dbr > 45:
            decision = "拒絕_REJECT"
            user_msg = "感謝申請。經綜合評估，暫時無法核貸。"
            next_step = "CASE_CLOSED_REJECT"
        elif dve_risk == "MEDIUM" or dbr > 30:
            decision = "轉介審核_ESCALATE"
            user_msg = "申請已受理，將轉由人工覆核。"
            next_step = "HUMAN_HANDOVER"
        else:
            # 可參考 RAG 結果微調
            if rag_reference and rag_reference.get("approval_rate") is not None:
                approval_rate = rag_reference["approval_rate"]
                if approval_rate < 0.3:
                    # 相似案例核准率很低，謹慎處理
                    decision = "轉介審核_ESCALATE"
                    user_msg = "申請已受理，將轉由人工覆核。"
                    next_step = "HUMAN_HANDOVER"
                    logger.info(f"📚 RAG 影響決策: 相似案例核准率僅 {approval_rate:.0%}，轉人工")
                else:
                    decision = "核准_PASS"
                    user_msg = f"恭喜！您的信用評分 ({credit_score}分) 符合標準。\n初審額度: {p_amount:,} 元"
                    next_step = "CASE_CLOSED_SUCCESS"
            else:
                decision = "核准_PASS"
                user_msg = f"恭喜！您的信用評分 ({credit_score}分) 符合標準。\n初審額度: {p_amount:,} 元"
                next_step = "CASE_CLOSED_SUCCESS"
        
        logger.info(f"🔧 規則式決策結果: {decision}")
        
        result = {
            "expert": f"FRE ({decision})",
            "mode": "rule_based",
            "response": user_msg,
            "fre_raw_report": {
                "決策": decision,
                "DBR": f"{dbr:.1f}%",
                "信用評分": credit_score,
                "DVE風險": dve_risk
            },
            "financial_metrics": {"dbr": dbr, "score": credit_score},
            "next_step": next_step
        }
        
        # 加入 RAG 參考資訊
        if rag_reference:
            result["rag_reference"] = {
                "similar_cases_count": len(rag_reference.get("similar_cases", [])),
                "approval_rate": rag_reference.get("approval_rate"),
                "avg_approved_amount": rag_reference.get("avg_approved_amount"),
                "recommendation": rag_reference.get("recommendation")
            }
        
        return result
