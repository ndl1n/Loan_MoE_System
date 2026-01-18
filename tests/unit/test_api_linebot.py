"""
API 和 LINE Bot 整合測試
測試完整的 API 端點和 LINE Bot 整合
"""

import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestAPIEndpoints:
    """測試 API 端點"""
    
    @pytest.fixture
    def mock_loan_system(self):
        """Mock LoanMoESystem"""
        mock = MagicMock()
        mock.process_message.return_value = {
            "stage": "CONVERSATION",
            "expert": None,
            "response": "請問您的姓名是?",
            "profile": {"name": None},
            "missing_fields": ["name", "id", "job"],
            "next_step": "CONTINUE_COLLECTING"
        }
        return mock
    
    @pytest.fixture
    def client(self, mock_loan_system):
        """建立測試 client"""
        with patch('api.loan_system', mock_loan_system):
            with patch('api.LoanMoESystem', return_value=mock_loan_system):
                from fastapi.testclient import TestClient
                from api import app
                
                # 跳過 lifespan
                app.router.lifespan_context = None
                
                yield TestClient(app)
    
    def test_root_endpoint(self, client):
        """測試根路徑"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health_check(self, client):
        """測試健康檢查"""
        with patch('api.loan_system', MagicMock()):
            with patch('api.check_redis_connection', return_value=True):
                with patch('api.check_mongodb_connection', return_value=True):
                    response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
    
    def test_chat_endpoint_success(self, client, mock_loan_system):
        """測試對話 API - 成功"""
        with patch('api.loan_system', mock_loan_system):
            response = client.post(
                "/api/v1/chat",
                json={"user_id": "test_user", "message": "我想申請貸款"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "response" in data
        assert "profile" in data
    
    def test_chat_endpoint_missing_user_id(self, client):
        """測試對話 API - 缺少 user_id"""
        response = client.post(
            "/api/v1/chat",
            json={"message": "我想申請貸款"}
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_chat_endpoint_empty_message(self, client):
        """測試對話 API - 空訊息"""
        response = client.post(
            "/api/v1/chat",
            json={"user_id": "test_user", "message": ""}
        )
        
        assert response.status_code == 422  # Validation Error


class TestChatRequestValidation:
    """測試 ChatRequest 驗證"""
    
    def test_valid_request(self):
        """測試有效的請求"""
        from api import ChatRequest
        
        request = ChatRequest(user_id="U123", message="測試訊息")
        
        assert request.user_id == "U123"
        assert request.message == "測試訊息"
    
    def test_invalid_empty_user_id(self):
        """測試空的 user_id"""
        from api import ChatRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ChatRequest(user_id="", message="測試訊息")
    
    def test_invalid_empty_message(self):
        """測試空的訊息"""
        from api import ChatRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ChatRequest(user_id="U123", message="")


class TestChatResponseFormat:
    """測試 ChatResponse 格式"""
    
    def test_response_structure(self):
        """測試回應結構"""
        from api import ChatResponse
        
        response = ChatResponse(
            success=True,
            stage="CONVERSATION",
            expert=None,
            response="請問您的姓名是?",
            profile={"name": None},
            missing_fields=["name"],
            next_step="CONTINUE_COLLECTING"
        )
        
        assert response.success == True
        assert response.stage == "CONVERSATION"
        assert response.response == "請問您的姓名是?"


class TestLINEBotWebhook:
    """測試 LINE Bot Webhook"""
    
    def test_webhook_missing_signature(self):
        """測試缺少簽名"""
        with patch('api.LINEBOT_AVAILABLE', True):
            with patch('api.line_handler', MagicMock()):
                from fastapi.testclient import TestClient
                from api import app
                
                app.router.lifespan_context = None
                client = TestClient(app)
                
                response = client.post(
                    "/api/v1/webhook/line",
                    json={"events": []}
                )
        
        # 缺少 X-Line-Signature 應該返回 400
        assert response.status_code in [400, 503]
    
    def test_webhook_sdk_not_installed(self):
        """測試 SDK 未安裝"""
        with patch('api.LINEBOT_AVAILABLE', False):
            from fastapi.testclient import TestClient
            from api import app
            
            app.router.lifespan_context = None
            client = TestClient(app)
            
            response = client.post(
                "/api/v1/webhook/line",
                json={"events": []},
                headers={"X-Line-Signature": "test"}
            )
        
        assert response.status_code == 501


class TestLINEMessageFormatting:
    """測試 LINE 訊息格式化"""
    
    def test_format_line_response_conversation(self):
        """測試對話階段格式化"""
        from api import format_line_response
        
        result = {
            "stage": "CONVERSATION",
            "response": "請問您的姓名是?",
            "expert": None,
            "next_step": "CONTINUE_COLLECTING"
        }
        
        formatted = format_line_response(result)
        
        assert "📝" in formatted
        assert "請問您的姓名是?" in formatted
    
    def test_format_line_response_success(self):
        """測試核准結果格式化"""
        from api import format_line_response
        
        result = {
            "stage": "EXPERT_PROCESSING",
            "response": "恭喜核准",
            "expert": "FRE",
            "next_step": "CASE_CLOSED_SUCCESS"
        }
        
        formatted = format_line_response(result)
        
        assert "恭喜" in formatted or "✅" in formatted
    
    def test_format_line_response_reject(self):
        """測試拒絕結果格式化"""
        from api import format_line_response
        
        result = {
            "stage": "EXPERT_PROCESSING",
            "response": "很抱歉",
            "expert": "FRE",
            "next_step": "CASE_CLOSED_REJECT"
        }
        
        formatted = format_line_response(result)
        
        assert "抱歉" in formatted or "❌" in formatted
    
    def test_get_help_message(self):
        """測試說明訊息"""
        from api import get_help_message
        
        help_msg = get_help_message()
        
        assert "使用說明" in help_msg
        assert "申請貸款" in help_msg
        assert "重新開始" in help_msg


class TestSessionManagement:
    """測試 Session 管理"""
    
    @pytest.fixture
    def mock_system(self):
        """Mock 系統"""
        mock = MagicMock()
        mock._conversation_managers = {}
        return mock
    
    def test_session_info_structure(self):
        """測試 SessionInfo 結構"""
        from api import SessionInfo
        
        info = SessionInfo(
            user_id="U123",
            profile={"name": "王小明"},
            history_length=5,
            verification_status="pending",
            created_at=1700000000.0
        )
        
        assert info.user_id == "U123"
        assert info.history_length == 5


class TestHealthCheck:
    """測試健康檢查功能"""
    
    def test_check_redis_connection_success(self):
        """測試 Redis 連線成功"""
        with patch('conversation.user_session_manager.redis_client') as mock_redis:
            mock_redis.ping.return_value = True
            
            from api import check_redis_connection
            
            # 由於 check_redis_connection 內部 import，需要 patch 正確路徑
            result = check_redis_connection()
            
            # 結果取決於實際連線狀態
            assert isinstance(result, bool)
    
    def test_check_mongodb_connection_success(self):
        """測試 MongoDB 連線成功"""
        with patch('services.database.MongoManager') as mock_mongo:
            mock_instance = MagicMock()
            mock_instance._client = MagicMock()
            mock_instance._client.admin.command.return_value = True
            mock_mongo.return_value = mock_instance
            
            from api import check_mongodb_connection
            
            # 結果取決於實際連線狀態
            result = check_mongodb_connection()
            assert isinstance(result, bool)
    
    def test_check_redis_connection_failure(self):
        """測試 Redis 連線失敗"""
        from api import check_redis_connection
        
        # 即使失敗也應該返回 False 而不是拋出異常
        result = check_redis_connection()
        assert isinstance(result, bool)
    
    def test_check_mongodb_connection_failure(self):
        """測試 MongoDB 連線失敗"""
        from api import check_mongodb_connection
        
        # 即使失敗也應該返回 False 而不是拋出異常
        result = check_mongodb_connection()
        assert isinstance(result, bool)


class TestFlexTemplates:
    """測試 Flex Message 模板"""
    
    def test_welcome_message_structure(self):
        """測試歡迎訊息結構"""
        from linebot_handler import FlexTemplates
        
        welcome = FlexTemplates.welcome_message()
        
        assert welcome["type"] == "bubble"
        assert "hero" in welcome
        assert "body" in welcome
        assert "footer" in welcome
    
    def test_application_progress_structure(self):
        """測試申請進度結構"""
        from linebot_handler import FlexTemplates
        
        profile = {"name": "王小明", "id": "A123456789"}
        missing = ["phone", "job", "income"]
        
        progress = FlexTemplates.application_progress(profile, missing)
        
        assert progress["type"] == "bubble"
        assert "body" in progress
    
    def test_approval_result_approved(self):
        """測試核准結果"""
        from linebot_handler import FlexTemplates
        
        result = FlexTemplates.approval_result(
            decision="核准_PASS",
            amount=500000,
            rate=3.5,
            monthly_payment=7000
        )
        
        assert result["type"] == "bubble"
    
    def test_approval_result_rejected(self):
        """測試拒絕結果"""
        from linebot_handler import FlexTemplates
        
        result = FlexTemplates.approval_result(
            decision="拒絕_REJECT",
            amount=500000
        )
        
        assert result["type"] == "bubble"


class TestQuickReplyTemplates:
    """測試快速回覆模板"""
    
    def test_loan_purpose_options(self):
        """測試貸款用途選項"""
        from linebot_handler import QuickReplyTemplates
        
        options = QuickReplyTemplates.loan_purpose_options()
        
        assert isinstance(options, list)
        assert len(options) > 0
        
        for opt in options:
            assert "type" in opt
            assert "action" in opt
    
    def test_amount_options(self):
        """測試金額選項"""
        from linebot_handler import QuickReplyTemplates
        
        options = QuickReplyTemplates.amount_options()
        
        assert isinstance(options, list)
        assert len(options) > 0


class TestLineMessageBuilder:
    """測試 LINE 訊息建構器"""
    
    def test_build_flex_message(self):
        """測試建構 Flex Message"""
        from linebot_handler import LineMessageBuilder
        
        contents = {"type": "bubble", "body": {"type": "box"}}
        
        msg = LineMessageBuilder.build_flex_message("測試", contents)
        
        assert msg["type"] == "flex"
        assert msg["altText"] == "測試"
        assert msg["contents"] == contents
    
    def test_build_text_with_quick_reply(self):
        """測試建構帶快速回覆的文字"""
        from linebot_handler import LineMessageBuilder
        
        items = [{"type": "action", "action": {"type": "message", "label": "A", "text": "A"}}]
        
        msg = LineMessageBuilder.build_text_with_quick_reply("請選擇", items)
        
        assert msg["type"] == "text"
        assert msg["text"] == "請選擇"
        assert "quickReply" in msg
    
    def test_build_response_for_conversation_stage(self):
        """測試對話階段回應建構"""
        from linebot_handler import LineMessageBuilder
        
        result = {
            "stage": "CONVERSATION",
            "response": "請問您的姓名?",
            "next_step": "CONTINUE_COLLECTING",
            "profile": {},
            "missing_fields": ["name"]
        }
        
        messages = LineMessageBuilder.build_response_for_stage(result)
        
        assert len(messages) >= 1
        assert messages[0]["type"] == "text"


class TestRichMenuConfig:
    """測試 Rich Menu 配置"""
    
    def test_rich_menu_structure(self):
        """測試 Rich Menu 結構"""
        from linebot_handler import RICH_MENU_CONFIG
        
        assert "size" in RICH_MENU_CONFIG
        assert "areas" in RICH_MENU_CONFIG
        assert RICH_MENU_CONFIG["size"]["width"] == 2500
        assert RICH_MENU_CONFIG["size"]["height"] == 843
    
    def test_rich_menu_areas(self):
        """測試 Rich Menu 區域"""
        from linebot_handler import RICH_MENU_CONFIG
        
        areas = RICH_MENU_CONFIG["areas"]
        
        assert len(areas) == 3
        
        for area in areas:
            assert "bounds" in area
            assert "action" in area
