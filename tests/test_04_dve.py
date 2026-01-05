import sys
import os
import time

# 確保可以 import src 下的模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.experts.dve import DVE_Expert

def test_dve():
    print("🚀 初始化 DVE 專家 (這可能需要幾秒鐘載入模型)...")
    
    # 1. 初始化
    dve = DVE_Expert()
    
    # 2. 準備測試案例
    # 記得嗎？我們在 dve.py 裡把 RAG 資料寫死成「公立高中教師」
    # 為了測試 DVE 有沒有在工作，我們故意填寫一個「不一樣」的職業
    
    print("\n🧪 測試案例: 故意製造矛盾")
    print("   [Context/RAG]: 公立高中教師 (寫死在程式裡)")
    print("   [Query/User] : 自由接案設計師 (我們輸入的)")
    print("-" * 50)

    mock_task = {
        "user_query": "我是做設計的，月收大概六萬",
        "profile_state": {
            "name": "林大衛",
            "id": "A123456789",
            "job": "自由接案設計師",  # <--- 這裡跟 RAG 不符！預期會被抓包
            "income": "60000"
        }
    }
    
    # 3. 執行推論
    print("🌊 準備呼叫模型 (請緊盯終端機，應該會開始跳字)...")
    start_time = time.time()
    
    try:
        result = dve.process(mock_task)
        
        end_time = time.time()
        print(f"\n\n⏱️ 推論耗時: {end_time - start_time:.2f} 秒")
        
        # 4. 顯示結果
        print("\n" + "="*30)
        print("=== 🛡️ DVE 最終查核報告 ===")
        print("="*30)
        print(f"🔹 專家代號: {result.get('expert')}")
        print(f"🔹 對話回應: {result.get('response')}")
        print(f"🔹 下一步驟: {result.get('next_step')}")
        
        if "dve_raw_report" in result:
            print("\n📝 原始 JSON 報告:")
            import json
            print(json.dumps(result['dve_raw_report'], ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"\n❌ 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dve()