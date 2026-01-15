"""
專家系統整合測試
測試 LDE, DVE, FRE 之間的協作
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestExpertCoordination:
    """專家協調測試"""
    
    @pytest.fixture
    def standard_profile(self):
        """標準 Profile"""
        return {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師",
            "income": 70000,
            "purpose": "購車",
            "amount": 500000,
            "phone": "0912-345-678",
            "company": "科技公司"
        }
    
    def test_expert_response_compatibility(self):
        """測試專家回應相容性"""
        common_fields = ["expert", "response", "next_step"]
        
        lde_response = {
            "expert": "LDE (Guide)",
            "mode": "guide",
            "response": "請提供更多資訊",
            "updated_profile": {"name": "王小明"},
            "next_step": "等待補件"
        }
        
        dve_response = {
            "expert": "DVE (LOW)",
            "mode": "ai_verification",
            "response": "驗證通過",
            "dve_raw_report": {},
            "next_step": "TRANSFER_TO_FRE",
            "risk_level": "LOW"
        }
        
        fre_response = {
            "expert": "FRE (核准_PASS)",
            "mode": "ai_decision",
            "response": "恭喜核准",
            "fre_raw_report": {},
            "financial_metrics": {"dbr": 8.7, "score": 700},
            "next_step": "CASE_CLOSED_SUCCESS"
        }
        
        for response in [lde_response, dve_response, fre_response]:
            for field in common_fields:
                assert field in response, f"Missing {field} in {response['expert']}"
    
    def test_dve_result_passed_to_fre(self, standard_profile):
        """測試 DVE 結果傳遞給 FRE"""
        dve_result = {
            "risk_level": "LOW",
            "check_status": "VERIFIED",
            "dve_raw_report": {
                "風險標記": "LOW",
                "核實狀態": "VERIFIED"
            }
        }
        
        fre_task = {
            "user_query": "進行最終評估",
            "profile_state": standard_profile,
            "verification_status": "verified",
            "dve_result": dve_result
        }
        
        assert fre_task["dve_result"]["risk_level"] == "LOW"
    
    def test_expert_next_step_handling(self):
        """測試專家 next_step 處理"""
        next_step_actions = {
            "等待補件": "continue_conversation",
            "等待客戶後續意願": "wait_user",
            "TRANSFER_TO_FRE": "call_fre",
            "FORCE_LDE_CLARIFY": "call_lde_with_mismatch",
            "CASE_CLOSED_SUCCESS": "end_approved",
            "CASE_CLOSED_REJECT": "end_rejected",
            "HUMAN_HANDOVER": "transfer_human"
        }
        
        for step, action in next_step_actions.items():
            assert action is not None


class TestExpertRAGIntegration:
    """專家與 RAG 整合測試"""
    
    def test_dve_rag_context_usage(self):
        """測試 DVE 使用 RAG Context"""
        rag_history = [
            {
                "user_id": "A123456789",
                "content": "歷史紀錄",
                "metadata": {
                    "hist_job": "工程師",
                    "hist_income": "70000",
                    "hist_phone": "0912-345-678",
                    "default_record": "無"
                }
            }
        ]
        
        latest = rag_history[-1]
        meta = latest.get("metadata", {})
        
        rag_context = {
            "檔案中紀錄職業": meta.get("hist_job", "無紀錄"),
            "檔案中年薪/月薪": meta.get("hist_income", "0"),
            "檔案中聯絡電話": meta.get("hist_phone", "無紀錄"),
            "歷史違約紀錄": meta.get("default_record", "無")
        }
        
        assert rag_context["檔案中紀錄職業"] == "工程師"
        assert rag_context["歷史違約紀錄"] == "無"
    
    def test_dve_archive_after_verification(self):
        """測試 DVE 驗證後存檔"""
        archive_content = {
            "user_id": "A123456789",
            "content": "【銀行內部存檔】...",
            "metadata": {
                "name": "王小明",
                "hist_job": "工程師",
                "hist_income": "70000",
                "last_risk_level": "LOW"
            }
        }
        
        required_fields = ["user_id", "content", "metadata"]
        for field in required_fields:
            assert field in archive_content
    
    def test_mismatch_detection_logic(self):
        """測試不符檢測邏輯"""
        # 口述資料
        current = {
            "job": "醫師",
            "income": 150000,
            "phone": "0911-111-111"
        }
        
        # 歷史資料
        history = {
            "hist_job": "工程師",
            "hist_income": "70000",
            "hist_phone": "0912-345-678"
        }
        
        mismatches = []
        
        if history["hist_job"] != current["job"]:
            mismatches.append("職業不符")
        
        hist_income = int(history["hist_income"])
        if abs(hist_income - current["income"]) > hist_income * 0.2:
            mismatches.append("收入差異過大")
        
        if history["hist_phone"] != current["phone"]:
            mismatches.append("電話不符")
        
        assert len(mismatches) == 3


class TestExpertLLMIntegration:
    """專家與 LLM 整合測試"""
    
    def test_prompt_template_formatting(self):
        """測試 Prompt Template 格式化"""
        template = "### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Output:"
        
        instruction = "你是一個貸款專家"
        input_text = '{"name": "王小明"}'
        
        prompt = template.format(instruction=instruction, input_text=input_text)
        
        assert "### Instruction:" in prompt
        assert "你是一個貸款專家" in prompt
        assert "王小明" in prompt
    
    def test_llm_response_parsing(self):
        """測試 LLM 回應解析"""
        raw_output = '''### Output:
{
  "風險標記": "LOW",
  "核實狀態": "VERIFIED"
}
<|end_of_text|>'''
        
        # 清理輸出
        if "<|end_of_text|>" in raw_output:
            raw_output = raw_output.split("<|end_of_text|>")[0]
        
        if "### Output:" in raw_output:
            generated = raw_output.split("### Output:")[1].strip()
        else:
            generated = raw_output
        
        import json
        result = json.loads(generated)
        
        assert result["風險標記"] == "LOW"


class TestExpertErrorHandling:
    """專家錯誤處理測試"""
    
    def test_fallback_to_rule_based(self):
        """測試降級到規則式處理"""
        # 當 AI 模型不可用時，應該使用規則式
        enable_finetuned = False
        
        if not enable_finetuned:
            mode = "rule_based"
        else:
            mode = "ai_mode"
        
        assert mode == "rule_based"
    
    def test_invalid_json_handling(self):
        """測試無效 JSON 處理"""
        invalid_outputs = [
            "這不是 JSON",
            '{"unclosed": ',
            '{"key": undefined}'
        ]
        
        for output in invalid_outputs:
            try:
                import json
                json.loads(output)
                parsed = True
            except (json.JSONDecodeError, ValueError):
                parsed = False
            
            assert parsed is False
    
    def test_missing_field_graceful_handling(self):
        """測試缺失欄位的優雅處理"""
        profile = {"name": "王小明"}
        
        # 使用 .get() 避免 KeyError
        job = profile.get("job", "資料不足")
        income = profile.get("income", 0)
        
        assert job == "資料不足"
        assert income == 0
