"""
RAG 服務
使用 MongoDB 進行資料存取和語意搜尋

兩個 Collection，各司其職:

1. user_history (精確查詢)
   - 用途: DVE 驗證「這個人」的歷史申請紀錄
   - 查詢: 根據 user_id 精確比對
   - 內容: 每個用戶的個人資料和申請歷史

2. case_library (語意搜尋 - 真正的 RAG)
   - 用途: FRE 決策時找「相似案例」參考
   - 查詢: Vector Search 語意相似度
   - 內容: 匿名化的歷史案例 (含審核結果)

使用場景:
- LDE: 不使用 RAG (只負責問答和引導)
- DVE: user_history (精確查詢驗證)
- FRE: case_library (Vector Search 找相似案例)
"""

import os
import logging
import time
from typing import Dict, List, Optional

from .database import mongo_db

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG 服務
    
    使用兩個 Collection:
    - user_history: 用戶個人歷史 (DVE 驗證用，精確查詢)
    - case_library: 案例庫 (FRE RAG 用，Vector Search)
    """
    
    # Collection 名稱
    USER_HISTORY_COLLECTION = "user_history"
    CASE_LIBRARY_COLLECTION = "case_library"
    
    # 相似度閾值
    SIMILARITY_THRESHOLD = 0.5
    
    def __init__(self):
        self._user_history = None
        self._case_library = None
        self._encoder = None
        self._initialized = False

    def _lazy_init(self):
        """延遲初始化 (避免啟動時就載入大模型)"""
        if self._initialized:
            return
            
        # 取得 MongoDB Collection
        self._collection = mongo_db.get_collection(self.collection_name)
        
        if self._collection is None:
            logger.warning("⚠️ MongoDB 未連線，RAG 功能將受限")
        
        # 載入 Embedding 模型
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("📥 正在載入 Embedding 模型 (all-MiniLM-L6-v2)...")
            self._encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding 模型載入完成")
        except ImportError:
            logger.warning("⚠️ sentence-transformers 未安裝，向量搜尋功能將無法使用")
            self._encoder = None
        except Exception as e:
            logger.error(f"❌ Embedding 模型載入失敗: {e}")
            self._encoder = None
        
        self._initialized = True

    def get_embedding(self, text: str) -> List[float]:
        """將文字轉為向量 (384 維)"""
        self._lazy_init()
        
        if not text or self._encoder is None:
            return []
        
        return self._encoder.encode(text).tolist()

    def add_document(
        self, 
        user_id: str, 
        content: str, 
        metadata: Dict = None
    ) -> Optional[str]:
        """
        新增資料 - 將文字轉成向量並存入 MongoDB
        
        Args:
            user_id: 使用者 ID
            content: 文字內容
            metadata: 額外資訊 (dict)
        
        Returns:
            ObjectId: 插入的文件 ID，失敗則回傳 None
        """
        self._lazy_init()
        
        if metadata is None:
            metadata = {}
        
        if self._collection is None:
            logger.error("MongoDB 未連線，無法新增文件")
            return None
        
        vector = self.get_embedding(content)
        
        doc = {
            "user_id": user_id,
            "content": content,
            "embedding": vector,
            "metadata": metadata,
            "created_at": time.time()
        }
        
        try:
            result = self._collection.insert_one(doc)
            logger.info(f"💾 資料已存入 MongoDB (ID: {result.inserted_id})")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ MongoDB 寫入失敗: {e}")
            return None

    def vector_search(self, query_text: str, top_k: int = 3) -> List[Dict]:
        """
        RAG 核心 - 語意搜尋
        根據 Query 找出最相似的歷史紀錄
        
        Args:
            query_text: 查詢文字
            top_k: 回傳數量
        
        Returns:
            list: 相似文件列表
        """
        self._lazy_init()
        
        if self._collection is None or self._encoder is None:
            logger.warning("RAG 服務未就緒，返回空結果")
            return []
        
        query_vector = self.get_embedding(query_text)
        
        if not query_vector:
            return []
        
        # MongoDB Atlas Vector Search
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
        
        try:
            results = list(self._collection.aggregate(pipeline))
            logger.info(f"🔍 Vector Search 完成，找到 {len(results)} 筆結果")
            return results
            
        except Exception as e:
            logger.warning(f"⚠️ Vector Search 失敗 (可能索引未建立): {e}")
            return []

    def get_user_history_by_id(self, user_id: str) -> List[Dict]:
        """
        精準檢索 - 根據 User ID 撈出該用戶的所有歷史資料
        
        這對 DVE 查核最重要，因為我們要比對的是「這個人」的歷史
        
        Args:
            user_id: 使用者 ID
        
        Returns:
            list: 該用戶的所有歷史紀錄
        """
        self._lazy_init()
        
        if self._collection is None:
            logger.warning("MongoDB 未連線，返回空歷史")
            return []
        
        try:
            results = list(
                self._collection.find(
                    {"user_id": user_id},
                    {"_id": 0, "embedding": 0}
                )
            )
            
            logger.info(f"📂 找到 {len(results)} 筆歷史紀錄 (User: {user_id})")
            
            return results
        except Exception as e:
            logger.error(f"❌ 查詢歷史失敗: {e}")
            return []


# 方便外部使用的單例物件
rag_engine = RAGService()
