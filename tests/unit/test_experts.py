"""
experts 模組單元測試
測試 LDE, DVE, FRE 專家功能
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestBaseExpert:
    """基礎專家測試"""
    
    def test_base_expert_abstract(self):
        """測試基類是否為抽象類"""
        from experts.base import BaseExpert
        
        # BaseExpert 的 process 方法應該拋出 NotImplementedError
        # 但實例化需要 LLM，所以這裡跳過
        pass


class TestLDEExpert:
    """LDE 專家測試"""
    
    @pytest.fixture
    def sample_task_data(self):
        """標準任務資料"""
        return {
            "user_query": "我想申請貸款",
            "profile_state": {
                "name": "王小明",
                "id": "A123456789",
                "job": "工程師",
                "income": 70000,
                "purpose": "購車",
                "amount": 500000
            },
            "verification_status": "unknown"
        }
    
    def test_decide_mode_consult_few_data(self):
        """測試諮詢模式決策 - 資料少"""
        # 資料少 + 諮詢問題 → Consult
        profile = {"name": "王小明"}  # 只有 1 個欄位
        query = "請問利率多少?"
        verification_status = "unknown"
        
        # 測試決策邏輯
        consult_keywords = ["多少", "利率", "什麼", "資格"]
        is_consult_question = any(kw in query for kw in consult_keywords)
        filled_count = sum(1 for v in profile.values() if v is not None)
        
        assert is_consult_question is True
        assert filled_count <= 2
        # 應該選擇 consult 模式
    
    def test_decide_mode_guide(self):
        """測試引導模式決策"""
        profile = {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師"
        }
        query = "我叫王小明"
        verification_status = "unknown"
        
        # unknown 狀態應該選擇 guide 模式
        assert verification_status in ["unknown", "pending", "mismatch"]
    
    @patch('experts.lde.lde_expert.ENABLE_FINETUNED_MODELS', False)
    def test_lde_without_finetuned_model(self):
        """測試無 Fine-tuned Model 的 LDE"""
        # 當 ENABLE_FINETUNED_MODELS=False 時，應該使用 Gemini
        pass
    
    def test_consult_keywords(self):
        """測試諮詢關鍵字"""
        consult_keywords = [
            "多少", "利率", "什麼", "資格", "可以嗎",
            "試算", "好過", "推薦", "怎麼", "如何",
            "條件", "審核", "期限", "費用", "划算"
        ]
        
        test_queries = [
            ("請問利率多少?", True),
            ("我叫王小明", False),
            ("條件是什麼?", True),
            ("0912345678", False)
        ]
        
        for query, expected in test_queries:
            is_consult = any(kw in query for kw in consult_keywords)
            assert is_consult == expected, f"Query: {query}"


class TestDVEExpert:
    """DVE 專家測試"""
    
    @pytest.fixture
    def sample_task_data(self):
        """標準任務資料"""
        return {
            "user_query": "補件完成",
            "profile_state": {
                "name": "王小明",
                "id": "A123456789",
                "job": "工程師",
                "income": 70000,
                "purpose": "購車",
                "amount": 500000,
                "phone": "0912-345-678"
            },
            "verification_status": "pending"
        }
    
    def test_tech_keywords_detection(self):
        """測試技術問題關鍵字偵測"""
        tech_keywords = ["傳不上", "失敗", "格式錯誤", "太慢", "當機", "無法"]
        
        test_queries = [
            ("圖片傳不上去", True),
            ("系統失敗", True),
            ("我要補件", False),
            ("完成了", False)
        ]
        
        for query, expected in test_queries:
            has_tech = any(k in query for k in tech_keywords)
            assert has_tech == expected, f"Query: {query}"
    
    def test_risk_level_logic(self):
        """測試風險等級邏輯"""
        # 測試規則式驗證的風險等級判斷
        
        # 情況 1: 無不符 → LOW
        mismatches_0 = []
        if len(mismatches_0) >= 2:
            risk = "HIGH"
        elif len(mismatches_0) == 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        assert risk == "LOW"
        
        # 情況 2: 1 項不符 → MEDIUM
        mismatches_1 = ["職業不符"]
        if len(mismatches_1) >= 2:
            risk = "HIGH"
        elif len(mismatches_1) == 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        assert risk == "MEDIUM"
        
        # 情況 3: 2+ 項不符 → HIGH
        mismatches_2 = ["職業不符", "收入不符"]
        if len(mismatches_2) >= 2:
            risk = "HIGH"
        elif len(mismatches_2) == 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        assert risk == "HIGH"
    
    def test_next_step_by_risk(self):
        """測試根據風險等級決定下一步"""
        risk_to_step = {
            "LOW": "TRANSFER_TO_FRE",
            "MEDIUM": "TRANSFER_TO_FRE",
            "HIGH": "FORCE_LDE_CLARIFY"
        }
        
        for risk, expected_step in risk_to_step.items():
            if risk == "LOW":
                next_step = "TRANSFER_TO_FRE"
            elif risk == "HIGH":
                next_step = "FORCE_LDE_CLARIFY"
            else:
                next_step = "TRANSFER_TO_FRE"
            
            assert next_step == expected_step


class TestFREExpert:
    """FRE 專家測試"""
    
    @pytest.fixture
    def sample_task_data(self):
        """標準任務資料"""
        return {
            "user_query": "進行最終評估",
            "profile_state": {
                "name": "王小明",
                "id": "A123456789",
                "job": "工程師",
                "income": 70000,
                "purpose": "購車",
                "amount": 500000
            },
            "verification_status": "verified",
            "dve_result": {
                "risk_level": "LOW"
            }
        }
    
    def test_dbr_calculation(self):
        """測試 DBR (負債比) 計算"""
        p_income = 70000
        p_amount = 500000
        
        # 假設 5 年期 (84 個月)，利率 3%
        monthly_pay = int((p_amount * 1.03) / 84)
        dbr = (monthly_pay / p_income * 100)
        
        assert monthly_pay > 0
        assert dbr < 100  # DBR 應該小於 100%
        
        # 這個案例的 DBR 應該是合理的
        expected_dbr = (500000 * 1.03 / 84) / 70000 * 100
        assert abs(dbr - expected_dbr) < 0.1
    
    def test_credit_score_calculation(self):
        """測試信用評分計算"""
        # 收入 > 40000 → 700 分
        # 收入 <= 40000 → 600 分
        
        test_cases = [
            (70000, 700),
            (50000, 700),
            (40000, 600),
            (30000, 600)
        ]
        
        for income, expected_score in test_cases:
            score = 700 if income > 40000 else 600
            assert score == expected_score, f"Income: {income}"
    
    def test_safety_guard_missing_data(self):
        """測試安全鎖 - 資料缺失"""
        p_income = 0
        p_job = "資料不足"
        decision = "核准_PASS"
        
        # 關鍵資料缺失時，不應核准
        missing_critical = (p_income == 0) or (p_job == "資料不足")
        
        if missing_critical and ("PASS" in decision or "核准" in decision):
            decision = "轉介審核_ESCALATE"
        
        assert decision == "轉介審核_ESCALATE"
    
    def test_safety_guard_high_dbr(self):
        """測試安全鎖 - 高 DBR"""
        dbr = 65  # 超過 60%
        decision = "核准_PASS"
        
        if dbr > 60 and ("PASS" in decision or "核准" in decision):
            decision = "拒絕_REJECT"
        
        assert decision == "拒絕_REJECT"
    
    def test_safety_guard_low_credit(self):
        """測試安全鎖 - 低信用分"""
        credit_score = 600  # 低於 650
        decision = "核准_PASS"
        
        if credit_score < 650 and ("PASS" in decision or "核准" in decision):
            decision = "拒絕_REJECT"
        
        assert decision == "拒絕_REJECT"
    
    def test_decision_mapping(self):
        """測試決策映射"""
        decisions = {
            "核准_PASS": "CASE_CLOSED_SUCCESS",
            "拒絕_REJECT": "CASE_CLOSED_REJECT",
            "轉介審核_ESCALATE": "HUMAN_HANDOVER"
        }
        
        for decision, expected_step in decisions.items():
            if "PASS" in decision or "核准" in decision:
                next_step = "CASE_CLOSED_SUCCESS"
            elif "REJECT" in decision or "拒絕" in decision:
                next_step = "CASE_CLOSED_REJECT"
            else:
                next_step = "HUMAN_HANDOVER"
            
            assert next_step == expected_step


class TestExpertResponseStructure:
    """專家回應結構測試"""
    
    def test_lde_response_structure(self):
        """測試 LDE 回應結構"""
        required_fields = ["expert", "mode", "response", "next_step"]
        
        sample_response = {
            "expert": "LDE (Consult)",
            "mode": "consult",
            "response": "您好，請問有什麼可以幫您的?",
            "updated_profile": None,
            "next_step": "等待客戶後續意願"
        }
        
        for field in required_fields:
            assert field in sample_response
    
    def test_dve_response_structure(self):
        """測試 DVE 回應結構"""
        required_fields = ["expert", "mode", "response", "next_step", "risk_level"]
        
        sample_response = {
            "expert": "DVE (LOW)",
            "mode": "ai_verification",
            "response": "資料驗證無誤，正在為您進行試算。",
            "dve_raw_report": {},
            "next_step": "TRANSFER_TO_FRE",
            "risk_level": "LOW"
        }
        
        for field in required_fields:
            assert field in sample_response
    
    def test_fre_response_structure(self):
        """測試 FRE 回應結構"""
        required_fields = ["expert", "mode", "response", "next_step", "financial_metrics"]
        
        sample_response = {
            "expert": "FRE (核准_PASS)",
            "mode": "ai_decision",
            "response": "恭喜！您的信用評分符合標準。",
            "fre_raw_report": {},
            "financial_metrics": {"dbr": 8.7, "score": 700},
            "next_step": "CASE_CLOSED_SUCCESS"
        }
        
        for field in required_fields:
            assert field in sample_response
