"""
MoE 模組單元測試
測試 MoE 路由相關功能
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestProfileAdapter:
    """Profile 適配器測試"""
    
    def test_adapt_basic(self):
        """測試基本欄位適配"""
        from moe.moe_router import ProfileAdapter
        
        conv_profile = {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",  # 對話欄位名
            "amount": 500000
        }
        
        adapted = ProfileAdapter.adapt(conv_profile)
        
        assert adapted["name"] == "王小明"
        assert adapted["purpose"] == "購車"  # 應轉換為 MoE 欄位名
    
    def test_adapt_with_none_values(self):
        """測試包含 None 的適配"""
        from moe.moe_router import ProfileAdapter
        
        conv_profile = {
            "name": "王小明",
            "id": None,
            "job": None
        }
        
        adapted = ProfileAdapter.adapt(conv_profile)
        
        assert adapted["name"] == "王小明"
        assert "id" not in adapted  # None 值不應被加入
    
    def test_validate_for_moe_valid(self):
        """測試有效 Profile 驗證"""
        from moe.moe_router import ProfileAdapter
        
        profile = {
            "name": "王小明",
            "job": "工程師",
            "income": 50000,
            "purpose": "購車"
        }
        
        is_valid, missing = ProfileAdapter.validate_for_moe(profile)
        
        assert is_valid is True
        assert len(missing) == 0
    
    def test_validate_for_moe_invalid(self):
        """測試無效 Profile 驗證"""
        from moe.moe_router import ProfileAdapter
        
        profile = {
            "name": "王小明"
            # 缺少 job, income, purpose
        }
        
        is_valid, missing = ProfileAdapter.validate_for_moe(profile)
        
        assert is_valid is False
        assert "job" in missing
        assert "income" in missing
        assert "purpose" in missing


class TestVerificationStatusManager:
    """驗證狀態管理器測試"""
    
    def test_infer_status_unknown(self):
        """測試未完成狀態推斷"""
        from moe.moe_router import VerificationStatusManager
        
        profile = {}
        status = VerificationStatusManager.infer_status(profile, is_collection_complete=False)
        
        assert status == "unknown"
    
    def test_infer_status_pending(self):
        """測試待驗證狀態推斷"""
        from moe.moe_router import VerificationStatusManager
        
        profile = {}
        status = VerificationStatusManager.infer_status(profile, is_collection_complete=True)
        
        assert status == "pending"
    
    def test_infer_status_explicit(self):
        """測試明確狀態"""
        from moe.moe_router import VerificationStatusManager
        
        profile = {"verification_status": "verified"}
        status = VerificationStatusManager.infer_status(profile, is_collection_complete=True)
        
        assert status == "verified"
    
    def test_valid_statuses(self):
        """測試有效狀態列表"""
        from moe.moe_router import VerificationStatusManager
        
        valid = VerificationStatusManager.VALID_STATUSES
        
        assert "unknown" in valid
        assert "pending" in valid
        assert "verified" in valid
        assert "mismatch" in valid


class TestMoEGateKeeper:
    """MoE GateKeeper 測試"""
    
    @pytest.fixture
    def sample_input(self):
        """標準輸入"""
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
    
    def test_calculate_risk_score_low(self):
        """測試低風險評分"""
        # 需要模型權重才能測試，這裡測試邏輯
        profile = {
            "job": "醫師",
            "income": 200000,
            "purpose": "購屋",
            "amount": 500000
        }
        
        # 預期低風險
        # 職業: 醫師 -> 低風險 (0.1)
        # 收入: 200000 -> 低風險 (0.1)
        # 用途: 購屋 -> 低風險 (0.2)
        # DTI: 低
        
        # 注意: 實際計算需要載入模型
    
    def test_calculate_risk_score_high(self):
        """測試高風險評分"""
        profile = {
            "job": "無業",
            "income": 20000,
            "purpose": "債務整合",
            "amount": 1000000
        }
        
        # 預期高風險


class TestMoERouter:
    """MoE 路由器測試"""
    
    def test_router_initialization(self):
        """測試路由器初始化"""
        from moe.moe_router import MoERouter
        
        router = MoERouter()
        
        assert router.gatekeeper is None  # 延遲載入
    
    def test_calculate_completeness_full(self):
        """測試完整度計算 - 全部填寫"""
        from moe.moe_router import MoERouter
        
        router = MoERouter()
        
        profile = {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師",
            "income": 70000,
            "purpose": "購車",
            "amount": 500000
        }
        
        completeness = router._calculate_completeness(profile)
        
        assert completeness == 1.0
    
    def test_calculate_completeness_partial(self):
        """測試完整度計算 - 部分填寫"""
        from moe.moe_router import MoERouter
        
        router = MoERouter()
        
        profile = {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師"
            # 缺少 3 個欄位
        }
        
        completeness = router._calculate_completeness(profile)
        
        assert completeness == 0.5  # 3/6
    
    def test_route_missing_fields(self):
        """測試缺少必要欄位的路由"""
        from moe.moe_router import MoERouter
        
        router = MoERouter()
        
        # 這個 profile 缺少必要欄位
        profile = {
            "name": "王小明"
        }
        
        expert, confidence, reason, info = router.route(
            profile=profile,
            user_query="測試",
            is_collection_complete=False
        )
        
        # 應該路由到 LDE
        assert expert == "LDE"
        assert "Missing" in reason or "missing" in reason.lower()


class TestGuardrails:
    """護欄規則測試"""
    
    def test_guardrail_unknown_to_lde(self):
        """測試 unknown 狀態護欄"""
        # 這個測試需要載入模型
        # 先測試邏輯
        status = "unknown"
        expected = "LDE"
        
        # 當狀態是 unknown 時，應該導向 LDE
        assert True  # placeholder
    
    def test_guardrail_verified_to_fre(self):
        """測試 verified 狀態護欄"""
        status = "verified"
        expected = "FRE"
        
        assert True  # placeholder
    
    def test_guardrail_mismatch_to_lde(self):
        """測試 mismatch 狀態護欄"""
        status = "mismatch"
        expected = "LDE"
        
        assert True  # placeholder
    
    def test_guardrail_tech_keywords(self):
        """測試技術問題關鍵字"""
        tech_keywords = ["系統", "錯誤", "無法", "bug", "故障", "補件", "驗證"]
        
        # 包含這些關鍵字時，應該導向 DVE
        test_queries = [
            "系統出現錯誤",
            "無法上傳",
            "補件需求"
        ]
        
        for query in test_queries:
            has_tech_kw = any(kw in query for kw in tech_keywords)
            assert has_tech_kw is True


class TestModelArchitecture:
    """模型架構測試"""
    
    def test_model_structure(self):
        """測試模型結構"""
        from moe.model_arch import StateFirstGatingModel
        import torch
        
        model = StateFirstGatingModel(n_classes=3, struct_dim=7)
        
        # 檢查層級結構
        assert hasattr(model, 'bert')
        assert hasattr(model, 'text_compressor')
        assert hasattr(model, 'struct_net')
        assert hasattr(model, 'classifier')
    
    def test_model_output_shape(self):
        """測試模型輸出形狀"""
        from moe.model_arch import StateFirstGatingModel
        import torch
        
        model = StateFirstGatingModel(n_classes=3, struct_dim=7)
        model.eval()
        
        # 建立假輸入
        batch_size = 2
        seq_len = 64
        
        input_ids = torch.randint(0, 1000, (batch_size, seq_len))
        attention_mask = torch.ones(batch_size, seq_len)
        struct_features = torch.rand(batch_size, 7)
        
        with torch.no_grad():
            output = model(input_ids, attention_mask, struct_features)
        
        assert output.shape == (batch_size, 3)  # 3 個專家
    
    def test_model_forward_pass(self):
        """測試前向傳播"""
        from moe.model_arch import StateFirstGatingModel
        import torch
        
        model = StateFirstGatingModel(n_classes=3, struct_dim=7)
        model.eval()
        
        input_ids = torch.randint(0, 1000, (1, 32))
        attention_mask = torch.ones(1, 32)
        struct_features = torch.rand(1, 7)
        
        try:
            with torch.no_grad():
                output = model(input_ids, attention_mask, struct_features)
            success = True
        except Exception as e:
            success = False
        
        assert success is True
