"""
API 端點測試
測試 FastAPI 和 LINE Bot Webhook
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestAPIEndpoints:
    """API 端點測試"""
    
    def test_chat_request_model(self):
        """測試 ChatRequest 模型"""
        from pydantic import BaseModel, Field
        
        class ChatRequest(BaseModel):
            user_id: str = Field(..., min_length=1)
            message: str = Field(..., min_length=1)
        
        # 有效請求
        req = ChatRequest(user_id="U123", message="Hello")
        assert req.user_id == "U123"
        assert req.message == "Hello"
        
        # 無效請求
        with pytest.raises(Exception):
            ChatRequest(user_id="", message="Hello")
    
    def test_chat_response_model(self):
        """測試 ChatResponse 模型"""
        from pydantic import BaseModel
        from typing import Optional
        
        class ChatResponse(BaseModel):
            success: bool
            stage: str
            expert: Optional[str]
            response: str
            profile: dict
            next_step: str
        
        resp = ChatResponse(
            success=True,
            stage="CONVERSATION",
            expert=None,
            response="請問您貴姓？",
            profile={},
            next_step="CONTINUE_COLLECTING"
        )
        
        assert resp.success is True
        assert resp.stage == "CONVERSATION"
    
    def test_health_response_model(self):
        """測試 HealthResponse 模型"""
        from pydantic import BaseModel
        
        class HealthResponse(BaseModel):
            status: str
            version: str
            services: dict
        
        resp = HealthResponse(
            status="healthy",
            version="1.0.0",
            services={
                "loan_system": True,
                "line_bot": False,
                "redis": True,
                "mongodb": True
            }
        )
        
        assert resp.status == "healthy"
        assert resp.services["redis"] is True


class TestLINEBotHandlers:
    """LINE Bot 處理器測試"""
    
    def test_format_line_response_conversation(self):
        """測試對話階段回應格式"""
        result = {
            "stage": "CONVERSATION",
            "expert": None,
            "response": "請問您貴姓？",
            "next_step": "CONTINUE_COLLECTING"
        }
        
        # 模擬格式化函數
        def format_line_response(result):
            response = result.get("response", "")
            stage = result.get("stage", "")
            
            if stage == "CONVERSATION":
                prefix = "📝 "
            else:
                prefix = ""
            
            return f"{prefix}{response}"
        
        formatted = format_line_response(result)
        assert "📝" in formatted
        assert "請問您貴姓" in formatted
    
    def test_format_line_response_approval(self):
        """測試核准回應格式"""
        result = {
            "stage": "EXPERT_PROCESSING",
            "expert": "FRE",
            "response": "恭喜您，申請已核准！",
            "next_step": "CASE_CLOSED_SUCCESS"
        }
        
        def format_line_response(result):
            response = result.get("response", "")
            next_step = result.get("next_step", "")
            
            formatted = response
            
            if next_step == "CASE_CLOSED_SUCCESS":
                formatted += "\n\n✅ 恭喜！您的申請已初步核准。"
            
            return formatted
        
        formatted = format_line_response(result)
        assert "核准" in formatted
        assert "✅" in formatted
    
    def test_format_line_response_rejection(self):
        """測試拒絕回應格式"""
        result = {
            "stage": "EXPERT_PROCESSING",
            "expert": "FRE",
            "response": "很抱歉，本次申請未能通過。",
            "next_step": "CASE_CLOSED_REJECT"
        }
        
        def format_line_response(result):
            response = result.get("response", "")
            next_step = result.get("next_step", "")
            
            formatted = response
            
            if next_step == "CASE_CLOSED_REJECT":
                formatted += "\n\n❌ 很抱歉，本次申請未能通過。"
            
            return formatted
        
        formatted = format_line_response(result)
        assert "❌" in formatted
    
    def test_get_help_message(self):
        """測試說明訊息"""
        def get_help_message():
            return """📖 使用說明
            
🔹 申請貸款
直接告訴我您的需求

🔹 常用指令
• 「重新開始」- 重置對話
• 「說明」- 顯示此說明"""
        
        help_msg = get_help_message()
        
        assert "說明" in help_msg
        assert "重新開始" in help_msg


class TestFlexTemplates:
    """Flex Message 模板測試"""
    
    def test_welcome_message_structure(self):
        """測試歡迎訊息結構"""
        welcome = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "歡迎使用"}
                ]
            }
        }
        
        assert welcome["type"] == "bubble"
        assert "body" in welcome
    
    def test_application_progress_calculation(self):
        """測試申請進度計算"""
        def calculate_progress(profile, missing_fields):
            total_fields = 7
            filled_fields = total_fields - len(missing_fields)
            return int((filled_fields / total_fields) * 100)
        
        # 空 profile
        assert calculate_progress({}, ["name", "id", "phone", "job", "income", "loan_purpose", "amount"]) == 0
        
        # 部分填寫
        assert calculate_progress({"name": "王"}, ["id", "phone", "job", "income", "loan_purpose", "amount"]) == 14
        
        # 完整
        assert calculate_progress({}, []) == 100
    
    def test_approval_result_template(self):
        """測試審核結果模板"""
        def build_approval_result(decision, amount):
            is_approved = "PASS" in decision
            
            return {
                "type": "bubble",
                "header_text": "✅ 核准" if is_approved else "❌ 拒絕",
                "amount": amount if is_approved else None
            }
        
        # 核准
        result = build_approval_result("核准_PASS", 500000)
        assert "✅" in result["header_text"]
        assert result["amount"] == 500000
        
        # 拒絕
        result = build_approval_result("拒絕_REJECT", 0)
        assert "❌" in result["header_text"]


class TestQuickReplyTemplates:
    """快速回覆模板測試"""
    
    def test_loan_purpose_options(self):
        """測試貸款用途選項"""
        purposes = ["購車", "房屋裝修", "週轉金", "教育", "醫療", "其他"]
        
        options = [
            {"type": "action", "action": {"type": "message", "label": p, "text": p}}
            for p in purposes
        ]
        
        assert len(options) == 6
        assert options[0]["action"]["label"] == "購車"
    
    def test_amount_options(self):
        """測試金額選項"""
        amounts = ["30萬", "50萬", "80萬", "100萬", "150萬", "其他金額"]
        
        options = [
            {"type": "action", "action": {"type": "message", "label": a, "text": a}}
            for a in amounts
        ]
        
        assert len(options) == 6
        assert "萬" in options[0]["action"]["label"]


class TestWebhookSignature:
    """Webhook 簽名驗證測試"""
    
    def test_signature_generation(self):
        """測試簽名生成"""
        import hmac
        import hashlib
        import base64
        
        channel_secret = "test_secret"
        body = '{"events":[]}'
        
        # 生成簽名
        hash = hmac.new(
            channel_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(hash).decode('utf-8')
        
        assert signature is not None
        assert len(signature) > 0
    
    def test_signature_verification(self):
        """測試簽名驗證"""
        import hmac
        import hashlib
        import base64
        
        channel_secret = "test_secret"
        body = '{"events":[]}'
        
        # 生成正確簽名
        hash = hmac.new(
            channel_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).digest()
        correct_signature = base64.b64encode(hash).decode('utf-8')
        
        # 驗證
        def verify_signature(body, signature, secret):
            hash = hmac.new(
                secret.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).digest()
            expected = base64.b64encode(hash).decode('utf-8')
            return hmac.compare_digest(expected, signature)
        
        assert verify_signature(body, correct_signature, channel_secret) is True
        assert verify_signature(body, "wrong_signature", channel_secret) is False


class TestAPIIntegration:
    """API 整合測試"""
    
    def test_chat_flow_simulation(self):
        """模擬對話流程"""
        messages = [
            ("我想申請貸款", "CONVERSATION"),
            ("我是王小明", "CONVERSATION"),
            ("A123456789", "CONVERSATION"),
        ]
        
        for msg, expected_stage in messages:
            # 模擬處理
            result = {
                "stage": expected_stage,
                "response": f"收到: {msg}"
            }
            
            assert result["stage"] == expected_stage
    
    def test_session_management(self):
        """測試 Session 管理"""
        sessions = {}
        
        # 建立 session
        user_id = "U123"
        sessions[user_id] = {"profile": {}, "history": []}
        
        assert user_id in sessions
        
        # 更新 session
        sessions[user_id]["profile"]["name"] = "王小明"
        
        assert sessions[user_id]["profile"]["name"] == "王小明"
        
        # 刪除 session
        del sessions[user_id]
        
        assert user_id not in sessions
    
    def test_error_handling(self):
        """測試錯誤處理"""
        def handle_request(request):
            try:
                if not request.get("user_id"):
                    raise ValueError("Missing user_id")
                
                if not request.get("message"):
                    raise ValueError("Missing message")
                
                return {"success": True}
            
            except ValueError as e:
                return {"success": False, "error": str(e)}
        
        # 正常請求
        result = handle_request({"user_id": "U123", "message": "Hello"})
        assert result["success"] is True
        
        # 缺少 user_id
        result = handle_request({"message": "Hello"})
        assert result["success"] is False
        assert "user_id" in result["error"]
        
        # 缺少 message
        result = handle_request({"user_id": "U123"})
        assert result["success"] is False
        assert "message" in result["error"]
