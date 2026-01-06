from .database import mongo_db
import os

# 我們先用開源輕量模型產生向量，方便測試 (實際上線可換成 OpenAI)
from sentence_transformers import SentenceTransformer

class RAGService:
    def __init__(self, collection_name="user_history"):
        self.collection = mongo_db.get_collection(collection_name)
        # 載入一個輕量的 embedding 模型 (會自動下載，約 90MB)
        print("📥 正在載入 Embedding 模型 (all-MiniLM-L6-v2)...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding 模型載入完成")

    def get_embedding(self, text):
        """將文字轉為向量 (List of floats)"""
        if not text:
            return []
        # sentence-transformers 回傳的是 numpy array，要轉成 list 才能存進 Mongo
        return self.encoder.encode(text).tolist()

    def add_document(self, user_id, content, metadata={}):
        """
        [新增資料] 將文字轉成向量並存入 MongoDB
        """
        vector = self.get_embedding(content)
        
        doc = {
            "user_id": user_id,
            "content": content,    # 原始文字 (Context)
            "embedding": vector,   # 向量欄位
            "metadata": metadata,  # 額外資訊 (例如: 職業, 年薪)
            "created_at": str(os.times())
        }
        
        result = self.collection.insert_one(doc)
        print(f"💾 資料已存入 MongoDB (ID: {result.inserted_id})")
        return result.inserted_id

    def vector_search(self, query_text, top_k=3):
        """
        [RAG 核心] 語意搜尋：根據 Query 找出最相似的歷史紀錄
        """
        query_vector = self.get_embedding(query_text)
        
        # MongoDB Atlas Vector Search Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",      # ⚠️ 請確保在 Atlas 建立了這個索引名稱
                    "path": "embedding",          # 向量欄位名稱
                    "queryVector": query_vector,  # 查詢向量
                    "numCandidates": 100,         # 候選數量
                    "limit": top_k                # 回傳數量
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"} # 顯示相似度分數
                }
            }
        ]
        
        try:
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception as e:
            print(f"⚠️ Vector Search 失敗 (可能是索引未建立): {e}")
            # 如果 Vector Search 失敗 (例如本地端測試)，回傳空陣列或改用簡易搜尋
            return []

    def get_user_history_by_id(self, user_id):
        """
        [精準檢索] 直接根據 User ID 撈出該用戶的所有歷史資料
        這對 DVE 查核最重要，因為我們要比對的是「這個人」的歷史
        """
        return list(self.collection.find({"user_id": user_id}, {"_id": 0, "embedding": 0}))

# 方便外部使用
rag_engine = RAGService()