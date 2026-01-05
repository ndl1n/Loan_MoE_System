import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# 建立 Redis 連線池
pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)

class UserSessionManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.profile_key = f"loan:profile:{user_id}"
        self.history_key = f"loan:history:{user_id}"

    def get_profile(self):
        data = r.get(self.profile_key)
        if data:
            return json.loads(data)
        return {"name": None, "id": None, "job": None, "income": None, "amount": None, "risk_score": 0.5}

    def update_profile(self, new_data):
        current = self.get_profile()
        current.update(new_data)
        r.set(self.profile_key, json.dumps(current))
        return current

    def get_history(self, limit=10):
        msgs = r.lrange(self.history_key, -limit, -1)
        return [json.loads(m) for m in msgs]

    def add_message(self, role, content):
        msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        r.rpush(self.history_key, msg)
        r.expire(self.history_key, 3600) # 1小時過期
        r.expire(self.profile_key, 3600)