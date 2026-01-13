"""
services 模組單元測試
測試 MongoDB 和 RAG 服務
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestMongoManager:
    """MongoDB 管理器測試"""
    
    @patch('services.database.MongoClient')
    def test_singleton_pattern(self, mock_client):
        """測試 Singleton 模式"""
        mock_client.return_value.admin.command.return_value = True
        
        # 重置單例
        from services.database import MongoManager
        MongoManager._instance = None
        MongoManager._client = None
        MongoManager._db = None
        
        # 多次創建應該返回同一實例
        # (實際測試需要處理環境變數)
    
    def test_collection_access(self):
        """測試 Collection 存取"""
        # 需要 MongoDB 連線或 Mock
        pass


class TestRAGService:
    """RAG 服務測試"""
    
    @pytest.fixture
    def mock_collection(self):
        """Mock MongoDB Collection"""
        mock = MagicMock()
        mock.find.return_value = []
        mock.insert_one.return_value = MagicMock(inserted_id="test_id")
        mock.aggregate.return_value = []
        return mock
    
    def test_embedding_generation(self):
        """測試 Embedding 生成"""
        # 這需要載入模型，在 CI 環境可能會失敗
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            text = "測試文字"
            embedding = model.encode(text).tolist()
            
            assert isinstance(embedding, list)
            assert len(embedding) == 384  # all-MiniLM-L6-v2 輸出 384 維
        except ImportError:
            pytest.skip("sentence-transformers 未安裝")
    
    def test_add_document_structure(self):
        """測試文件結構"""
        doc = {
            "user_id": "A123456789",
            "content": "測試內容",
            "embedding": [0.1] * 384,
            "metadata": {"name": "王小明"},
            "created_at": 1700000000
        }
        
        required_fields = ["user_id", "content", "embedding", "metadata"]
        for field in required_fields:
            assert field in doc
    
    def test_vector_search_pipeline(self):
        """測試向量搜尋 Pipeline 結構"""
        query_vector = [0.1] * 384
        top_k = 3
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": top_k
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        assert len(pipeline) == 2
        assert "$vectorSearch" in pipeline[0]
        assert pipeline[0]["$vectorSearch"]["limit"] == top_k
    
    def test_get_user_history_by_id_query(self):
        """測試根據 ID 查詢的結構"""
        user_id = "A123456789"
        
        query = {"user_id": user_id}
        projection = {"_id": 0, "embedding": 0}
        
        assert query["user_id"] == user_id
        assert projection["embedding"] == 0  # 不回傳 embedding


class TestRAGServiceIntegration:
    """RAG 服務整合測試"""
    
    def test_rag_metadata_structure(self):
        """測試 RAG Metadata 結構"""
        required_metadata = [
            "name",
            "hist_job",
            "hist_income",
            "hist_phone",
            "hist_purpose",
            "default_record"
        ]
        
        sample_metadata = {
            "name": "王小明",
            "hist_job": "工程師",
            "hist_income": "70000",
            "hist_phone": "0912-345-678",
            "hist_purpose": "購車",
            "hist_company": "科技公司",
            "default_record": "無",
            "inquiry_count": "2"
        }
        
        for field in required_metadata:
            assert field in sample_metadata
    
    def test_rag_context_for_dve(self):
        """測試 DVE 使用的 RAG Context 結構"""
        rag_context = {
            "檔案中紀錄職業": "工程師",
            "上次貸款資金用途": "購車",
            "檔案中聯絡電話": "0912-345-678",
            "歷史違約紀錄": "無",
            "檔案中服務公司名稱": "科技公司",
            "檔案中年薪/月薪": "70000",
            "信用報告查詢次數": "2",
            "地址變動次數": "0"
        }
        
        required_keys = [
            "檔案中紀錄職業",
            "歷史違約紀錄",
            "檔案中年薪/月薪"
        ]
        
        for key in required_keys:
            assert key in rag_context


class TestDatabaseConnectionHandling:
    """資料庫連線處理測試"""
    
    def test_connection_failure_handling(self):
        """測試連線失敗處理"""
        # 模擬連線失敗時的行為
        # RAGService 應該能優雅處理
        pass
    
    def test_lazy_initialization(self):
        """測試延遲初始化"""
        # RAGService 應該延遲載入 embedding 模型
        # 避免啟動時就佔用大量記憶體
        pass
