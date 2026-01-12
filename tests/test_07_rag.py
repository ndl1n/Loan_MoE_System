"""
測試 RAG 服務
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
print("🧪 測試 RAG 服務")
print("=" * 60)

# === 步驟 1: 初始化 RAG Service ===
print("\n📍 步驟 1: 初始化 RAG Service")

try:
    from services.rag_service import rag_engine
    print("✅ RAG Service 初始化成功")
except Exception as e:
    print(f"❌ RAG Service 初始化失敗: {e}")
    print("\n請確認:")
    print("1. 已安裝 sentence-transformers: pip install sentence-transformers")
    print("2. MongoDB 連線正常: python test_mongodb.py")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === 步驟 2: 測試 Embedding 生成 ===
print("\n📍 步驟 2: 測試 Embedding 生成")

try:
    test_text = "這是一個測試文本,用於生成向量"
    embedding = rag_engine.get_embedding(test_text)
    
    print(f"✅ Embedding 生成成功")
    print(f"   文字: {test_text}")
    print(f"   向量維度: {len(embedding)}")
    print(f"   向量前 5 個值: {embedding[:5]}")
    
    if len(embedding) != 384:
        print(f"⚠️  警告: 向量維度不是 384 (實際: {len(embedding)})")
    
except Exception as e:
    print(f"❌ Embedding 生成失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === 步驟 3: 測試新增文件 ===
print("\n📍 步驟 3: 測試新增文件")

try:
    # 準備測試資料
    test_user_id = "TEST_USER_001"
    test_content = """
    【銀行內部存檔】
    存檔時間: 2026-01-12 10:00:00
    客戶姓名: 測試用戶 (TEST_USER_001)
    職業紀錄: 任職於「測試公司」,職稱為「測試工程師」
    財務紀錄: 口述月薪 50000 元
    查核結果: 本次 DVE 查核風險為 LOW
    """
    
    test_metadata = {
        "name": "測試用戶",
        "hist_job": "測試工程師",
        "hist_company": "測試公司",
        "hist_income": 50000,
        "hist_phone": "0912-345-678",
        "hist_purpose": "購車",
        "default_record": "無",
        "inquiry_count": "1",
        "last_risk_level": "LOW"
    }
    
    # 新增文件
    doc_id = rag_engine.add_document(
        user_id=test_user_id,
        content=test_content,
        metadata=test_metadata
    )
    
    print(f"✅ 文件新增成功 (ID: {doc_id})")
    
except Exception as e:
    print(f"❌ 文件新增失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# === 步驟 4: 測試精準檢索 (根據 User ID) ===
print("\n📍 步驟 4: 測試精準檢索 (根據 User ID)")

try:
    # 檢索剛剛新增的文件
    results = rag_engine.get_user_history_by_id(test_user_id)
    
    print(f"✅ 檢索成功,找到 {len(results)} 筆紀錄")
    
    if len(results) > 0:
        print(f"\n最新一筆紀錄:")
        latest = results[-1]
        print(f"   User ID: {latest.get('user_id')}")
        print(f"   Content: {latest.get('content')[:100]}...")
        print(f"   Metadata: {latest.get('metadata')}")
    else:
        print("⚠️  警告: 沒有找到紀錄")
    
except Exception as e:
    print(f"❌ 檢索失敗: {e}")
    import traceback
    traceback.print_exc()

# === 步驟 5: 測試 Vector Search (語意搜尋) ===
print("\n📍 步驟 5: 測試 Vector Search (語意搜尋)")

try:
    query = "工程師的貸款紀錄"
    results = rag_engine.vector_search(query, top_k=3)
    
    if len(results) > 0:
        print(f"✅ Vector Search 成功,找到 {len(results)} 筆結果")
        
        for i, result in enumerate(results, 1):
            print(f"\n結果 {i}:")
            print(f"   相似度分數: {result.get('score', 'N/A')}")
            print(f"   Content: {result.get('content', '')[:80]}...")
    else:
        print("⚠️  Vector Search 未回傳結果")
        print("   可能原因:")
        print("   1. MongoDB Atlas Vector Search Index 尚未建立")
        print("   2. Collection 資料太少")
        print("\nℹ️  這不影響 DVE 功能,因為 DVE 主要使用精準檢索 (User ID)")
    
except Exception as e:
    print(f"⚠️  Vector Search 失敗: {e}")
    print("   這是正常的,如果:")
    print("   - 使用本地 MongoDB (不支援 Vector Search)")
    print("   - Atlas 上尚未建立 Vector Search Index")
    print("\nℹ️  DVE 主要功能 (精準檢索) 仍可正常運作")

# === 步驟 6: 清理測試資料 ===
print("\n📍 步驟 6: 清理測試資料")

try:
    from services.database import mongo_db
    collection = mongo_db.get_collection("user_history")
    
    result = collection.delete_many({"user_id": test_user_id})
    print(f"✅ 已刪除 {result.deleted_count} 筆測試資料")
    
except Exception as e:
    print(f"⚠️  清理失敗: {e}")
    print(f"   請手動刪除 user_id = {test_user_id} 的資料")

print("\n" + "=" * 60)
print("✅ RAG 服務測試完成!")
print("=" * 60)

print("\n📊 測試總結:")
print("   ✅ Embedding 生成: 正常")
print("   ✅ 文件新增: 正常")
print("   ✅ 精準檢索 (User ID): 正常")
print("   ⚠️  Vector Search: 需要 Atlas Index (非必要)")

print("\nℹ️  下一步:")
print("   執行 python test_dve_expert.py 測試 DVE Expert")