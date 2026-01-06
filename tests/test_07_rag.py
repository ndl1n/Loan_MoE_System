# tests/test_mongo_rag.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_service import rag_engine

def test_rag_flow():
    print("🚀 開始測試 RAG 流程...")
    
    # 1. 模擬插入一筆歷史資料 (Context)
    user_id = "A123456789"
    content = "客戶紀錄：職業為公立高中教師，年收入約 80 萬，任職於台北市立建國中學。"
    metadata = {"job": "教師", "company": "建國中學", "year": 2023}
    
    print(f"\n📝 步驟 1: 寫入歷史資料 (User: {user_id})")
    rag_engine.add_document(user_id, content, metadata)
    
    # 2. 模擬 User ID 精準查詢 (DVE 最常用的功能)
    print(f"\n🔍 步驟 2: 執行 ID 精準查詢")
    history = rag_engine.get_user_history_by_id(user_id)
    print(f"   👉 找到 {len(history)} 筆紀錄")
    print(f"   👉 第一筆內容: {history[0]['content']}")

    # 3. 模擬語意搜尋 (Vector Search)
    # 情境: 我們想知道這個人以前有沒有做過「教育」相關的工作
    query = "教育相關工作經驗"
    print(f"\n🔎 步驟 3: 執行語意搜尋 (Query: '{query}')")
    
    # 注意：如果還沒在 Atlas 建立 Vector Index，這一步可能會沒結果或報錯
    results = rag_engine.vector_search(query)
    
    if results:
        for i, res in enumerate(results):
            print(f"   👉 結果 {i+1} (相似度 {res['score']:.4f}): {res['content']}")
    else:
        print("   ⚠️ 未找到相似結果 (可能是 Atlas Index 尚未建立或尚未同步)")

if __name__ == "__main__":
    test_rag_flow()