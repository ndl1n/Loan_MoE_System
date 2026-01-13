"""
User Session Manager
使用 Redis 管理使用者對話狀態
"""

import redis
import json
import time
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SESSION_TTL

# 設定 Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# 📌 Redis Connection Pool
# ==========================================
try:
    pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        max_connections=50
    )
    redis_client = redis.Redis(connection_pool=pool)
    
    # 啟動時測試連線
    redis_client.ping()
    logger.info(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})")

except redis.exceptions.ConnectionError as e:
    logger.error(f"❌ Redis connection failed: {e}")
    redis_client = None


# ==========================================
# 👤 User Session Manager
# ==========================================
class UserSessionManager:
    """
    負責管理單一使用者的:
    1. Profile (貸款申請資料)
    2. Conversation History (對話紀錄)
    """

    DEFAULT_PROFILE = {
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
        "verification_status": None,  # 新增: 追蹤驗證狀態
        "created_at": None,
        "updated_at": None
    }

    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        if redis_client is None:
            raise RuntimeError("Redis connection not available")
        
        self.user_id = user_id
        self.profile_key = f"loan:profile:{user_id}"
        self.history_key = f"loan:history:{user_id}"
        self.lock_key = f"loan:lock:{user_id}"

    # -------------------------
    # Profile Management
    # -------------------------
    def get_profile(self) -> Dict:
        """讀取使用者 profile，若不存在則初始化"""
        try:
            data = redis_client.get(self.profile_key)
            
            if not data:
                logger.info(f"[Init Profile] User: {self.user_id}")
                self._init_profile()
                return self.DEFAULT_PROFILE.copy()
            
            profile = json.loads(data)
            
            # 確保所有欄位都存在
            for key in self.DEFAULT_PROFILE:
                if key not in profile:
                    profile[key] = self.DEFAULT_PROFILE[key]
            
            return profile
            
        except json.JSONDecodeError as e:
            logger.error(f"Profile JSON decode failed for {self.user_id}: {e}")
            self._init_profile()
            return self.DEFAULT_PROFILE.copy()
            
        except Exception as e:
            logger.error(f"Failed to get profile for {self.user_id}: {e}")
            return self.DEFAULT_PROFILE.copy()

    def update_profile(self, updates: Dict) -> Dict:
        """更新部分欄位 (Partial Update)"""
        try:
            current_profile = self.get_profile()

            if current_profile.get("created_at") is None:
                current_profile["created_at"] = time.time()
            current_profile["updated_at"] = time.time()

            updated = False
            for k, v in updates.items():
                if v is None:
                    continue
                    
                if current_profile.get(k) != v:
                    current_profile[k] = v
                    updated = True
                    logger.info(f"[Profile Update] {self.user_id}: {k} = {v}")

            if updated:
                json_data = json.dumps(current_profile, ensure_ascii=False)
                self._save_to_redis(self.profile_key, json_data)
            
            return current_profile

        except Exception as e:
            logger.error(f"Failed to update profile for {self.user_id}: {e}")
            return self.get_profile()

    def _init_profile(self):
        """初始化空的 Profile"""
        initial_data = self.DEFAULT_PROFILE.copy()
        initial_data["created_at"] = time.time()
        
        self._save_to_redis(
            self.profile_key,
            json.dumps(initial_data, ensure_ascii=False)
        )

    # -------------------------
    # History Management
    # -------------------------
    def add_message(self, role: str, content: str):
        """新增對話紀錄"""
        if not content or not content.strip():
            return

        msg = json.dumps({
            "role": role,
            "content": content,
            "timestamp": time.time()
        }, ensure_ascii=False)

        try:
            pipe = redis_client.pipeline()
            pipe.rpush(self.history_key, msg)
            pipe.ltrim(self.history_key, -50, -1)
            pipe.expire(self.history_key, SESSION_TTL)
            pipe.execute()
            
            logger.debug(f"[Message Added] {self.user_id} ({role}): {content[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to add message for {self.user_id}: {e}")

    def get_history(self, limit: int = 10) -> List[Dict]:
        """取得最近 N 筆對話紀錄"""
        try:
            msgs = redis_client.lrange(self.history_key, -limit, -1)
            
            result = []
            for m in msgs:
                try:
                    result.append(json.loads(m))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping malformed message in history")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get history for {self.user_id}: {e}")
            return []

    # -------------------------
    # Utils / Cleanup
    # -------------------------
    def clear_session(self):
        """清空該使用者的所有資料"""
        try:
            pipe = redis_client.pipeline()
            pipe.delete(self.profile_key)
            pipe.delete(self.history_key)
            pipe.delete(self.lock_key)
            pipe.execute()
            
            logger.info(f"✅ Session cleared for {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear session for {self.user_id}: {e}")

    def get_session_info(self) -> Dict:
        """取得 session 基本資訊"""
        try:
            profile_ttl = redis_client.ttl(self.profile_key)
            history_ttl = redis_client.ttl(self.history_key)
            history_len = redis_client.llen(self.history_key)
            
            return {
                "user_id": self.user_id,
                "profile_exists": redis_client.exists(self.profile_key) > 0,
                "profile_ttl": profile_ttl,
                "history_length": history_len,
                "history_ttl": history_ttl
            }
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return {}

    def _save_to_redis(self, key: str, value: str):
        """內部 helper: 寫入並重設 TTL"""
        try:
            pipe = redis_client.pipeline()
            pipe.set(key, value)
            pipe.expire(key, SESSION_TTL)
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Redis write failed for {key}: {e}")
            raise
