"""
RAG 種子資料產生器
Seed Data Generator for case_library Collection

用途:
1. 產生模擬的歷史申請案例 (匿名化)
2. 存入 MongoDB case_library 並生成 embedding
3. 供 FRE 的 RAG 功能使用 (決策參考)

Collection 說明:
- user_history: DVE 用，存每個用戶的個人紀錄 (精確查詢)
- case_library: FRE 用，存匿名案例供 RAG 搜尋 (Vector Search) ← 本腳本

使用方式:
    python scripts/seed_case_data.py         # 產生 100 筆
    python scripts/seed_case_data.py -n 500  # 產生 500 筆
    python scripts/seed_case_data.py --clear # 清除後重新產生
"""

import os
import sys
import random
import time
from datetime import datetime, timedelta

# 確保可以 import 專案模組
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from services.rag_service import rag_engine


# ============================================
# 種子資料定義
# ============================================

# 職業列表 (含薪資範圍)
JOBS = [
    {"job": "軟體工程師", "income_range": (60000, 150000), "stability": "high"},
    {"job": "資深工程師", "income_range": (80000, 200000), "stability": "high"},
    {"job": "專案經理", "income_range": (70000, 180000), "stability": "high"},
    {"job": "醫師", "income_range": (150000, 400000), "stability": "high"},
    {"job": "護理師", "income_range": (45000, 80000), "stability": "high"},
    {"job": "教師", "income_range": (50000, 90000), "stability": "high"},
    {"job": "公務員", "income_range": (45000, 100000), "stability": "high"},
    {"job": "會計師", "income_range": (60000, 150000), "stability": "high"},
    {"job": "律師", "income_range": (80000, 300000), "stability": "high"},
    {"job": "銀行行員", "income_range": (45000, 100000), "stability": "high"},
    {"job": "業務經理", "income_range": (50000, 150000), "stability": "medium"},
    {"job": "行銷專員", "income_range": (40000, 80000), "stability": "medium"},
    {"job": "設計師", "income_range": (40000, 100000), "stability": "medium"},
    {"job": "餐飲業主管", "income_range": (40000, 80000), "stability": "medium"},
    {"job": "零售店長", "income_range": (35000, 60000), "stability": "medium"},
    {"job": "自營商", "income_range": (30000, 200000), "stability": "low"},
    {"job": "計程車司機", "income_range": (30000, 60000), "stability": "low"},
    {"job": "外送員", "income_range": (25000, 50000), "stability": "low"},
    {"job": "臨時工", "income_range": (25000, 40000), "stability": "low"},
    {"job": "待業中", "income_range": (0, 0), "stability": "none"},
]

# 貸款用途
PURPOSES = [
    "購車", "房屋裝修", "週轉金", "教育費用", "醫療費用",
    "結婚基金", "投資理財", "債務整合", "創業資金", "其他"
]

# 公司名稱
COMPANIES = [
    "台積電", "聯發科", "鴻海精密", "中華電信", "台北市政府",
    "新光醫院", "台大醫院", "永豐銀行", "國泰人壽", "遠傳電信",
    "Google台灣", "微軟台灣", "亞馬遜台灣", "宏碁", "華碩",
    "統一企業", "全聯福利中心", "7-11總部", "麥當勞台灣", "自營"
]

# 審核結果 (根據條件加權)
DECISIONS = ["核准_PASS", "拒絕_REJECT", "轉介審核_ESCALATE"]


def generate_random_id():
    """產生模擬身分證字號"""
    letters = "ABCDEFGHJKLMNPQRSTUVXYWZIO"
    first = random.choice(letters)
    second = random.choice("12")
    rest = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{first}{second}{rest}"


def generate_random_phone():
    """產生模擬電話號碼"""
    return f"09{random.randint(10, 99)}{random.randint(100000, 999999)}"


def calculate_decision(income: int, amount: int, stability: str) -> tuple:
    """
    根據條件計算審核結果
    
    Returns:
        (decision, approved_amount, rate)
    """
    # 計算 DBR
    monthly_payment = (amount * 1.03) / 84  # 7年期
    dbr = (monthly_payment / income * 100) if income > 0 else 100
    
    # 基本分數
    score = 700
    
    # 根據穩定性調整
    if stability == "high":
        score += 50
    elif stability == "medium":
        score += 20
    elif stability == "low":
        score -= 30
    elif stability == "none":
        score -= 100
    
    # 根據 DBR 調整
    if dbr > 60:
        return ("拒絕_REJECT", 0, 0)
    elif dbr > 40:
        score -= 50
    
    # 根據收入調整
    if income >= 100000:
        score += 30
    elif income >= 60000:
        score += 10
    elif income < 30000:
        score -= 50
    
    # 決策
    if score >= 700:
        # 核准
        approved_amount = amount
        rate = 2.5 if income >= 100000 else (3.0 if income >= 60000 else 3.5)
        return ("核准_PASS", approved_amount, rate)
    elif score >= 600:
        # 轉介或部分核准
        if random.random() > 0.5:
            approved_amount = int(amount * 0.7)  # 核准 70%
            rate = 4.0
            return ("核准_PASS", approved_amount, rate)
        else:
            return ("轉介審核_ESCALATE", 0, 0)
    else:
        return ("拒絕_REJECT", 0, 0)


def generate_seed_case() -> dict:
    """產生一筆種子資料"""
    # 隨機選擇職業
    job_info = random.choice(JOBS)
    job = job_info["job"]
    stability = job_info["stability"]
    
    # 根據職業產生收入
    income_min, income_max = job_info["income_range"]
    income = random.randint(income_min, income_max) if income_max > 0 else 0
    
    # 隨機產生其他資料
    purpose = random.choice(PURPOSES)
    company = random.choice(COMPANIES)
    
    # 根據收入決定貸款金額 (通常是年收入的 5-10 倍)
    annual_income = income * 12
    amount_min = max(100000, annual_income * 0.5)
    amount_max = min(3000000, annual_income * 2)
    amount = int(random.randint(int(amount_min), int(amount_max)) / 10000) * 10000
    
    # 計算決策
    decision, approved_amount, rate = calculate_decision(income, amount, stability)
    
    # 產生 user_id
    user_id = generate_random_id()
    
    # 產生 content (用於 embedding)
    content = (
        f"職業:{job}，月薪:{income}，"
        f"貸款金額:{amount}，用途:{purpose}，"
        f"公司:{company}，"
        f"審核結果:{decision}"
    )
    
    # metadata
    metadata = {
        "hist_job": job,
        "hist_income": income,
        "hist_phone": generate_random_phone(),
        "hist_company": company,
        "hist_purpose": purpose,
        "amount": amount,
        "approved_amount": approved_amount,
        "rate": rate,
        "final_decision": decision,
        "job_stability": stability,
        "has_default_record": random.random() < 0.05,  # 5% 有違約紀錄
    }
    
    return {
        "user_id": user_id,
        "content": content,
        "metadata": metadata,
        "doc_type": "application"
    }


def seed_database(num_records: int = 100):
    """
    產生種子資料並存入 MongoDB case_library
    
    Args:
        num_records: 要產生的紀錄數量
    """
    print(f"🌱 開始產生 {num_records} 筆種子資料到 case_library...")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    # 統計
    stats = {
        "核准_PASS": 0,
        "拒絕_REJECT": 0,
        "轉介審核_ESCALATE": 0
    }
    
    for i in range(num_records):
        try:
            case = generate_seed_case()
            
            # 存入 case_library (不是 user_history)
            result = rag_engine.add_case(
                content=case["content"],
                metadata=case["metadata"],
                case_id=f"seed_{i+1:05d}"
            )
            
            if result:
                success_count += 1
                decision = case["metadata"]["final_decision"]
                stats[decision] = stats.get(decision, 0) + 1
                
                if (i + 1) % 10 == 0:
                    print(f"  ✓ 已產生 {i + 1}/{num_records} 筆...")
            else:
                fail_count += 1
                print(f"  ✗ 第 {i + 1} 筆存入失敗")
                
        except Exception as e:
            fail_count += 1
            print(f"  ✗ 第 {i + 1} 筆產生失敗: {e}")
    
    print("=" * 50)
    print(f"✅ 完成！成功: {success_count}, 失敗: {fail_count}")
    print(f"\n📊 審核結果分布:")
    for decision, count in stats.items():
        pct = count / success_count * 100 if success_count > 0 else 0
        print(f"   {decision}: {count} ({pct:.1f}%)")


def show_sample_queries():
    """顯示範例查詢 (測試 FRE 的 RAG)"""
    print("\n" + "=" * 50)
    print("📚 測試 case_library RAG 查詢 (FRE 用)")
    print("=" * 50)
    
    test_profiles = [
        {"job": "軟體工程師", "income": 80000, "amount": 500000, "purpose": "購車"},
        {"job": "護理師", "income": 50000, "amount": 300000, "purpose": "週轉金"},
        {"job": "自營商", "income": 60000, "amount": 1000000, "purpose": "創業資金"},
    ]
    
    for profile in test_profiles:
        print(f"\n🔍 查詢 Profile: {profile}")
        
        # 使用 FRE 專用方法
        result = rag_engine.get_reference_for_decision(
            profile=profile,
            dve_risk_level="LOW",
            top_k=3
        )
        
        print(f"   核准率: {result['approval_rate']:.0%}" if result['approval_rate'] else "   核准率: N/A")
        print(f"   平均核准金額: {result['avg_approved_amount']:,.0f}" if result['avg_approved_amount'] else "   平均核准金額: N/A")
        print(f"   建議: {result['recommendation']}")
        
        if result['similar_cases']:
            print(f"   相似案例 ({len(result['similar_cases'])} 筆):")
            for i, case in enumerate(result['similar_cases'][:2], 1):
                meta = case.get("metadata", {})
                score = case.get("score", 0)
                print(f"      {i}. {meta.get('hist_job')} / {meta.get('hist_income')} / {meta.get('final_decision')} (相似度: {score:.0%})")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 種子資料產生器")
    parser.add_argument(
        "-n", "--num", 
        type=int, 
        default=100,
        help="要產生的紀錄數量 (預設: 100)"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="只測試查詢，不產生新資料"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清除現有資料後再產生"
    )
    
    args = parser.parse_args()
    
    print("🚀 RAG 種子資料產生器")
    print("=" * 50)
    
    # 檢查 MongoDB 連線
    from services.database import mongo_db
    if not mongo_db.is_connected():
        print("❌ MongoDB 未連線，請檢查 MONGODB_URI 設定")
        print("   提示: 確認 .env 中有設定 MONGODB_URI")
        return
    
    print("✅ MongoDB 已連線")
    
    # 清除現有資料
    if args.clear:
        print("\n⚠️ 清除 case_library 現有資料...")
        try:
            collection = mongo_db.get_collection("case_library")
            if collection:
                result = collection.delete_many({})
                print(f"   已刪除 {result.deleted_count} 筆資料")
        except Exception as e:
            print(f"   清除失敗: {e}")
    
    # 產生種子資料
    if not args.test_only:
        seed_database(args.num)
    
    # 測試查詢
    show_sample_queries()
    
    print("\n✨ 完成！")
    print("\n💡 提示:")
    print("   1. 資料存入 case_library Collection (不是 user_history)")
    print("   2. 需在 MongoDB Atlas 建立 Vector Search Index:")
    print("      - Collection: case_library")
    print("      - Index name: vector_index")
    print("      - Path: embedding")
    print("   3. 索引建立可能需要幾分鐘")
    print("   4. 詳見 MONGODB_RAG.md")


if __name__ == "__main__":
    main()
