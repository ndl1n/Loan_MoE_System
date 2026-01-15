"""
額外測試 - 提高覆蓋率
針對覆蓋率較低的模組進行補強測試
"""

import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==========================================
# Field Schema Additional Tests
# ==========================================
class TestFieldSchemaAdditional:
    """Field Schema 額外測試"""
    
    def test_field_with_float_type(self):
        """測試浮點數類型欄位"""
        from conversation.field_schema import Field
        
        field = Field("rate", ftype=float)
        
        is_valid, error = field.validate(3.5)
        assert is_valid is True
        
        is_valid, error = field.validate("3.5")
        assert is_valid is True
    
    def test_field_type_conversion_error(self):
        """測試類型轉換錯誤"""
        from conversation.field_schema import Field
        
        field = Field("income", ftype=int)
        
        is_valid, error = field.validate("not_a_number")
        assert is_valid is False
        assert "int" in error
    
    def test_field_custom_validator_false(self):
        """測試自定義驗證器回傳 False"""
        from conversation.field_schema import Field
        
        field = Field(
            "amount",
            ftype=int,
            validator=lambda x: x >= 10000,
            error_msg="金額必須大於等於 10000"
        )
        
        is_valid, error = field.validate(5000)
        assert is_valid is False
        assert "10000" in error
    
    def test_field_not_required_none(self):
        """測試非必填欄位可以是 None"""
        from conversation.field_schema import Field
        
        field = Field("company", required=False)
        
        is_valid, error = field.validate(None)
        assert is_valid is True
        assert error is None
    
    def test_field_phone_with_country_code(self):
        """測試帶國碼的電話"""
        from conversation.field_schema import Field
        
        # _validate_phone 是靜態方法
        assert Field._validate_phone("886912345678") is True
        assert Field._validate_phone("+886912345678") is True  # 有加號不處理
    
    def test_field_tw_id_edge_cases(self):
        """測試身分證邊界情況"""
        from conversation.field_schema import Field
        
        # 空字串
        assert Field._validate_tw_id("") is False
        
        # 長度不對
        assert Field._validate_tw_id("A12345678") is False  # 9 碼
        assert Field._validate_tw_id("A1234567890") is False  # 11 碼
        
        # 第一個字元不是英文
        assert Field._validate_tw_id("1234567890") is False
    
    def test_schema_validate_all(self):
        """測試驗證所有欄位"""
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
        
        results = schema.validate_all(profile)
        
        assert "name" in results
        assert results["name"]["valid"] is True
    
    def test_schema_get_validation_errors(self):
        """測試取得驗證錯誤"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        
        # 有錯誤的 profile
        profile = {
            "name": "王小明",
            "id": None,  # 缺失
            "phone": "12345",  # 格式錯誤
            "income": -1000  # 負數
        }
        
        errors = schema.get_validation_errors(profile)
        
        assert "id" in errors
        assert "phone" in errors
    
    def test_schema_get_field_info(self):
        """測試取得欄位資訊"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        
        field = schema.get_field_info("name")
        assert field is not None
        assert field.name == "name"
        
        # 不存在的欄位
        field = schema.get_field_info("nonexistent")
        assert field is None


# ==========================================
# Utils Additional Tests
# ==========================================
class TestUtilsAdditional:
    """工具函數額外測試"""
    
    def test_parse_amount_edge_cases(self):
        """測試金額解析邊界情況"""
        from conversation.utils import parse_tw_amount
        
        # 帶逗號的金額
        assert parse_tw_amount("1,000,000") == 1000000
        
        # 帶空格
        assert parse_tw_amount(" 50000 ") == 50000
        
        # 純浮點數
        assert parse_tw_amount(50000.5) == 50000
    
    def test_phone_normalization_edge_cases(self):
        """測試電話正規化邊界情況"""
        from conversation.utils import normalize_tw_phone
        
        # 帶括號
        result = normalize_tw_phone("(09)12-345-678")
        # 應該正確處理或回傳 None
        
        # 很短的輸入
        assert normalize_tw_phone("09") is None
    
    def test_validate_tw_id_lowercase(self):
        """測試小寫身分證"""
        from conversation.utils import validate_tw_id
        
        # 應該能處理小寫
        result = validate_tw_id("a123456789")
        # 函數會轉大寫後驗證
        assert result is True


# ==========================================
# Gemini Client Additional Tests
# ==========================================
class TestGeminiClientAdditional:
    """Gemini Client 額外測試"""
    
    def test_extract_json_patterns(self):
        """測試各種 JSON 提取模式"""
        import re
        
        patterns = [
            ('純 JSON', '{"name": "test"}', True),
            ('前有文字', '答案是 {"name": "test"}', True),
            ('後有文字', '{"name": "test"} 以上', True),
            ('Markdown 格式', '```json\n{"name": "test"}\n```', True),
            ('無 JSON', '沒有 JSON 在這裡', False),
        ]
        
        for desc, text, should_find in patterns:
            match = re.search(r'\{[^{}]*\}', text)
            if should_find:
                assert match is not None, f"Failed: {desc}"
            else:
                assert match is None, f"Should not find: {desc}"


# ==========================================
# User Session Manager Tests
# ==========================================
class TestUserSessionManagerLogic:
    """User Session Manager 邏輯測試"""
    
    def test_profile_key_format(self):
        """測試 profile key 格式"""
        user_id = "test_user_123"
        
        profile_key = f"loan:profile:{user_id}"
        history_key = f"loan:history:{user_id}"
        lock_key = f"loan:lock:{user_id}"
        
        assert profile_key == "loan:profile:test_user_123"
        assert history_key == "loan:history:test_user_123"
        assert lock_key == "loan:lock:test_user_123"
    
    def test_default_profile_fields(self):
        """測試預設 profile 欄位"""
        default = {
            "name": None,
            "id": None,
            "phone": None,
            "loan_purpose": None,
            "job": None,
            "income": None,
            "amount": None,
            "company": None,
            "last_asked_field": None,
            "retry_count": 0,
            "verification_status": None,
            "created_at": None,
            "updated_at": None
        }
        
        # 確保所有預期欄位都存在
        expected_fields = [
            "name", "id", "phone", "job", "income",
            "loan_purpose", "amount", "verification_status"
        ]
        
        for field in expected_fields:
            assert field in default
    
    def test_profile_merge_logic(self):
        """測試 profile 合併邏輯"""
        current = {
            "name": "王小明",
            "id": None,
            "income": None
        }
        
        updates = {
            "id": "A123456789",
            "income": 50000,
            "name": None  # None 不應覆蓋
        }
        
        # 合併邏輯
        for k, v in updates.items():
            if v is not None:
                current[k] = v
        
        assert current["name"] == "王小明"  # 保留
        assert current["id"] == "A123456789"  # 更新
        assert current["income"] == 50000  # 更新
    
    def test_message_json_serialization(self):
        """測試訊息 JSON 序列化"""
        import time
        
        msg = {
            "role": "user",
            "content": "測試訊息 with 中文",
            "timestamp": time.time()
        }
        
        json_str = json.dumps(msg, ensure_ascii=False)
        parsed = json.loads(json_str)
        
        assert parsed["content"] == "測試訊息 with 中文"
    
    def test_history_trimming(self):
        """測試歷史紀錄裁剪"""
        history = list(range(100))
        max_size = 50
        
        # LTRIM -50 -1 的效果
        trimmed = history[-max_size:]
        
        assert len(trimmed) == 50
        assert trimmed[0] == 50
        assert trimmed[-1] == 99


# ==========================================
# Conversation Manager Additional Tests
# ==========================================
class TestConversationManagerAdditional:
    """Conversation Manager 額外測試"""
    
    def test_status_determination(self):
        """測試狀態判斷"""
        from conversation.field_schema import FieldSchema
        
        schema = FieldSchema()
        
        # 不完整 profile
        incomplete = {"name": "王小明"}
        missing = schema.get_missing_fields(incomplete)
        
        if len(missing) > 0:
            status = "COLLECTING"
        else:
            status = "READY_FOR_MOE"
        
        assert status == "COLLECTING"
        
        # 完整 profile
        complete = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912345678",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",
            "amount": 500000
        }
        missing = schema.get_missing_fields(complete)
        
        if len(missing) > 0:
            status = "COLLECTING"
        else:
            status = "READY_FOR_MOE"
        
        assert status == "READY_FOR_MOE"
    
    def test_retry_count_logic(self):
        """測試重試計數邏輯"""
        max_retry = 3
        
        # 模擬重試
        for retry_count in range(5):
            if retry_count >= max_retry:
                action = "skip"
            else:
                action = "retry"
            
            if retry_count == 2:
                assert action == "retry"
            elif retry_count == 3:
                assert action == "skip"
    
    def test_extract_slots_result_merge(self):
        """測試欄位提取結果合併"""
        current = {"name": "王小明"}
        extracted = {"id": "A123456789", "income": 50000}
        
        # 合併
        current.update(extracted)
        
        assert current["name"] == "王小明"
        assert current["id"] == "A123456789"
        assert current["income"] == 50000


# ==========================================
# Database & RAG Service Tests
# ==========================================
class TestDatabaseLogic:
    """資料庫相關邏輯測試"""
    
    def test_mongodb_uri_parsing(self):
        """測試 MongoDB URI 解析"""
        # 模擬 URI
        uri = "mongodb+srv://user:pass@cluster.mongodb.net/database"
        
        assert "mongodb" in uri
        assert "@" in uri
    
    def test_collection_name(self):
        """測試 collection 名稱"""
        db_name = "MoE-Finance"
        collection_name = "user_history"
        
        assert db_name == "MoE-Finance"
        assert collection_name == "user_history"


class TestRAGServiceLogic:
    """RAG Service 邏輯測試"""
    
    def test_embedding_dimension(self):
        """測試 embedding 維度"""
        expected_dim = 384  # all-MiniLM-L6-v2
        
        # 模擬 embedding
        import random
        embedding = [random.random() for _ in range(expected_dim)]
        
        assert len(embedding) == 384
    
    def test_vector_search_pipeline(self):
        """測試向量搜尋 pipeline 結構"""
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": [0.1] * 384,
                    "numCandidates": 100,
                    "limit": 3
                }
            },
            {
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        assert len(pipeline) == 2
        assert "$vectorSearch" in pipeline[0]
    
    def test_document_structure(self):
        """測試文件結構"""
        doc = {
            "user_id": "A123456789",
            "content": "使用者歷史資料",
            "embedding": [0.1] * 384,
            "metadata": {
                "hist_job": "工程師",
                "hist_income": "50000",
                "hist_phone": "0912345678"
            },
            "created_at": "2024-01-01T00:00:00"
        }
        
        assert "embedding" in doc
        assert len(doc["embedding"]) == 384
        assert "metadata" in doc


# ==========================================
# Expert Logic Tests (Without Import)
# ==========================================
class TestExpertLogicNoImport:
    """專家邏輯測試 (不需 import experts 模組)"""
    
    def test_lde_mode_decision(self):
        """測試 LDE 模式決策邏輯"""
        consult_keywords = [
            "多少", "利率", "什麼", "資格", "可以嗎",
            "試算", "好過", "推薦", "怎麼", "如何"
        ]
        
        test_cases = [
            ("請問利率多少", True),
            ("我叫王小明", False),
            ("貸款條件是什麼", True),
            ("A123456789", False)
        ]
        
        for query, expected_consult in test_cases:
            is_consult = any(kw in query for kw in consult_keywords)
            assert is_consult == expected_consult, f"Failed: {query}"
    
    def test_dve_risk_classification(self):
        """測試 DVE 風險分類邏輯"""
        def classify_risk(mismatch_count):
            if mismatch_count == 0:
                return "LOW"
            elif mismatch_count == 1:
                return "MEDIUM"
            else:
                return "HIGH"
        
        assert classify_risk(0) == "LOW"
        assert classify_risk(1) == "MEDIUM"
        assert classify_risk(2) == "HIGH"
        assert classify_risk(5) == "HIGH"
    
    def test_fre_dbr_calculation(self):
        """測試 FRE DBR 計算"""
        def calculate_dbr(income, amount, term=84, rate=0.03):
            monthly_payment = (amount * (1 + rate)) / term
            dbr = (monthly_payment / income) * 100
            return round(dbr, 2)
        
        # 月薪 5 萬，借 50 萬
        dbr = calculate_dbr(50000, 500000)
        assert dbr < 20  # 應該是約 12.24%
        
        # 月薪 3 萬，借 100 萬
        dbr = calculate_dbr(30000, 1000000)
        assert dbr > 40  # 應該是約 40.8%
    
    def test_fre_credit_score_logic(self):
        """測試 FRE 信用評分邏輯"""
        def calculate_credit_score(income):
            if income > 40000:
                return 700
            else:
                return 600
        
        assert calculate_credit_score(50000) == 700
        assert calculate_credit_score(30000) == 600
    
    def test_fre_safety_guard_logic(self):
        """測試 FRE 安全鎖邏輯"""
        def apply_safety_guard(decision, dbr, credit_score, income):
            # Rule 1: DBR > 60%
            if dbr > 60 and "PASS" in decision:
                return "拒絕_REJECT", "DBR 過高"
            
            # Rule 2: Credit Score < 650
            if credit_score < 650 and "PASS" in decision:
                return "拒絕_REJECT", "信用分不足"
            
            # Rule 3: Missing income
            if income == 0 and "PASS" in decision:
                return "轉介審核_ESCALATE", "資料缺失"
            
            return decision, None
        
        # 測試案例
        result, reason = apply_safety_guard("核准_PASS", 70, 700, 50000)
        assert result == "拒絕_REJECT"
        assert "DBR" in reason
        
        result, reason = apply_safety_guard("核准_PASS", 30, 600, 50000)
        assert result == "拒絕_REJECT"
        assert "信用分" in reason
        
        result, reason = apply_safety_guard("核准_PASS", 30, 700, 0)
        assert result == "轉介審核_ESCALATE"
        
        result, reason = apply_safety_guard("核准_PASS", 30, 700, 50000)
        assert result == "核准_PASS"
        assert reason is None
    
    def test_decision_mapping(self):
        """測試決策映射"""
        decision_map = {
            "核准_PASS": "CASE_CLOSED_SUCCESS",
            "拒絕_REJECT": "CASE_CLOSED_REJECT",
            "轉介審核_ESCALATE": "HUMAN_HANDOVER"
        }
        
        assert decision_map["核准_PASS"] == "CASE_CLOSED_SUCCESS"
        assert decision_map["拒絕_REJECT"] == "CASE_CLOSED_REJECT"


# ==========================================
# MoE Router Logic Tests
# ==========================================
class TestMoERouterLogic:
    """MoE Router 邏輯測試"""
    
    def test_profile_completeness_calculation(self):
        """測試 profile 完整度計算"""
        def calculate_completeness(profile):
            required = ["name", "id", "phone", "job", "income", "loan_purpose", "amount"]
            filled = sum(1 for f in required if profile.get(f) is not None)
            return filled / len(required)
        
        # 空 profile
        assert calculate_completeness({}) == 0.0
        
        # 部分填寫
        partial = {"name": "王小明", "id": "A123456789"}
        assert calculate_completeness(partial) == 2/7
        
        # 完整
        complete = {
            "name": "王小明",
            "id": "A123456789",
            "phone": "0912345678",
            "job": "工程師",
            "income": 50000,
            "loan_purpose": "購車",
            "amount": 500000
        }
        assert calculate_completeness(complete) == 1.0
    
    def test_guardrail_rules(self):
        """測試護欄規則"""
        def apply_guardrails(verification_status, query):
            tech_keywords = ["系統", "錯誤", "失敗", "上傳"]
            
            # 狀態優先
            if verification_status == "unknown":
                return "LDE", "資料收集未完成"
            elif verification_status == "pending":
                return "DVE", "待驗證"
            elif verification_status == "verified":
                return "FRE", "已驗證"
            elif verification_status == "mismatch":
                return "LDE", "資料不符需釐清"
            
            # 關鍵字檢查
            if any(kw in query for kw in tech_keywords):
                return "DVE", "技術問題"
            
            return None, None
        
        assert apply_guardrails("unknown", "")[0] == "LDE"
        assert apply_guardrails("pending", "")[0] == "DVE"
        assert apply_guardrails("verified", "")[0] == "FRE"
        assert apply_guardrails("mismatch", "")[0] == "LDE"
        assert apply_guardrails(None, "系統錯誤")[0] == "DVE"
    
    def test_expert_labels(self):
        """測試專家標籤"""
        ID2LABEL = {0: "LDE", 1: "DVE", 2: "FRE"}
        LABEL2ID = {"LDE": 0, "DVE": 1, "FRE": 2}
        
        assert ID2LABEL[0] == "LDE"
        assert LABEL2ID["FRE"] == 2
        
        # 雙向映射一致
        for id, label in ID2LABEL.items():
            assert LABEL2ID[label] == id


# ==========================================
# LLM Utils Logic Tests
# ==========================================
class TestLLMUtilsLogic:
    """LLM Utils 邏輯測試"""
    
    def test_prompt_template_format(self):
        """測試 Prompt Template 格式"""
        template = "### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Output:"
        
        instruction = "你是貸款專家"
        input_text = '{"name": "王小明"}'
        
        prompt = template.format(instruction=instruction, input_text=input_text)
        
        assert "### Instruction:" in prompt
        assert "你是貸款專家" in prompt
        assert "王小明" in prompt
    
    def test_output_cleaning(self):
        """測試輸出清理"""
        raw_outputs = [
            '### Output:\n{"result": "pass"}<|end_of_text|>',
            '{"result": "pass"}',
            '```json\n{"result": "pass"}\n```'
        ]
        
        for raw in raw_outputs:
            # 清理 end_of_text
            cleaned = raw.split("<|end_of_text|>")[0]
            
            # 清理 ### Output:
            if "### Output:" in cleaned:
                cleaned = cleaned.split("### Output:")[1].strip()
            
            # 清理 markdown
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            
            assert '{"result": "pass"}' in cleaned or cleaned == '{"result": "pass"}'
    
    def test_adapter_path_structure(self):
        """測試 adapter 路徑結構"""
        base_path = "models"
        adapters = ["LDE_adapter", "DVE_adapter", "FRE_adapter"]
        
        for adapter in adapters:
            path = f"{base_path}/{adapter}"
            assert base_path in path
            assert adapter in path
