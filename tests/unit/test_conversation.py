"""
conversation 模組單元測試
測試對話相關功能
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestFieldSchema:
    """欄位 Schema 測試"""
    
    def test_field_creation(self):
        """測試欄位建立"""
        from conversation.field_schema import Field
        
        field = Field("test_field", required=True, ftype=str)
        
        assert field.name == "test_field"
        assert field.required is True
        assert field.type == str
    
    def test_field_validation_string(self):
        """測試字串欄位驗證"""
        from conversation.field_schema import Field
        
        field = Field("name", required=True, ftype=str)
        
        is_valid, error = field.validate("王小明")
        assert is_valid is True
        assert error is None
        
        is_valid, error = field.validate(None)
        assert is_valid is False
        assert "必填" in error
    
    def test_field_validation_integer(self):
        """測試整數欄位驗證"""
        from conversation.field_schema import Field
        
        field = Field("income", required=True, ftype=int, validator=lambda x: x > 0)
        
        is_valid, error = field.validate(50000)
        assert is_valid is True
        
        is_valid, error = field.validate("50000")  # 字串也應能轉換
        assert is_valid is True
        
        is_valid, error = field.validate(-1000)
        assert is_valid is False
    
    def test_phone_validation(self):
        """測試手機號碼驗證"""
        from conversation.field_schema import Field
        
        field = Field("phone", validator="phone")
        
        # 有效格式
        assert field.validate("0912345678")[0] is True
        assert field.validate("09-1234-5678")[0] is True
        
        # 無效格式
        assert field.validate("1234567890")[0] is False
        assert field.validate("0812345678")[0] is False
    
    def test_id_validation(self):
        """測試身分證字號驗證"""
        from conversation.field_schema import Field
        
        field = Field("id", validator="id")
        
        # 有效格式
        assert field.validate("A123456789")[0] is True
        
        # 無效格式
        assert field.validate("123456789")[0] is False
        assert field.validate("A12345678")[0] is False


class TestFieldSchemaManager:
    """欄位 Schema 管理器測試"""
    
    def test_get_missing_fields_empty(self):
        """測試空 profile 的缺失欄位"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        profile = {}
        
        missing = schema.get_missing_fields(profile)
        
        # 應該回傳所有必填欄位
        assert "name" in missing
        assert "id" in missing
        assert "phone" in missing
        assert "job" in missing
        assert "income" in missing
        assert "loan_purpose" in missing
        assert "amount" in missing
    
    def test_get_missing_fields_partial(self):
        """測試部分填寫的缺失欄位"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        profile = {
            "name": "王小明",
            "id": "A123456789"
        }
        
        missing = schema.get_missing_fields(profile)
        
        assert "name" not in missing
        assert "id" not in missing
        assert "phone" in missing
    
    def test_get_missing_fields_complete(self):
        """測試完整填寫"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        profile = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912345678",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",
            "amount": 500000
        }
        
        missing = schema.get_missing_fields(profile)
        
        assert len(missing) == 0
    
    def test_field_priority_order(self):
        """測試欄位優先順序"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        profile = {}
        
        missing = schema.get_missing_fields(profile)
        
        # 應該按優先級排序
        # name (1) < id (2) < phone (3) < ...
        assert missing[0] == "name"
        assert missing[1] == "id"
        assert missing[2] == "phone"
    
    def test_all_required_filled(self):
        """測試全部必填檢查"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        
        incomplete = {"name": "王小明"}
        assert schema.all_required_filled(incomplete) is False
        
        complete = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912345678",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",
            "amount": 500000
        }
        assert schema.all_required_filled(complete) is True


class TestUtils:
    """工具函數測試"""
    
    def test_normalize_tw_phone_standard(self):
        """測試標準手機號碼正規化"""
        from conversation.utils import normalize_tw_phone
        
        assert normalize_tw_phone("0912345678") == "0912-345-678"
        assert normalize_tw_phone("0912-345-678") == "0912-345-678"
        assert normalize_tw_phone("0912 345 678") == "0912-345-678"
    
    def test_normalize_tw_phone_international(self):
        """測試國際格式手機號碼"""
        from conversation.utils import normalize_tw_phone
        
        assert normalize_tw_phone("+886912345678") == "0912-345-678"
        assert normalize_tw_phone("886912345678") == "0912-345-678"
    
    def test_normalize_tw_phone_invalid(self):
        """測試無效手機號碼"""
        from conversation.utils import normalize_tw_phone
        
        assert normalize_tw_phone("0812345678") is None  # 錯誤開頭
        assert normalize_tw_phone("091234567") is None   # 長度不足
        assert normalize_tw_phone("") is None
        assert normalize_tw_phone(None) is None
    
    def test_parse_tw_amount_wan(self):
        """測試萬元單位解析"""
        from conversation.utils import parse_tw_amount
        
        assert parse_tw_amount("5萬") == 50000
        assert parse_tw_amount("50萬") == 500000
        assert parse_tw_amount("1.5萬") == 15000
    
    def test_parse_tw_amount_k(self):
        """測試 K 單位解析"""
        from conversation.utils import parse_tw_amount
        
        assert parse_tw_amount("100k") == 100000
        assert parse_tw_amount("100K") == 100000
        assert parse_tw_amount("50k") == 50000
    
    def test_parse_tw_amount_m(self):
        """測試 M 單位解析"""
        from conversation.utils import parse_tw_amount
        
        assert parse_tw_amount("1m") == 1000000
        assert parse_tw_amount("1.5M") == 1500000
    
    def test_parse_tw_amount_pure_number(self):
        """測試純數字解析"""
        from conversation.utils import parse_tw_amount
        
        assert parse_tw_amount("50000") == 50000
        assert parse_tw_amount("1,000,000") == 1000000
        assert parse_tw_amount(50000) == 50000
    
    def test_validate_tw_id_valid(self):
        """測試有效身分證字號"""
        from conversation.utils import validate_tw_id
        
        # 這些是格式正確的測試用號碼
        assert validate_tw_id("A123456789") is True
        assert validate_tw_id("B223456789") is True
    
    def test_validate_tw_id_invalid(self):
        """測試無效身分證字號"""
        from conversation.utils import validate_tw_id
        
        assert validate_tw_id("123456789") is False   # 缺少英文
        assert validate_tw_id("A12345678") is False   # 長度不足
        assert validate_tw_id("AA12345678") is False  # 兩個英文
        assert validate_tw_id("") is False
        assert validate_tw_id(None) is False


class TestGeminiClient:
    """Gemini Client 測試"""
    
    def test_ask_question_standard(self):
        """測試標準問題生成"""
        from conversation.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        question = client.ask_question("name", "standard")
        assert "姓名" in question
        
        question = client.ask_question("income", "standard")
        assert "收入" in question
    
    def test_ask_question_retry(self):
        """測試重試問題生成"""
        from conversation.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        question = client.ask_question("phone", "retry")
        assert "09" in question or "手機" in question
    
    def test_ask_question_unknown_field(self):
        """測試未知欄位"""
        from conversation.gemini_client import GeminiClient
        
        client = GeminiClient()
        
        question = client.ask_question("unknown_field", "standard")
        assert "unknown_field" in question
    
    @patch('conversation.gemini_client.client.models.generate_content')
    def test_extract_slots_success(self, mock_generate):
        """測試欄位抽取成功"""
        from conversation.gemini_client import GeminiClient
        
        mock_response = MagicMock()
        mock_response.text = '{"name": "王小明", "income": 50000}'
        mock_generate.return_value = mock_response
        
        client = GeminiClient()
        result = client.extract_slots("我叫王小明，月薪5萬", ["name", "income"])
        
        assert result.get("name") == "王小明"
        assert result.get("income") == 50000
    
    @patch('conversation.gemini_client.client.models.generate_content')
    def test_extract_slots_with_amount_conversion(self, mock_generate):
        """測試金額轉換"""
        from conversation.gemini_client import GeminiClient
        
        mock_response = MagicMock()
        mock_response.text = '{"amount": "50萬"}'
        mock_generate.return_value = mock_response
        
        client = GeminiClient()
        result = client.extract_slots("想借50萬", ["amount"])
        
        assert result.get("amount") == 500000


class TestConversationManager:
    """對話管理器測試"""
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock Session Manager"""
        mock = MagicMock()
        mock.get_profile.return_value = {
            "name": None,
            "id": None,
            "phone": None,
            "job": None,
            "income": None,
            "loan_purpose": None,
            "amount": None,
            "last_asked_field": None,
            "retry_count": 0
        }
        mock.get_history.return_value = []
        mock.update_profile.return_value = mock.get_profile.return_value
        return mock
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini Client"""
        mock = MagicMock()
        mock.ask_question.return_value = "請問您的姓名是?"
        mock.extract_slots.return_value = {}
        return mock
    
    def test_handle_turn_collecting(self, mock_session_manager, mock_gemini_client):
        """測試資料收集中的狀態"""
        from conversation.conversation_manager import ConversationManager
        from conversation.field_schema import FieldSchema
        
        manager = ConversationManager(
            mock_session_manager,
            FieldSchema(),
            mock_gemini_client
        )
        
        result = manager.handle_turn("user_001", "你好")
        
        assert result["status"] == "COLLECTING"
        assert "response" in result
        assert "missing_fields" in result
    
    def test_handle_turn_ready_for_moe(self, mock_session_manager, mock_gemini_client):
        """測試資料收集完成"""
        from conversation.conversation_manager import ConversationManager
        from conversation.field_schema import FieldSchema
        
        # 設定完整 profile
        mock_session_manager.get_profile.return_value = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912345678",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",
            "amount": 500000,
            "last_asked_field": None,
            "retry_count": 0
        }
        
        manager = ConversationManager(
            mock_session_manager,
            FieldSchema(),
            mock_gemini_client
        )
        
        result = manager.handle_turn("user_001", "完成")
        
        assert result["status"] == "READY_FOR_MOE"
        assert "summary" in result
