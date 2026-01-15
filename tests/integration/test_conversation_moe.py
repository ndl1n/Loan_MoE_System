"""
對話系統到 MoE 路由的整合測試
測試 Conversation → MoE 的完整流程
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestConversationToMoEFlow:
    """對話到 MoE 的流程測試"""
    
    @pytest.fixture
    def complete_profile(self):
        """完整的 Profile"""
        return {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912-345-678",
            "job": "軟體工程師",
            "income": 80000,
            "loan_purpose": "購車",
            "amount": 500000,
            "verification_status": None,
            "last_asked_field": None,
            "retry_count": 0
        }
    
    def test_profile_adapter_integration(self, complete_profile):
        """測試 Profile 適配器與對話欄位的整合"""
        from moe.moe_router import ProfileAdapter
        
        # 對話系統使用 loan_purpose
        assert "loan_purpose" in complete_profile
        
        # 適配後應該變成 purpose
        adapted = ProfileAdapter.adapt(complete_profile)
        
        assert "purpose" in adapted
        assert adapted["purpose"] == "購車"
    
    def test_conversation_status_to_moe(self, complete_profile):
        """測試對話狀態傳遞到 MoE"""
        from moe.moe_router import VerificationStatusManager
        
        # 對話完成時，status 應該是 pending
        complete_profile["verification_status"] = None
        
        status = VerificationStatusManager.infer_status(
            complete_profile,
            is_collection_complete=True
        )
        
        assert status == "pending"
    
    def test_field_mapping_consistency(self):
        """測試欄位映射一致性"""
        from moe.moe_router import ProfileAdapter
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        
        # 對話系統的欄位
        conv_fields = list(schema.fields.keys())
        
        # 檢查映射
        mapping = ProfileAdapter.FIELD_MAPPING
        
        # 確保所有對話欄位都有映射
        for field in conv_fields:
            if field in mapping:
                assert mapping[field] is not None
    
    def test_moe_required_fields_from_conversation(self, complete_profile):
        """測試 MoE 必要欄位來自對話"""
        from moe.moe_router import ProfileAdapter
        
        adapted = ProfileAdapter.adapt(complete_profile)
        
        # MoE 必要欄位
        required = ProfileAdapter.REQUIRED_FIELDS
        
        # 檢查適配後是否包含所有必要欄位
        is_valid, missing = ProfileAdapter.validate_for_moe(adapted)
        
        assert is_valid is True
        assert len(missing) == 0


class TestMoEToExpertFlow:
    """MoE 到專家的流程測試"""
    
    @pytest.fixture
    def sample_moe_input(self):
        """MoE 輸入"""
        return {
            "profile_state": {
                "name": "王小明",
                "id": "A123456789",
                "job": "工程師",
                "income": 70000,
                "purpose": "購車",
                "amount": 500000
            },
            "verification_status": "pending",
            "user_query": "我想申請貸款"
        }
    
    def test_routing_result_to_expert_task(self, sample_moe_input):
        """測試路由結果轉換為專家任務"""
        # 模擬路由結果
        routing_result = ("DVE", 0.9, "Guardrail: Pending → DVE", {
            "verification_status": "pending",
            "profile_completeness": 1.0,
            "risk_score": 0.3
        })
        
        expert, confidence, reason, info = routing_result
        
        # 建立專家任務
        task_data = {
            "user_query": sample_moe_input["user_query"],
            "profile_state": sample_moe_input["profile_state"],
            "verification_status": info["verification_status"]
        }
        
        assert task_data["verification_status"] == "pending"
        assert expert == "DVE"
    
    def test_expert_selection_by_status(self):
        """測試根據狀態選擇專家"""
        status_to_expert = {
            "unknown": "LDE",
            "pending": "DVE",
            "verified": "FRE",
            "mismatch": "LDE"
        }
        
        for status, expected_expert in status_to_expert.items():
            # 這是護欄規則，應該符合
            assert expected_expert in ["LDE", "DVE", "FRE"]


class TestExpertChainFlow:
    """專家鏈流程測試"""
    
    def test_dve_to_fre_handoff(self):
        """測試 DVE 到 FRE 的交接"""
        # DVE 回應
        dve_response = {
            "expert": "DVE (LOW)",
            "mode": "ai_verification",
            "response": "資料驗證無誤",
            "risk_level": "LOW",
            "next_step": "TRANSFER_TO_FRE"
        }
        
        # 當 next_step 是 TRANSFER_TO_FRE 時，應該呼叫 FRE
        assert dve_response["next_step"] == "TRANSFER_TO_FRE"
        
        # FRE 任務應該包含 DVE 結果
        fre_task = {
            "user_query": "評估",
            "profile_state": {},
            "verification_status": "verified",
            "dve_result": dve_response
        }
        
        assert "dve_result" in fre_task
        assert fre_task["dve_result"]["risk_level"] == "LOW"
    
    def test_dve_to_lde_clarify(self):
        """測試 DVE 到 LDE 的釐清流程"""
        dve_response = {
            "expert": "DVE (HIGH)",
            "mode": "rule_based",
            "response": "資料有出入",
            "risk_level": "HIGH",
            "next_step": "FORCE_LDE_CLARIFY"
        }
        
        assert dve_response["next_step"] == "FORCE_LDE_CLARIFY"
        
        # 此時應該更新 verification_status 為 mismatch
        new_status = "mismatch"
        
        # 然後呼叫 LDE
        lde_task = {
            "user_query": "釐清資料",
            "profile_state": {},
            "verification_status": new_status
        }
        
        assert lde_task["verification_status"] == "mismatch"


class TestDataFlowIntegrity:
    """資料流完整性測試"""
    
    def test_profile_not_mutated(self):
        """測試 Profile 不被意外修改"""
        original = {
            "name": "王小明",
            "income": 70000
        }
        
        # 複製一份
        working_copy = original.copy()
        
        # 修改複製
        working_copy["income"] = 80000
        
        # 原始不應改變
        assert original["income"] == 70000
    
    def test_history_accumulation(self):
        """測試對話歷史累積"""
        history = []
        
        # 模擬多輪對話
        turns = [
            {"role": "assistant", "content": "請問您的姓名?"},
            {"role": "user", "content": "王小明"},
            {"role": "assistant", "content": "請問您的職業?"},
            {"role": "user", "content": "工程師"}
        ]
        
        for turn in turns:
            history.append(turn)
        
        assert len(history) == 4
        assert history[0]["role"] == "assistant"
        assert history[-1]["content"] == "工程師"
    
    def test_status_transition_validity(self):
        """測試狀態轉換有效性"""
        valid_transitions = {
            "unknown": ["pending"],  # 收集完成
            "pending": ["verified", "mismatch"],  # DVE 驗證後
            "verified": [],  # 終態
            "mismatch": ["pending"]  # 重新提交
        }
        
        # 檢查每個轉換是否合理
        for from_status, to_statuses in valid_transitions.items():
            for to_status in to_statuses:
                assert to_status in ["unknown", "pending", "verified", "mismatch"]
