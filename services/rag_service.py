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
        """延遲初始化"""
        if self._initialized:
            return
        
        # 取得兩個 Collection
        self._user_history = mongo_db.get_collection(self.USER_HISTORY_COLLECTION)
        self._case_library = mongo_db.get_collection(self.CASE_LIBRARY_COLLECTION)
        
        if self._user_history is None:
            logger.warning(f"⚠️ Collection '{self.USER_HISTORY_COLLECTION}' 未連線")
        else:
            logger.info(f"✅ Collection '{self.USER_HISTORY_COLLECTION}' 已連線")
            
        if self._case_library is None:
            logger.warning(f"⚠️ Collection '{self.CASE_LIBRARY_COLLECTION}' 未連線")
        else:
            logger.info(f"✅ Collection '{self.CASE_LIBRARY_COLLECTION}' 已連線")
        
        # 載入 Embedding 模型
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("📥 正在載入 Embedding 模型...")
            self._encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding 模型載入完成 (384 維)")
        except ImportError:
            logger.warning("⚠️ sentence-transformers 未安裝")
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

    # ========================================
    # user_history Collection (DVE 用)
    # 精確查詢，不是 RAG
    # ========================================

    def add_user_record(
        self, 
        user_id: str, 
        content: str, 
        metadata: Dict = None,
        doc_type: str = "application"
    ) -> Optional[str]:
        """
        新增用戶紀錄到 user_history
        
        用於 DVE 驗證時的個人歷史比對
        
        Args:
            user_id: 使用者 ID (身分證字號)
            content: 文字內容 (描述)
            metadata: 結構化資訊 (職業、收入、電話等)
            doc_type: 文件類型 (application/verification/decision)
        """
        self._lazy_init()
        
        if metadata is None:
            metadata = {}
        
        if self._user_history is None:
            logger.error("MongoDB user_history 未連線")
            return None
        
        doc = {
            "user_id": user_id,
            "content": content,
            "metadata": metadata,
            "doc_type": doc_type,
            "created_at": time.time()
        }
        
        try:
            result = self._user_history.insert_one(doc)
            logger.info(f"💾 用戶紀錄已存入 user_history (User: {user_id[:4]}***)")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ user_history 寫入失敗: {e}")
            return None

    def get_user_history_by_id(self, user_id: str) -> List[Dict]:
        """
        📂 精準檢索 - 根據 User ID 撈出該用戶的所有歷史資料
        
        ⚠️ 這不是 RAG！這是 Database Query
        
        用於 DVE 驗證「同一個人」的歷史
        """
        self._lazy_init()
        
        if self._user_history is None:
            logger.warning("MongoDB user_history 未連線")
            return []
        
        try:
            results = list(
                self._user_history.find(
                    {"user_id": user_id},
                    {"_id": 0}
                ).sort("created_at", -1)
            )
            
            logger.info(f"📂 user_history: 找到 {len(results)} 筆 (User: {user_id[:4]}***)")
            return results
        except Exception as e:
            logger.error(f"❌ 查詢 user_history 失敗: {e}")
            return []

    def get_latest_user_record(self, user_id: str) -> Optional[Dict]:
        """取得用戶最新一筆紀錄"""
        history = self.get_user_history_by_id(user_id)
        return history[0] if history else None

    def verify_against_history(
        self,
        user_id: str,
        current_data: Dict
    ) -> Dict:
        """
        🔍 DVE 驗證 - 比對當前資料與 user_history 中的歷史紀錄
        
        Args:
            user_id: 使用者 ID
            current_data: 當前申請資料 {job, income, phone, ...}
        
        Returns:
            {
                "has_history": bool,
                "mismatches": [(field, current, historical), ...],
                "mismatch_count": int,
                "risk_level": "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN",
                "historical_data": {...}
            }
        """
        history = self.get_user_history_by_id(user_id)
        
        if not history:
            return {
                "has_history": False,
                "mismatches": [],
                "mismatch_count": 0,
                "risk_level": "UNKNOWN",  # 新用戶
                "historical_data": None
            }
        
        latest = history[0]
        historical_data = latest.get("metadata", {})
        
        mismatches = []
        
        # 職業比對
        if current_data.get("job") and historical_data.get("hist_job"):
            if current_data["job"] != historical_data["hist_job"]:
                mismatches.append(("job", current_data["job"], historical_data["hist_job"]))
        
        # 收入比對 (允許 20% 誤差)
        curr_income = current_data.get("income", 0) or 0
        hist_income = historical_data.get("hist_income", 0) or 0
        
        if curr_income and hist_income:
            variance = abs(curr_income - hist_income) / hist_income
            if variance > 0.2:
                mismatches.append(("income", curr_income, hist_income))
        
        # 電話比對
        curr_phone = self._normalize_phone(current_data.get("phone", ""))
        hist_phone = self._normalize_phone(historical_data.get("hist_phone", ""))
        
        if curr_phone and hist_phone and curr_phone != hist_phone:
            mismatches.append(("phone", current_data.get("phone"), historical_data.get("hist_phone")))
        
        # 風險分類
        has_default = historical_data.get("has_default_record", False)
        mismatch_count = len(mismatches)
        
        if has_default or mismatch_count >= 2:
            risk_level = "HIGH"
        elif mismatch_count == 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "has_history": True,
            "mismatches": mismatches,
            "mismatch_count": mismatch_count,
            "risk_level": risk_level,
            "historical_data": historical_data
        }
    
    def _normalize_phone(self, phone: str) -> str:
        """正規化電話號碼"""
        if not phone:
            return ""
        return "".join(c for c in str(phone) if c.isdigit())

    # ========================================
    # case_library Collection (FRE RAG 用)
    # 真正的 RAG - Vector Search
    # ========================================

    def add_case(
        self, 
        content: str, 
        metadata: Dict = None,
        case_id: str = None
    ) -> Optional[str]:
        """
        新增案例到 case_library (用於 FRE 的 RAG)
        
        這些是匿名化的歷史案例，供 FRE 決策時參考
        
        Args:
            content: 案例描述 (用於生成 embedding)
            metadata: 結構化資訊 (職業、收入、金額、審核結果等)
            case_id: 案例 ID (可選，用於避免重複)
        """
        self._lazy_init()
        
        if metadata is None:
            metadata = {}
        
        if self._case_library is None:
            logger.error("MongoDB case_library 未連線")
            return None
        
        # 生成 embedding
        embedding = self.get_embedding(content)
        
        doc = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata,
            "created_at": time.time()
        }
        
        if case_id:
            doc["case_id"] = case_id
        
        try:
            result = self._case_library.insert_one(doc)
            logger.info(f"💾 案例已存入 case_library")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ case_library 寫入失敗: {e}")
            return None

    def search_similar_cases(
        self, 
        query_text: str = None,
        profile: Dict = None,
        top_k: int = 5,
        min_score: float = None
    ) -> List[Dict]:
        """
        🔍 RAG 核心 - 在 case_library 中搜尋相似案例
        
        用於 FRE 決策時參考歷史案例
        
        Args:
            query_text: 查詢文字 (直接搜尋)
            profile: 用戶 profile (自動組成查詢文字)
            top_k: 回傳數量
            min_score: 最低相似度
        
        Returns:
            相似案例列表，包含 score
        """
        self._lazy_init()
        
        if self._case_library is None or self._encoder is None:
            logger.warning("RAG 服務未就緒")
            return []
        
        # 組建查詢文字
        if query_text is None and profile:
            query_text = self._profile_to_query(profile)
        
        if not query_text:
            logger.warning("沒有查詢文字")
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
                    "created_at": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        try:
            results = list(self._case_library.aggregate(pipeline))
            
            # 過濾低分
            if min_score is None:
                min_score = self.SIMILARITY_THRESHOLD
            
            results = [r for r in results if r.get("score", 0) >= min_score]
            
            logger.info(f"🔍 case_library Vector Search: 找到 {len(results)} 筆相似案例")
            return results
            
        except Exception as e:
            logger.warning(f"⚠️ Vector Search 失敗: {e}")
            # Fallback: 簡單搜尋
            return self._fallback_search(query_text, top_k)
    
    def _profile_to_query(self, profile: Dict) -> str:
        """將 profile 轉為查詢文字"""
        parts = []
        
        if profile.get("job"):
            parts.append(f"職業:{profile['job']}")
        if profile.get("income"):
            parts.append(f"月薪:{profile['income']}")
        if profile.get("amount"):
            parts.append(f"貸款金額:{profile['amount']}")
        if profile.get("purpose") or profile.get("loan_purpose"):
            purpose = profile.get("purpose") or profile.get("loan_purpose")
            parts.append(f"用途:{purpose}")
        
        return "，".join(parts)
    
    def _fallback_search(self, query_text: str, top_k: int) -> List[Dict]:
        """備援搜尋 (當 Vector Search 不可用時)"""
        if self._case_library is None:
            return []
        
        try:
            # 用關鍵字搜尋
            results = list(
                self._case_library.find(
                    {"$text": {"$search": query_text}},
                    {"_id": 0, "embedding": 0, "score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})]).limit(top_k)
            )
            logger.info(f"📝 Fallback 搜尋: 找到 {len(results)} 筆")
            return results
        except Exception as e:
            logger.warning(f"Fallback 搜尋失敗: {e}")
            return []

    def get_reference_for_decision(
        self,
        profile: Dict,
        dve_risk_level: str = "LOW",
        top_k: int = 3
    ) -> Dict:
        """
        🎯 FRE 專用 - 取得決策參考資料
        
        綜合相似案例，提供決策參考
        
        Args:
            profile: 申請人資料
            dve_risk_level: DVE 風險等級
            top_k: 參考案例數量
        
        Returns:
            {
                "similar_cases": [...],
                "approval_rate": float,  # 相似案例核准率
                "avg_approved_amount": float,  # 平均核准金額
                "recommendation": str  # 建議
            }
        """
        similar_cases = self.search_similar_cases(profile=profile, top_k=top_k)
        
        if not similar_cases:
            return {
                "similar_cases": [],
                "approval_rate": None,
                "avg_approved_amount": None,
                "recommendation": "無相似案例參考，建議人工審核"
            }
        
        # 統計
        approved_count = 0
        total_approved_amount = 0
        
        for case in similar_cases:
            meta = case.get("metadata", {})
            decision = meta.get("final_decision", "")
            
            if "PASS" in decision or "核准" in decision:
                approved_count += 1
                total_approved_amount += meta.get("approved_amount", 0)
        
        approval_rate = approved_count / len(similar_cases)
        avg_amount = total_approved_amount / approved_count if approved_count > 0 else 0
        
        # 建議
        if dve_risk_level == "HIGH":
            recommendation = "DVE 風險高，建議拒絕或轉人工"
        elif approval_rate >= 0.7:
            recommendation = f"相似案例核准率 {approval_rate:.0%}，建議核准"
        elif approval_rate >= 0.4:
            recommendation = f"相似案例核准率 {approval_rate:.0%}，建議審慎評估"
        else:
            recommendation = f"相似案例核准率僅 {approval_rate:.0%}，建議拒絕"
        
        return {
            "similar_cases": similar_cases,
            "approval_rate": approval_rate,
            "avg_approved_amount": avg_amount,
            "recommendation": recommendation
        }

    # ========================================
    # 向下相容 (舊的 API)
    # ========================================
    
    def add_document(
        self, 
        user_id: str, 
        content: str, 
        metadata: Dict = None,
        doc_type: str = "application"
    ) -> Optional[str]:
        """
        向下相容: 新增文件到 user_history
        
        等同於 add_user_record()
        """
        return self.add_user_record(user_id, content, metadata, doc_type)
    
    def vector_search(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """
        向下相容: Vector Search
        
        等同於 search_similar_cases(query_text=...)
        """
        return self.search_similar_cases(query_text=query_text, top_k=top_k)


# 單例
rag_engine = RAGService()
