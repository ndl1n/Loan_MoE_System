import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import mongo_db

def test_connection():
    print("🚀 開始測試 MongoDB 連線...")
    
    try:
        # 1. 取得 Collection
        col = mongo_db.get_collection("test_connectivity")
        
        # 2. 寫入測試
        test_doc = {"msg": "Hello Atlas", "timestamp": "now"}
        res = col.insert_one(test_doc)
        print(f"✅ 寫入成功! ID: {res.inserted_id}")
        
        # 3. 讀取測試
        doc = col.find_one({"_id": res.inserted_id})
        print(f"✅ 讀取成功! 內容: {doc}")
        
        # 4. 清理測試資料
        col.delete_one({"_id": res.inserted_id})
        print("✅ 清理測試資料完成")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    test_connection()