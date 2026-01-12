"""
測試 MongoDB 連線
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 測試 MongoDB 連線")
print("=" * 60)

# === 步驟 1: 檢查環境變數 ===
print("\n📍 步驟 1: 檢查環境變數")

from dotenv import load_dotenv
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "loan_system")

if not MONGODB_URI:
    print("❌ 錯誤: 未設定 MONGODB_URI")
    print("\n請在 .env 檔案中設定:")
    print("MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/")
    print("DB_NAME=loan_system")
    sys.exit(1)

print(f"✅ MONGODB_URI: {MONGODB_URI[:30]}... (已隱藏)")
print(f"✅ DB_NAME: {DB_NAME}")

# === 步驟 2: 測試 MongoDB 連線 ===
print("\n📍 步驟 2: 測試 MongoDB 連線")

try:
    from services.database import mongo_db
    print("✅ MongoManager 初始化成功")
except Exception as e:
    print(f"❌ MongoManager 初始化失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === 步驟 3: 測試基本操作 ===
print("\n📍 步驟 3: 測試基本操作")

try:
    # 取得測試 collection
    test_collection = mongo_db.get_collection("test_collection")
    print("✅ 成功取得 Collection: test_collection")
    
    # 插入測試文件
    test_doc = {
        "test_field": "test_value",
        "timestamp": "2026-01-12"
    }
    
    result = test_collection.insert_one(test_doc)
    print(f"✅ 成功插入測試文件 (ID: {result.inserted_id})")
    
    # 讀取測試文件
    found_doc = test_collection.find_one({"_id": result.inserted_id})
    print(f"✅ 成功讀取測試文件: {found_doc}")
    
    # 刪除測試文件
    test_collection.delete_one({"_id": result.inserted_id})
    print("✅ 成功刪除測試文件")
    
except Exception as e:
    print(f"❌ 操作失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === 步驟 4: 檢查必要的 Collection ===
print("\n📍 步驟 4: 檢查 user_history Collection")

try:
    user_history = mongo_db.get_collection("user_history")
    count = user_history.count_documents({})
    print(f"✅ user_history Collection 存在")
    print(f"   目前文件數: {count}")
    
    if count == 0:
        print("ℹ️  Collection 為空,這是正常的 (首次使用)")
    
except Exception as e:
    print(f"⚠️  警告: {e}")
    print("ℹ️  這不影響測試,Collection 會在首次使用時自動建立")

print("\n" + "=" * 60)
print("✅ MongoDB 連線測試完成!")
print("=" * 60)
print("\nℹ️  下一步:")
print("   1. 執行 python test_rag_service.py 測試 RAG 功能")
print("   2. 在 MongoDB Atlas 建立 Vector Search Index")
print("      - Collection: user_history")
print("      - Index Name: vector_index")
print("      - Field: embedding (384 dimensions, cosine)")