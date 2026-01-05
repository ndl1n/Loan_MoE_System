import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.experts.fre import FRE_Expert

def test_fre():
    print("💰 初始化 FRE 風控專家...")
    fre = FRE_Expert()
    
    # --- 案例 1: 優質客戶 (應該 PASS) ---
    print("\n🧪 測試案例 1: 優質客戶 (月薪 10萬, 借 10萬)")
    case_pass = {
        "profile_state": {"income": "100000", "amount": "100000", "job": "醫師"},
        "dve_result": {"risk_level": "LOW"} # 假設 DVE 說沒問題
    }
    res_1 = fre.process(case_pass)
    print(f"   👉 結果: {res_1['expert']}")
    print(f"   👉 訊息: {res_1['response']}")
    if "dbr" in res_1.get("financial_metrics", {}):
        print(f"   📊 DBR: {res_1['financial_metrics']['dbr']:.2f}% (預期 < 45%)")

    # --- 案例 2: 拒絕案例 (負債比過高) ---
    print("\n🧪 測試案例 2: 負債比過高 (月薪 3萬, 借 200萬)")
    # 200萬月付約 2.5萬，DBR 會接近 80% -> 觸發 REJECT 規則
    case_fail = {
        "profile_state": {"income": "30000", "amount": "2000000", "job": "助理"},
        "dve_result": {"risk_level": "LOW"}
    }
    res_2 = fre.process(case_fail)
    print(f"   👉 結果: {res_2['expert']}")
    print(f"   👉 訊息: {res_2['response']}")
    if "dbr" in res_2.get("financial_metrics", {}):
        print(f"   📊 DBR: {res_2['financial_metrics']['dbr']:.2f}% (預期 > 45%)")
        
    # 查看 Raw Report 確認模型是不是真的因為 DBR 拒絕的
    if "fre_raw_report" in res_2:
        print(f"   📝 決策理由: {res_2['fre_raw_report'].get('整合判讀')}")

if __name__ == "__main__":
    test_fre()