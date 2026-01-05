import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gating_engine import MoEGateKeeper

def test_logic():
    print("🚀 初始化門控系統 (Gating Engine)...")
    gate = MoEGateKeeper()
    
    # 測試案例 1: 應該走綠色通道 (Green Channel)
    case_1 = {
        "user_query": "我要申請",
        "profile_state": {"job": "台積電工程師", "income": "200萬"},
        "verification_status": "pending"
    }
    print(f"\n🧪 測試案例 1 (優質客戶): {case_1['profile_state']['job']}")
    expert, conf, reason = gate.predict(case_1)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 2: 應該走紅色通道 (Red Channel)
    case_2 = {
        "user_query": "急用現金",
        "profile_state": {"job": "博弈", "income": "現金"},
        "verification_status": "pending"
    }
    print(f"\n🧪 測試案例 2 (高風險): {case_2['profile_state']['job']}")
    expert, conf, reason = gate.predict(case_2)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")
    
    # 測試案例 3: 技術問題 (Tech Interceptor)
    case_3 = {
        "user_query": "照片一直傳不上去，顯示格式錯誤",
        "profile_state": {"name": "Test"},
        "verification_status": "unknown"
    }
    print(f"\n🧪 測試案例 3 (技術障礙): {case_3['user_query']}")
    expert, conf, reason = gate.predict(case_3)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 4: 一般諮詢 (AI Inference)
    case_4 = {
        "user_query": "請問公教人員貸款利率多少？",
        "profile_state": {"name": "Test", "id": "A123"}, # 已有基本資料
        "verification_status": "unknown"
    }
    print(f"\n🧪 測試案例 4 (一般諮詢): {case_4['user_query']}")
    expert, conf, reason = gate.predict(case_4)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 5: 資料齊全的優質客戶 -> 應該去 FRE
    case_5 = {
        "user_query": "我想知道審核結果",
        "profile_state": {
            "name": "張三", "id": "A123", 
            "job": "台積電工程師", "income": "200000", "amount": "1000000"
        },
        "verification_status": "verified"  # 重點：已經查核過了
    }
    print(f"\n🧪 測試案例 5 (資料齊全/已查核): {case_5['user_query']}")
    expert, conf, reason = gate.predict(case_5)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")
    
    # 測試案例 6: 資料齊全但還沒查核 -> 應該去 DVE
    case_6 = {
        "user_query": "資料都填好了",
        "profile_state": {
            "name": "李四", "id": "B456", 
            "job": "工程師", "income": "100000", "amount": "500000"
        },
        "verification_status": "pending" # 重點：還沒查核
    }
    print(f"\n🧪 測試案例 6 (資料齊全/未查核): {case_6['user_query']}")
    expert, conf, reason = gate.predict(case_6)
    print(f"   👉 分派專家: {expert} |信心: {conf:.2f} | 原因: {reason}")
    
    # 測試案例 7: DVE (高風險關鍵字攔截)
    # 預期：雖然資料不全，但講到"現金"、"博弈"，應該優先由 DVE 介入或標記
    case_7 = {
        "user_query": "我沒有薪資證明，都是領現金的，這樣可以嗎？",
        "profile_state": {"name": "王小明"}, # 資料不全
        "verification_status": "unknown"
    }
    print(f"\n🧪 測試案例 7 (高風險關鍵字): {case_7['user_query']}")
    expert, conf, reason = gate.predict(case_7)
    print(f"   👉 分派專家: {expert} | 信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 8: DVE (資料齊全但未查核 -> 送去檢查)
    # 預期：5 個必填欄位都有了，但 status 還是 pending，所以要給 DVE 做比對
    case_8 = {
        "user_query": "我的資料都填好了，麻煩確認一下",
        "profile_state": {
            "name": "陳怡君", 
            "id": "Q223456789", 
            "job": "行政人員", 
            "income": "35000", 
            "amount": "100000"
        },
        "verification_status": "pending" # 重點：未查核
    }
    print(f"\n🧪 測試案例 8 (資料齊全/未查核): {case_8['user_query']}")
    expert, conf, reason = gate.predict(case_8)
    print(f"   👉 分派專家: {expert} | 信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 9: FRE (資料齊全 + 已查核 -> 請求決策)
    # 預期：流程已跑完查核 (Verified)，使用者想知道結果，送給 FRE 算分
    case_9 = {
        "user_query": "請問我的審核通過了嗎？",
        "profile_state": {
            "name": "林醫師", 
            "id": "A112233445", 
            "job": "主治醫師", 
            "income": "250000", 
            "amount": "2000000"
        },
        "verification_status": "verified" # 重點：已查核
    }
    print(f"\n🧪 測試案例 9 (請求審核結果): {case_9['user_query']}")
    expert, conf, reason = gate.predict(case_9)
    print(f"   👉 分派專家: {expert} | 信心: {conf:.2f} | 原因: {reason}")

    # 測試案例 10: FRE (詢問具體額度利率)
    # 預期：同樣是已查核狀態，詢問細節由 FRE 回答
    case_10 = {
        "user_query": "我想知道最後核准的利率是多少",
        "profile_state": {
            "name": "張經理", 
            "id": "F123456789", 
            "job": "科技業主管", 
            "income": "120000", 
            "amount": "800000"
        },
        "verification_status": "verified"
    }
    print(f"\n🧪 測試案例 10 (詢問額度利率): {case_10['user_query']}")
    expert, conf, reason = gate.predict(case_10)
    print(f"   👉 分派專家: {expert} | 信心: {conf:.2f} | 原因: {reason}")
    
if __name__ == "__main__":
    test_logic()