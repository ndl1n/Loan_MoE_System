import sys
import os
import json

# 設定路徑以便 import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_service import rag_engine

def print_record(title, records):
    """美化輸出的輔助函數"""
    print(f"\n🔎 {title}")
    if not records:
        print("   ❌ 未找到任何資料 (請確認 seed_db.py 是否已執行)")
        return

    print(f"   ✅ 找到 {len(records)} 筆紀錄：")
    for i, doc in enumerate(records):
        meta = doc.get("metadata", {})
        content = doc.get("content", "")
        
        print(f"   [{i+1}] 姓名: {meta.get('name')} | ID: {doc.get('user_id')}")
        print(f"       職業: {meta.get('job')} | 公司: {meta.get('company')}")
        print(f"       預期風險: {meta.get('expected_risk')}")
        print(f"       內容預覽: {content[:60]}...") 

def test_specific_user():
    print("🚀 開始測試 RAG 精準檢索功能 (Target: 左佩妤)...")
    
    # 🎯 設定測試目標 (根據您提供的資料)
    target_id = "Q229012345"
    target_name = "左佩妤"
    expected_job = "法院書記官"
    expected_company = "臺灣臺北地方法院"

    # ==========================================
    # 🧪 測試 1: 根據 ID 查找 (DVE 核心邏輯)
    # ==========================================
    print("\n" + "="*50)
    print(f"🧪 測試 1: 使用 ID '{target_id}' 尋找")
    print("="*50)
    
    by_id_results = rag_engine.get_user_history_by_id(target_id)
    print_record("ID 檢索結果", by_id_results)

    # 驗證資料正確性
    if by_id_results:
        record = by_id_results[-1] # 取最新
        meta = record.get("metadata", {})
        content = record.get("content", "")
        
        # 斷言檢查 (Assertion)
        if meta.get("job") == expected_job:
            print(f"   ✨ 職業驗證正確: {expected_job}")
        else:
            print(f"   ⚠️ 職業驗證失敗: 預期 {expected_job}, 實際 {meta.get('job')}")
            
        if expected_company in content:
            print(f"   ✨ 內容驗證正確: 包含 '{expected_company}'")
        else:
            print(f"   ⚠️ 內容驗證失敗: 內容中未找到 '{expected_company}'")

    # ==========================================
    # 🧪 測試 2: 根據 姓名 查找 (輔助查詢)
    # ==========================================
    print("\n" + "="*50)
    print(f"🧪 測試 2: 使用 姓名 '{target_name}' 尋找")
    print("="*50)

    # 直接查詢 Metadata
    query = {"metadata.name": target_name}
    by_name_results = list(rag_engine.collection.find(query, {"_id": 0, "embedding": 0}))
    
    print_record("姓名 檢索結果", by_name_results)

    # ==========================================
    # 🧪 測試 3: 一致性比對
    # ==========================================
    if by_id_results and by_name_results:
        print("\n" + "="*50)
        print("⚖️  交叉比對驗證")
        print("="*50)
        
        id_user = by_id_results[-1].get("user_id")
        name_user = by_name_results[-1].get("user_id")
        
        if id_user == target_id and name_user == target_id:
            print(f"   ✅ ID 與 姓名 搜尋結果指向同一人 ({target_id})！")
        else:
            print(f"   ❌ 資料不一致！ID搜到: {id_user}, 姓名搜到: {name_user}")

if __name__ == "__main__":
    test_specific_user()