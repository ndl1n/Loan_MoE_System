"""
RAG Service 完整測試
測試兩個 Collection 的運作
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestRAGServiceCollections:
    """測試 RAG Service 的兩個 Collection"""
    
    def test_collection_names(self):
        """測試 Collection 名稱設定"""
        from services.rag_service import RAGService
        
        service = RAGService()
        
        assert service.USER_HISTORY_COLLECTION == "user_history"
        assert service.CASE_LIBRARY_COLLECTION == "case_library"
    
    def test_similarity_threshold(self):
        """測試相似度閾值"""
        from services.rag_service import RAGService
        
        service = RAGService()
        
        assert service.SIMILARITY_THRESHOLD == 0.5
        assert 0 < service.SIMILARITY_THRESHOLD < 1


class TestUserHistoryCollection:
    """測試 user_history Collection (DVE 用)"""
    
    @pytest.fixture
    def mock_rag_service(self):
        """建立 mock RAG service"""
        with patch('services.rag_service.mongo_db') as mock_db:
            mock_collection = MagicMock()
            mock_db.get_collection.return_value = mock_collection
            
            from services.rag_service import RAGService
            service = RAGService()
            service._user_history = mock_collection
            service._initialized = True
            
            return service, mock_collection
    
    def test_add_user_record(self, mock_rag_service):
        """測試新增用戶紀錄"""
        service, mock_collection = mock_rag_service
        mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
        
        result = service.add_user_record(
            user_id="A123456789",
            content="測試內容",
            metadata={"name": "王小明"},
            doc_type="application"
        )
        
        assert result == "test_id"
        mock_collection.insert_one.assert_called_once()
    
    def test_get_user_history_by_id(self, mock_rag_service):
        """測試根據 ID 查詢用戶歷史"""
        service, mock_collection = mock_rag_service
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = [
            {"user_id": "A123456789", "content": "紀錄1"},
            {"user_id": "A123456789", "content": "紀錄2"}
        ]
        mock_collection.find.return_value = mock_cursor
        
        result = service.get_user_history_by_id("A123456789")
        
        assert len(result) == 2
        mock_collection.find.assert_called_once()
    
    def test_get_user_history_empty(self, mock_rag_service):
        """測試查詢不存在的用戶"""
        service, mock_collection = mock_rag_service
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = []
        mock_collection.find.return_value = mock_cursor
        
        result = service.get_user_history_by_id("NOT_EXIST")
        
        assert result == []
    
    def test_verify_against_history_no_history(self, mock_rag_service):
        """測試驗證 - 無歷史紀錄"""
        service, mock_collection = mock_rag_service
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = []
        mock_collection.find.return_value = mock_cursor
        
        result = service.verify_against_history(
            user_id="NEW_USER",
            current_data={"job": "工程師", "income": 80000}
        )
        
        assert result["has_history"] == False
        assert result["risk_level"] == "UNKNOWN"
    
    def test_verify_against_history_low_risk(self, mock_rag_service):
        """測試驗證 - 低風險"""
        service, mock_collection = mock_rag_service
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = [{
            "user_id": "A123456789",
            "metadata": {
                "hist_job": "工程師",
                "hist_income": 80000,
                "hist_phone": "0912345678",
                "has_default_record": False
            }
        }]
        mock_collection.find.return_value = mock_cursor
        
        result = service.verify_against_history(
            user_id="A123456789",
            current_data={"job": "工程師", "income": 80000, "phone": "0912345678"}
        )
        
        assert result["has_history"] == True
        assert result["risk_level"] == "LOW"
        assert result["mismatch_count"] == 0
    
    def test_verify_against_history_high_risk(self, mock_rag_service):
        """測試驗證 - 高風險 (多項不符)"""
        service, mock_collection = mock_rag_service
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = [{
            "user_id": "A123456789",
            "metadata": {
                "hist_job": "工程師",
                "hist_income": 80000,
                "hist_phone": "0912345678",
                "has_default_record": False
            }
        }]
        mock_collection.find.return_value = mock_cursor
        
        result = service.verify_against_history(
            user_id="A123456789",
            current_data={
                "job": "業務員",  # 不符
                "income": 50000,  # 差異超過 20%
                "phone": "0987654321"  # 不符
            }
        )
        
        assert result["has_history"] == True
        assert result["risk_level"] == "HIGH"
        assert result["mismatch_count"] >= 2


class TestCaseLibraryCollection:
    """測試 case_library Collection (FRE RAG 用)"""
    
    @pytest.fixture
    def mock_rag_service_with_encoder(self):
        """建立 mock RAG service (含 encoder)"""
        with patch('services.rag_service.mongo_db') as mock_db:
            mock_collection = MagicMock()
            mock_db.get_collection.return_value = mock_collection
            
            from services.rag_service import RAGService
            service = RAGService()
            service._case_library = mock_collection
            service._encoder = MagicMock()
            service._encoder.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
            service._initialized = True
            
            return service, mock_collection
    
    def test_add_case(self, mock_rag_service_with_encoder):
        """測試新增案例"""
        service, mock_collection = mock_rag_service_with_encoder
        mock_collection.insert_one.return_value = MagicMock(inserted_id="case_001")
        
        result = service.add_case(
            content="職業:工程師，月薪:80000",
            metadata={"hist_job": "工程師", "final_decision": "核准_PASS"},
            case_id="test_case_001"
        )
        
        assert result == "case_001"
        mock_collection.insert_one.assert_called_once()
        
        # 確認有生成 embedding
        call_args = mock_collection.insert_one.call_args[0][0]
        assert "embedding" in call_args
        assert len(call_args["embedding"]) == 384
    
    def test_search_similar_cases(self, mock_rag_service_with_encoder):
        """測試搜尋相似案例"""
        service, mock_collection = mock_rag_service_with_encoder
        
        mock_collection.aggregate.return_value = [
            {"content": "案例1", "metadata": {"final_decision": "核准_PASS"}, "score": 0.9},
            {"content": "案例2", "metadata": {"final_decision": "核准_PASS"}, "score": 0.8}
        ]
        
        result = service.search_similar_cases(
            query_text="工程師，月薪8萬",
            top_k=3
        )
        
        assert len(result) == 2
        assert result[0]["score"] > result[1]["score"]
    
    def test_search_similar_cases_with_profile(self, mock_rag_service_with_encoder):
        """測試用 profile 搜尋相似案例"""
        service, mock_collection = mock_rag_service_with_encoder
        
        mock_collection.aggregate.return_value = [
            {"content": "案例", "metadata": {"final_decision": "核准_PASS"}, "score": 0.85}
        ]
        
        profile = {
            "job": "軟體工程師",
            "income": 80000,
            "amount": 500000,
            "purpose": "購車"
        }
        
        result = service.search_similar_cases(profile=profile, top_k=3)
        
        assert len(result) == 1
    
    def test_get_reference_for_decision(self, mock_rag_service_with_encoder):
        """測試取得 FRE 決策參考"""
        service, mock_collection = mock_rag_service_with_encoder
        
        mock_collection.aggregate.return_value = [
            {"content": "案例1", "metadata": {"final_decision": "核准_PASS", "approved_amount": 500000}, "score": 0.9},
            {"content": "案例2", "metadata": {"final_decision": "核准_PASS", "approved_amount": 600000}, "score": 0.85},
            {"content": "案例3", "metadata": {"final_decision": "拒絕_REJECT", "approved_amount": 0}, "score": 0.8}
        ]
        
        profile = {"job": "工程師", "income": 80000, "amount": 500000}
        
        result = service.get_reference_for_decision(
            profile=profile,
            dve_risk_level="LOW",
            top_k=3
        )
        
        assert "similar_cases" in result
        assert "approval_rate" in result
        assert "avg_approved_amount" in result
        assert "recommendation" in result
        
        # 2/3 核准 = 66.7%
        assert result["approval_rate"] == pytest.approx(0.667, rel=0.01)


class TestRAGHelpers:
    """測試 RAG 輔助函數"""
    
    def test_profile_to_query(self):
        """測試 profile 轉查詢文字"""
        from services.rag_service import RAGService
        
        service = RAGService()
        
        profile = {
            "job": "軟體工程師",
            "income": 80000,
            "amount": 500000,
            "purpose": "購車"
        }
        
        query = service._profile_to_query(profile)
        
        assert "職業:軟體工程師" in query
        assert "月薪:80000" in query
        assert "貸款金額:500000" in query
        assert "用途:購車" in query
    
    def test_normalize_phone(self):
        """測試電話正規化"""
        from services.rag_service import RAGService
        
        service = RAGService()
        
        assert service._normalize_phone("0912-345-678") == "0912345678"
        assert service._normalize_phone("0912 345 678") == "0912345678"
        assert service._normalize_phone("") == ""
        assert service._normalize_phone(None) == ""


class TestBackwardCompatibility:
    """測試向下相容 API"""
    
    def test_add_document_calls_add_user_record(self):
        """測試 add_document 等同於 add_user_record"""
        with patch('services.rag_service.mongo_db') as mock_db:
            mock_collection = MagicMock()
            mock_db.get_collection.return_value = mock_collection
            mock_collection.insert_one.return_value = MagicMock(inserted_id="test_id")
            
            from services.rag_service import RAGService
            service = RAGService()
            service._user_history = mock_collection
            service._initialized = True
            
            result = service.add_document(
                user_id="A123456789",
                content="測試",
                metadata={}
            )
            
            assert result == "test_id"
    
    def test_vector_search_calls_search_similar_cases(self):
        """測試 vector_search 等同於 search_similar_cases"""
        with patch('services.rag_service.mongo_db') as mock_db:
            mock_collection = MagicMock()
            mock_db.get_collection.return_value = mock_collection
            mock_collection.aggregate.return_value = []
            
            from services.rag_service import RAGService
            service = RAGService()
            service._case_library = mock_collection
            service._encoder = MagicMock()
            service._encoder.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
            service._initialized = True
            
            result = service.vector_search("測試查詢", top_k=3)
            
            assert isinstance(result, list)
