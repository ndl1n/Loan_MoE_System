import redis
import json
import os
import logging
from dotenv import load_dotenv
from typing import Dict, List, Optional

# 設定 Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# ⚙️ Redis Configuration
# ==========================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
SESSION_TTL = int(os.getenv("SESSION_TTL", 3600))  # 預設 1 小時

# ==========================================
# 🔌 Redis Connection Pool (改善版)
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
        max_connections=50  # 增加連線池大小
    )
    redis_client = redis.Redis(connection_pool=pool)
    
    # 啟動時測試連線
    redis_client.ping()
    logger.info(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})")

except redis.exceptions.ConnectionError as e:
    logger.error(f"❌ Redis connection failed: {e}")
    redis_client = None  # 避免後續呼叫時出錯


# ==========================================
# 👤 User Session Manager
# ==========================================
class UserSessionManager:
    """
    負責管理單一使用者的：
    1. Profile (貸款申請資料) - JSON String
    2. Conversation History (對話紀錄) - List of JSON Strings
    """

    # 定義預設結構，確保取用時不會 KeyError
    DEFAULT_PROFILE = {
        "name": None,
        "id": None,
        "phone": None,
        "loan_purpose": None,
        "job": None,
        "income": None,
        "amount": None,
        "last_asked_field": None, # 紀錄機器人上一題問什麼
        "risk_score": None,       # 未來擴充用
    }

    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        self.user_id = user_id
        # 使用 namespace 避免 key 衝突
        self.profile_key = f"loan:profile:{user_id}"
        self.history_key = f"loan:history:{user_id}"

    # -------------------------
    # Profile Management
    # -------------------------
    def get_profile(self) -> Dict:
        """讀取使用者目前狀態，若無則回傳預設值"""
        try:
            data = redis_client.get(self.profile_key)
            if not data:
                # 懶加載：第一次讀取時才初始化
                self._init_profile()
                return self.DEFAULT_PROFILE.copy()
            return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get profile for {self.user_id}: {e}")
            return self.DEFAULT_PROFILE.copy()

    def update_profile(self, updates: Dict) -> Dict:
        """
        更新部分欄位 (Partial Update)
        Example: updates = {"income": 50000}
        """
        try:
            # 1. 先讀取舊資料
            current_profile = self.get_profile()

            # 2. 合併新資料
            updated = False
            for k, v in updates.items():
                # 只更新有變動的值
                if current_profile.get(k) != v:
                    current_profile[k] = v
                    updated = True
            
            # 3. 如果有變動，才寫入 Redis (節省寫入次數)
            if updated:
                self._save_to_redis(self.profile_key, json.dumps(current_profile, ensure_ascii=False))
            
            return current_profile

        except Exception as e:
            logger.error(f"Failed to update profile for {self.user_id}: {e}")
            return self.DEFAULT_PROFILE

    def _init_profile(self):
        """初始化空的 Profile"""
        self._save_to_redis(
            self.profile_key, 
            json.dumps(self.DEFAULT_PROFILE, ensure_ascii=False)
        )

    # -------------------------
    # History Management
    # -------------------------
    def add_message(self, role: str, content: str):
        """
        新增一條對話紀錄
        role: 'user' or 'assistant' or 'system'
        """
        if not content:
            return

        msg = json.dumps(
            {"role": role, "content": content},
            ensure_ascii=False
        )
        
        try:
            # 使用 Pipeline: 寫入 List + 更新 TTL (一次網路請求完成)
            pipe = redis_client.pipeline()
            pipe.rpush(self.history_key, msg)
            pipe.expire(self.history_key, SESSION_TTL)
            pipe.execute()
        except Exception as e:
            logger.error(f"Failed to add message for {self.user_id}: {e}")

    def get_history(self, limit: int = 10) -> List[Dict]:
        """取得最近 N 筆對話紀錄"""
        try:
            # lrange 範圍是包含結尾的，所以是用 -limit 到 -1
            msgs = redis_client.lrange(self.history_key, -limit, -1)
            return [json.loads(m) for m in msgs]
        except Exception as e:
            logger.error(f"Failed to get history for {self.user_id}: {e}")
            return []

    # -------------------------
    # Utils / Cleanup
    # -------------------------
    def clear_session(self):
        """清空該使用者的所有資料 (測試或重置用)"""
        try:
            pipe = redis_client.pipeline()
            pipe.delete(self.profile_key)
            pipe.delete(self.history_key)
            pipe.execute()
            logger.info(f"Session cleared for {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to clear session for {self.user_id}: {e}")

    def get_session_info(self) -> Dict:
        """取得 session 基本資訊 (除錯用)"""
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