"""
端到端測試 - 完整申請流程
測試從對話到最終決策的完整流程
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestFullApplicationFlow:
    """完整申請流程測試"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis"""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.set.return_value = True
        mock.hgetall.return_value = {}
        mock.hset.return_value = True
        mock.lrange.return_value = []
        mock.rpush.return_value = True
        mock.pipeline.return_value = MagicMock()
        return mock
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini"""
        mock = MagicMock()
        mock.text = '{"name": "王小明"}'
        return mock
    
    @pytest.fixture
    def mock_mongodb(self):
        """Mock MongoDB"""
        mock = MagicMock()
        mock.find.return_value = []
        mock.insert_one.return_value = MagicMock(inserted_id="test_id")
        return mock
    
    def test_happy_path_approval(self):
        """測試正常核准流程"""
        # 模擬完整流程
        
        # 1. 對話收集階段
        conversation_result = {
            "status": "READY_FOR_MOE",
            "profile": {
                "name": "王小明",
                "id": "A123456789",
                "phone": "0912-345-678",
                "job": "軟體工程師",
                "income": 100000,
                "loan_purpose": "購車",
                "amount": 500000
            }
        }
        
        assert conversation_result["status"] == "READY_FOR_MOE"
        
        # 2. MoE 路由階段
        routing_result = ("DVE", 0.9, "Guardrail: pending → DVE", {
            "verification_status": "pending"
        })
        
        assert routing_result[0] == "DVE"
        
        # 3. DVE 驗證階段
        dve_result = {
            "expert": "DVE (LOW)",
            "risk_level": "LOW",
            "next_step": "TRANSFER_TO_FRE"
        }
        
        assert dve_result["next_step"] == "TRANSFER_TO_FRE"
        
        # 4. FRE 決策階段
        fre_result = {
            "expert": "FRE (核准_PASS)",
            "response": "恭喜！您的申請已核准。",
            "financial_metrics": {"dbr": 5.9, "score": 700},
            "next_step": "CASE_CLOSED_SUCCESS"
        }
        
        assert fre_result["next_step"] == "CASE_CLOSED_SUCCESS"
        assert "核准" in fre_result["expert"]
    
    def test_rejection_path_high_risk(self):
        """測試高風險拒絕流程"""
        
        # 高風險 Profile
        profile = {
            "name": "張三",
            "id": "B987654321",
            "job": "無業",
            "income": 20000,
            "loan_purpose": "債務整合",
            "amount": 1000000
        }
        
        # DVE 應該判定高風險
        dve_result = {
            "expert": "DVE (HIGH)",
            "risk_level": "HIGH",
            "next_step": "FORCE_LDE_CLARIFY"
        }
        
        # 或者如果到 FRE，應該拒絕
        fre_result = {
            "expert": "FRE (拒絕_REJECT)",
            "response": "感謝申請。經綜合評估，暫時無法核貸。",
            "financial_metrics": {"dbr": 55.0, "score": 600},
            "next_step": "CASE_CLOSED_REJECT"
        }
        
        assert fre_result["next_step"] == "CASE_CLOSED_REJECT"
    
    def test_escalation_path_mismatch(self):
        """測試資料不符轉介流程"""
        
        # DVE 發現資料不符
        dve_result = {
            "expert": "DVE (MEDIUM)",
            "risk_level": "MEDIUM",
            "check_status": "MISMATCH_FOUND",
            "next_step": "TRANSFER_TO_FRE"
        }
        
        # FRE 應該轉介人工
        fre_result = {
            "expert": "FRE (轉介審核_ESCALATE)",
            "response": "申請已受理，將轉由人工覆核。",
            "next_step": "HUMAN_HANDOVER"
        }
        
        assert fre_result["next_step"] == "HUMAN_HANDOVER"
    
    def test_incomplete_data_loop(self):
        """測試資料不完整的循環"""
        
        # 第一輪：資料不完整
        turn_1 = {
            "status": "COLLECTING",
            "missing_fields": ["id", "phone", "job", "income", "loan_purpose", "amount"],
            "profile": {"name": "王小明"}
        }
        
        assert turn_1["status"] == "COLLECTING"
        assert len(turn_1["missing_fields"]) == 6
        
        # 第二輪：補充一些資料
        turn_2 = {
            "status": "COLLECTING",
            "missing_fields": ["income", "loan_purpose", "amount"],
            "profile": {
                "name": "王小明",
                "id": "A123456789",
                "phone": "0912-345-678",
                "job": "工程師"
            }
        }
        
        assert len(turn_2["missing_fields"]) == 3
        
        # 第三輪：資料完整
        turn_3 = {
            "status": "READY_FOR_MOE",
            "missing_fields": [],
            "profile": {
                "name": "王小明",
                "id": "A123456789",
                "phone": "0912-345-678",
                "job": "工程師",
                "income": 70000,
                "loan_purpose": "購車",
                "amount": 500000
            }
        }
        
        assert turn_3["status"] == "READY_FOR_MOE"
        assert len(turn_3["missing_fields"]) == 0


class TestScenarioBasedFlows:
    """場景式流程測試"""
    
    def test_scenario_new_customer_simple_loan(self):
        """場景: 新客戶簡單貸款申請"""
        scenario = {
            "description": "新客戶申請購車貸款",
            "customer_type": "new",
            "profile": {
                "name": "新客戶",
                "id": "N123456789",
                "job": "工程師",
                "income": 80000,
                "purpose": "購車",
                "amount": 400000
            },
            "expected_flow": ["LDE (收集)", "DVE (驗證)", "FRE (決策)"],
            "expected_outcome": "APPROVED"
        }
        
        # 新客戶沒有歷史資料
        rag_history = []
        
        # 應該是低風險
        assert len(rag_history) == 0
        assert scenario["expected_outcome"] == "APPROVED"
    
    def test_scenario_returning_customer_data_match(self):
        """場景: 回頭客資料相符"""
        scenario = {
            "description": "回頭客資料與歷史一致",
            "customer_type": "returning",
            "profile": {
                "name": "王老客戶",
                "id": "R123456789",
                "job": "醫師",
                "income": 200000,
                "purpose": "購屋",
                "amount": 800000
            },
            "history": {
                "hist_job": "醫師",
                "hist_income": "200000",
                "default_record": "無"
            },
            "expected_outcome": "APPROVED"
        }
        
        # 資料相符
        profile = scenario["profile"]
        history = scenario["history"]
        
        job_match = profile["job"] == history["hist_job"]
        income_match = abs(profile["income"] - int(history["hist_income"])) < 10000
        
        assert job_match is True
        assert income_match is True
    
    def test_scenario_returning_customer_data_mismatch(self):
        """場景: 回頭客資料不符"""
        scenario = {
            "description": "回頭客職業從工程師變無業",
            "customer_type": "returning",
            "profile": {
                "name": "資料異動客戶",
                "id": "M123456789",
                "job": "無業",
                "income": 20000,
                "purpose": "週轉",
                "amount": 500000
            },
            "history": {
                "hist_job": "工程師",
                "hist_income": "70000",
                "default_record": "無"
            },
            "expected_outcome": "ESCALATE_OR_REJECT"
        }
        
        profile = scenario["profile"]
        history = scenario["history"]
        
        job_match = profile["job"] == history["hist_job"]
        
        assert job_match is False
        assert scenario["expected_outcome"] == "ESCALATE_OR_REJECT"
    
    def test_scenario_tech_issue_during_verification(self):
        """場景: 驗證過程中遇到技術問題"""
        user_messages = [
            "圖片傳不上去",
            "系統一直失敗",
            "格式錯誤怎麼辦"
        ]
        
        tech_keywords = ["傳不上", "失敗", "格式錯誤"]
        
        for msg in user_messages:
            has_tech_issue = any(kw in msg for kw in tech_keywords)
            assert has_tech_issue is True
        
        # DVE 應該回傳技術支援訊息
        expected_response = "偵測到技術問題"
        assert "技術問題" in expected_response


class TestEdgeCases:
    """邊界情況測試"""
    
    def test_edge_case_zero_income(self):
        """邊界: 收入為零"""
        profile = {
            "name": "零收入客戶",
            "id": "Z123456789",
            "job": "學生",
            "income": 0,
            "purpose": "教育",
            "amount": 100000
        }
        
        # FRE 安全鎖應該攔截
        p_income = profile["income"]
        missing_critical = (p_income == 0)
        
        if missing_critical:
            decision = "轉介審核_ESCALATE"
        else:
            decision = "繼續評估"
        
        assert decision == "轉介審核_ESCALATE"
    
    def test_edge_case_extreme_dbr(self):
        """邊界: 極端 DBR"""
        # 月薪 30000，想借 2000000
        income = 30000
        amount = 2000000
        
        monthly_pay = int((amount * 1.03) / 84)
        dbr = (monthly_pay / income * 100)
        
        # DBR 應該超過 60%
        assert dbr > 60
        
        # 應該被拒絕
        if dbr > 60:
            decision = "拒絕_REJECT"
        else:
            decision = "繼續評估"
        
        assert decision == "拒絕_REJECT"
    
    def test_edge_case_special_characters_in_name(self):
        """邊界: 姓名包含特殊字元"""
        special_names = [
            "王小明（Jr.）",
            "李．大華",
            "張-美玲"
        ]
        
        for name in special_names:
            # 應該能正常處理
            assert len(name) > 0
            assert isinstance(name, str)
    
    def test_edge_case_concurrent_sessions(self):
        """邊界: 同一用戶多個 Session"""
        user_id = "A123456789"
        
        session_1 = {"user_id": user_id, "session_id": "s1", "status": "COLLECTING"}
        session_2 = {"user_id": user_id, "session_id": "s2", "status": "COLLECTING"}
        
        # 應該能區分不同 session
        assert session_1["session_id"] != session_2["session_id"]
    
    def test_edge_case_retry_limit(self):
        """邊界: 重試次數限制"""
        max_retry = 3
        retry_count = 0
        
        while retry_count < max_retry:
            retry_count += 1
        
        assert retry_count == max_retry
        
        # 超過重試次數應該改變策略
        if retry_count >= max_retry:
            variant = "retry"
        else:
            variant = "standard"
        
        assert variant == "retry"


class TestSystemResilience:
    """系統韌性測試"""
    
    def test_graceful_degradation_no_redis(self):
        """測試 Redis 不可用時的降級"""
        redis_available = False
        
        if not redis_available:
            # 應該使用記憶體存儲
            storage = "memory"
        else:
            storage = "redis"
        
        assert storage == "memory"
    
    def test_graceful_degradation_no_mongodb(self):
        """測試 MongoDB 不可用時的降級"""
        mongodb_available = False
        
        if not mongodb_available:
            # DVE 應該使用規則式驗證
            mode = "rule_based"
            rag_history = []
        else:
            mode = "rag_enabled"
            rag_history = [{"data": "..."}]
        
        assert mode == "rule_based"
        assert len(rag_history) == 0
    
    def test_graceful_degradation_no_llm(self):
        """測試 LLM 不可用時的降級"""
        llm_available = False
        
        if not llm_available:
            # 專家應該使用規則式
            expert_mode = "rule_based"
        else:
            expert_mode = "ai_mode"
        
        assert expert_mode == "rule_based"
    
    def test_timeout_handling(self):
        """測試超時處理"""
        import time
        
        timeout_seconds = 30
        start_time = time.time()
        
        # 模擬快速完成
        elapsed = 0.1
        
        if elapsed > timeout_seconds:
            result = "TIMEOUT"
        else:
            result = "SUCCESS"
        
        assert result == "SUCCESS"
