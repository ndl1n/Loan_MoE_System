import sys
import os
import json
import time

# 設定路徑以便 import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.experts.dve import DVE_Expert

def print_section(title):
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def test_dve_logic():
    print("🚀 初始化 DVE 資料查核專家...")
    dve = DVE_Expert()
    
    # ==========================================
    # 🟢 Case 1: 左佩妤 (完美一致 - LOW Risk)
    # 測試目的: 驗證 RAG 是否能抓到資料庫中的正確歷史，並判定為一致
    # ==========================================
    print_section("測試案例: 左佩妤 (資料完全一致)")

    # 模擬從 User Interface 傳來的資料 (Task Data)
    case_perfect = {
        "user_query": "我要申請個人進修貸款", # 用戶隨口說的話 (非必要，但模擬真實情境)
        "profile_state": {
            "name": "左佩妤",
            "id": "Q229012345",          # <--- 關鍵: DVE 會拿這個 ID 去 RAG 撈資料
            "job": "法院書記官",          # <--- 口述資料
            "company": "臺灣臺北地方法院", # <--- 口述資料
            "income": 55000,             # <--- 口述資料
            # "phone": "0910-111-888"    # (註: 若前端沒傳電話，DVE 程式碼範例中是寫死或預設，不影響主流程)
        }
    }

    print(f"📥 [Input] 用戶口述資料:")
    print(json.dumps(case_perfect['profile_state'], indent=2, ensure_ascii=False))
    
    print("\n🔄 DVE 處理中 (含 RAG 檢索 + LLM 比對 + 自動存檔)...")
    start_time = time.time()
    
    # --- 執行核心邏輯 ---
    result = dve.process(case_perfect)
    
    duration = time.time() - start_time
    print(f"\n⏱️ 處理耗時: {duration:.2f} 秒")

    # --- 驗證結果 ---
    print("\n📤 [Output] 專家回傳結果:")
    print(f"   👉 決策標記 (Expert): {result.get('expert')}")
    print(f"   👉 用戶回應 (Response): {result.get('response')}")
    print(f"   👉 下一步驟 (Next Step): {result.get('next_step')}")
    
    if "dve_raw_report" in result:
        print("\n📄 [Report] LLM 生成的原始報告:")
        # 只印出關鍵部分，避免太長
        report = result['dve_raw_report']
        print(f"{report}")
        print(f"   - 核實狀態: {report.get('核實狀態')}")
        print(f"   - 風險標記: {report.get('風險標記')}")
        print(f"   - 綜合分析: {report.get('綜合分析', '')[:50]}...") # 只印前50字

    # --- 自動化斷言 (Assertion) ---
    # 這是為了讓您可以直接看 "PASS" 或 "FAIL"
    print("\n⚖️  自動驗證結果:")
    if "LOW" in result.get('expert', ""):
        print("   ✅ 成功: 風險評級為 LOW，符合預期。")
    else:
        print(f"   ❌ 失敗: 預期 LOW，但得到 {result.get('expert')}")

    if "TRANSFER_TO_FRE" == result.get('next_step'):
        print("   ✅ 成功: 流程導向 FRE (風險計算)，符合預期。")
    else:
        print(f"   ❌ 失敗: 流程導向錯誤 ({result.get('next_step')})")

if __name__ == "__main__":
    test_dve_logic()