import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class MongoManager:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoManager, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """初始化 MongoDB 連線"""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("DB_NAME", "loan_system")
        
        if not uri:
            raise ValueError("❌ 錯誤: 未設定 MONGODB_URI 環境變數")

        try:
            print(f"🔌 正在連接 MongoDB Atlas...")
            cls._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            
            # 測試連線 (Ping)
            cls._client.admin.command('ping')
            print(f"✅ MongoDB 連線成功！資料庫: {db_name}")
            
            cls._db = cls._client[db_name]
            
        except ConnectionFailure as e:
            print(f"❌ MongoDB 連線失敗: {e}")
            raise e

    def get_collection(self, collection_name):
        """取得指定的 Collection"""
        if self._db is None:
            self._initialize()
        return self._db[collection_name]
    
    def close(self):
        """關閉連線"""
        if self._client:
            self._client.close()
            print("🔌 MongoDB 連線已關閉")

# 方便外部直接 import 使用的單例物件
mongo_db = MongoManager()