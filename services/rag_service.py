"""
RAG 服務
使用 MongoDB Vector Search 進行語意搜尋
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
    
    職責:
    - 將文字轉為向量 (Embedding)
    - 語意搜尋 (Vector Search)
    - 精準檢索 (根據 User ID)
    """
    
    def __init__(self, collection_name="user_history"):
        self.collection = mongo_db.get_collection(collection_name)
        
        # 載入輕量的 embedding 模型 (約 90MB)
        logger.info("📥 正在載入 Embedding 模型 (all-MiniLM-L6-v2)...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Embedding 模型載入完成")

    def get_embedding(self, text):
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

        """
        將文字轉為向量 (List of floats)
        
        Args:
            text: 要轉換的文字
        
        Returns:
            list: 向量 (384 維)
        """
        if not text:
            return []
        
        # sentence-transformers 回傳 numpy array,轉成 list 才能存 MongoDB
        return self.encoder.encode(text).tolist()

    def add_document(self, user_id, content, metadata={}):
        """
        新增資料 - 將文字轉成向量並存入 MongoDB
        
        Args:
            user_id: 使用者 ID
            content: 文字內容
            metadata: 額外資訊 (dict)
        
        Returns:
            ObjectId: 插入的文件 ID
        """
        vector = self.get_embedding(content)
        
        doc = {
            "user_id": user_id,
            "content": content,
            "embedding": vector,
            "metadata": metadata,
            "created_at": str(os.times())
        }
        
        result = self.collection.insert_one(doc)
        logger.info(f"💾 資料已存入 MongoDB (ID: {result.inserted_id})")
        
        return result.inserted_id

    def vector_search(self, query_text, top_k=3):
        """
        RAG 核心 - 語意搜尋
        根據 Query 找出最相似的歷史紀錄
        
        Args:
            query_text: 查詢文字
            top_k: 回傳數量
        
        Returns:
            list: 相似文件列表
        """
        query_vector = self.get_embedding(query_text)
        
        # MongoDB Atlas Vector Search Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",      # ⚠️ 請確保在 Atlas 建立此索引
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
            results = list(self.collection.aggregate(pipeline))
            logger.info(f"🔍 Vector Search 完成,找到 {len(results)} 筆結果")
            return results
            
        except Exception as e:
            logger.warning(f"⚠️  Vector Search 失敗 (可能索引未建立): {e}")
            # Fallback: 回傳空陣列
            return []

    def get_user_history_by_id(self, user_id):
        """
        精準檢索 - 根據 User ID 撈出該用戶的所有歷史資料
        
        這對 DVE 查核最重要,因為我們要比對的是「這個人」的歷史
        
        Args:
            user_id: 使用者 ID
        
        Returns:
            list: 該用戶的所有歷史紀錄
        """
        results = list(
            self.collection.find(
                {"user_id": user_id},
                {"_id": 0, "embedding": 0}  # 不回傳 _id 和 embedding
            )
        )
        
        logger.info(f"📂 找到 {len(results)} 筆歷史紀錄 (User: {user_id})")
        
        return results


# 方便外部使用的單例物件
rag_engine = RAGService()