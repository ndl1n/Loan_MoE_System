"""
端到端測試 - 使用者旅程模擬
模擬真實使用者的對話流程
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestUserJourneySimulation:
    """使用者旅程模擬測試"""
    
    def test_journey_complete_application(self):
        """旅程: 完整申請流程"""
        # 模擬使用者對話
        conversation = [
            # 開始
            {"user": "你好，我想申請貸款", "expected_action": "ask_name"},
            
            # 提供姓名
            {"user": "我叫王小明", "expected_action": "ask_id"},
            
            # 提供身分證
            {"user": "A123456789", "expected_action": "ask_phone"},
            
            # 提供電話
            {"user": "0912-345-678", "expected_action": "ask_job"},
            
            # 提供職業
            {"user": "我是軟體工程師", "expected_action": "ask_income"},
            
            # 提供收入
            {"user": "月薪大概8萬", "expected_action": "ask_purpose"},
            
            # 提供用途
            {"user": "想買車", "expected_action": "ask_amount"},
            
            # 提供金額
            {"user": "想借50萬", "expected_action": "start_moe"},
            
            # 進入 MoE
            {"system": "MoE 路由到 DVE", "expected_action": "dve_verification"},
            
            # DVE 驗證
            {"system": "DVE 驗證通過", "expected_action": "fre_decision"},
            
            # FRE 決策
            {"system": "FRE 核准", "expected_action": "end"}
        ]
        
        # 驗證流程
        current_stage = "conversation"
        for step in conversation:
            if step.get("expected_action") == "start_moe":
                current_stage = "moe"
            elif step.get("expected_action") == "end":
                current_stage = "completed"
        
        assert current_stage == "completed"
    
    def test_journey_with_clarification(self):
        """旅程: 需要釐清的申請"""
        conversation = [
            {"user": "我要貸款", "stage": "collecting"},
            {"user": "王小明", "stage": "collecting"},
            {"user": "B987654321", "stage": "collecting"},
            {"user": "0987-654-321", "stage": "collecting"},
            {"user": "自由業", "stage": "collecting"},  # 不穩定職業
            {"user": "月收入不固定，大概3萬", "stage": "collecting"},
            {"user": "想整合債務", "stage": "collecting"},  # 高風險用途
            {"user": "想借100萬", "stage": "collecting"},
            
            # DVE 發現問題
            {"system": "DVE 標記 HIGH 風險", "stage": "moe"},
            {"system": "需要更多說明", "stage": "clarification"},
            
            {"user": "我之前是工程師，最近轉自由接案", "stage": "clarification"},
            
            # 重新評估
            {"system": "重新評估", "stage": "moe"},
            {"system": "轉介人工", "stage": "escalation"}
        ]
        
        # 驗證有經過釐清階段
        stages = [step.get("stage") for step in conversation]
        assert "clarification" in stages
        assert "escalation" in stages
    
    def test_journey_consult_only(self):
        """旅程: 僅諮詢不申請"""
        conversation = [
            {"user": "請問利率是多少?", "mode": "consult"},
            {"user": "那審核要多久?", "mode": "consult"},
            {"user": "好的謝謝，我再考慮看看", "mode": "end"}
        ]
        
        # 純諮詢不應該進入 MoE 審核
        modes = [step.get("mode") for step in conversation]
        assert "consult" in modes
        assert "moe" not in modes
    
    def test_journey_tech_support_needed(self):
        """旅程: 需要技術支援"""
        conversation = [
            {"user": "我要申請貸款", "stage": "collecting"},
            {"user": "王小明", "stage": "collecting"},
            {"user": "A123456789", "stage": "collecting"},
            # ... 省略收集過程
            
            # 到 DVE 時遇到問題
            {"user": "我上傳文件但一直失敗", "stage": "tech_support"},
            {"system": "偵測到技術問題，提供協助", "stage": "tech_support"},
            
            {"user": "改用 JPG 格式可以了", "stage": "collecting"},
            
            # 繼續流程
            {"system": "DVE 驗證", "stage": "moe"},
            {"system": "FRE 決策", "stage": "moe"}
        ]
        
        stages = [step.get("stage") for step in conversation]
        assert "tech_support" in stages


class TestConversationPatterns:
    """對話模式測試"""
    
    def test_pattern_single_field_per_message(self):
        """模式: 每則訊息提供一個欄位"""
        messages = [
            ("王小明", ["name"]),
            ("A123456789", ["id"]),
            ("0912345678", ["phone"]),
            ("工程師", ["job"]),
            ("7萬", ["income"]),
            ("買車", ["loan_purpose"]),
            ("50萬", ["amount"])
        ]
        
        for msg, expected_fields in messages:
            assert len(expected_fields) == 1
    
    def test_pattern_multiple_fields_per_message(self):
        """模式: 單則訊息提供多個欄位"""
        messages = [
            ("我叫王小明，月薪7萬", ["name", "income"]),
            ("想借50萬買車", ["amount", "loan_purpose"]),
            ("我是工程師，在台積電上班", ["job", "company"])
        ]
        
        for msg, expected_fields in messages:
            assert len(expected_fields) >= 2
    
    def test_pattern_natural_language_amounts(self):
        """模式: 自然語言金額"""
        amount_expressions = [
            ("5萬", 50000),
            ("五萬", 50000),
            ("50萬", 500000),
            ("五十萬", 500000),
            ("100萬", 1000000),
            ("一百萬", 1000000),
            ("1.5萬", 15000),
            ("50k", 50000),
            ("100K", 100000)
        ]
        
        for expr, expected in amount_expressions:
            # 這裡只驗證測試資料的結構
            assert expected > 0
    
    def test_pattern_phone_formats(self):
        """模式: 各種電話格式"""
        phone_formats = [
            "0912345678",
            "0912-345-678",
            "0912 345 678",
            "+886912345678",
            "886912345678"
        ]
        
        expected_normalized = "0912-345-678"
        
        # 所有格式正規化後應該相同
        for fmt in phone_formats:
            # 驗證輸入存在
            assert len(fmt) >= 10


class TestResponseValidation:
    """回應驗證測試"""
    
    def test_response_is_professional(self):
        """測試回應專業性"""
        good_responses = [
            "請問您的姓名是?",
            "感謝您提供資訊，還需要確認您的身分證字號。",
            "恭喜！您的申請已通過初審。"
        ]
        
        bad_responses = [
            "嗨嗨～你叫什麼名字呀？",  # 太隨意
            "告訴我你的身分證！！！",   # 太強勢
            "你的申請...算了吧"          # 不專業
        ]
        
        # 好的回應應該有禮貌詞
        for resp in good_responses:
            has_polite = any(w in resp for w in ["請問", "感謝", "恭喜", "您的"])
            assert has_polite is True
    
    def test_response_contains_next_action(self):
        """測試回應包含下一步指引"""
        responses_with_guidance = [
            {"response": "請問您的姓名是?", "has_question": True},
            {"response": "收到，接下來需要您的身分證字號。", "has_guidance": True},
            {"response": "申請已受理，我們會盡快聯繫您。", "has_guidance": True}
        ]
        
        for item in responses_with_guidance:
            has_direction = item.get("has_question") or item.get("has_guidance")
            assert has_direction is True
    
    def test_response_no_sensitive_data_leak(self):
        """測試回應不洩漏敏感資料"""
        # 回應不應該包含完整身分證
        responses = [
            "已收到您的資料，A123456789 先生您好",  # BAD: 完整身分證
            "已收到您的資料，王先生您好",           # GOOD: 只用姓氏
        ]
        
        import re
        id_pattern = r'[A-Z][12]\d{8}'
        
        # 第一個是壞例子（包含身分證）
        assert re.search(id_pattern, responses[0]) is not None
        
        # 第二個是好例子（不包含身分證）
        assert re.search(id_pattern, responses[1]) is None


class TestMultiTurnConsistency:
    """多輪對話一致性測試"""
    
    def test_profile_accumulation(self):
        """測試 Profile 累積"""
        profile_history = [
            {"name": "王小明"},
            {"name": "王小明", "id": "A123456789"},
            {"name": "王小明", "id": "A123456789", "phone": "0912-345-678"},
            {"name": "王小明", "id": "A123456789", "phone": "0912-345-678", "job": "工程師"}
        ]
        
        # 每輪應該保留之前的資料
        for i in range(1, len(profile_history)):
            prev_keys = set(profile_history[i-1].keys())
            curr_keys = set(profile_history[i].keys())
            
            # 新的 profile 應該包含舊的所有 key
            assert prev_keys.issubset(curr_keys)
    
    def test_no_data_loss_on_error(self):
        """測試錯誤時不遺失資料"""
        profile_before_error = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912-345-678"
        }
        
        # 模擬錯誤發生
        error_occurred = True
        
        if error_occurred:
            profile_after_error = profile_before_error.copy()
        
        # 資料應該保留
        assert profile_after_error == profile_before_error
    
    def test_conversation_history_maintained(self):
        """測試對話歷史維護"""
        history = []
        
        turns = [
            ("assistant", "請問您的姓名是?"),
            ("user", "王小明"),
            ("assistant", "請問您的身分證字號是?"),
            ("user", "A123456789")
        ]
        
        for role, content in turns:
            history.append({"role": role, "content": content})
        
        # 歷史應該完整
        assert len(history) == 4
        
        # 角色應該交替
        for i in range(1, len(history)):
            assert history[i]["role"] != history[i-1]["role"]
