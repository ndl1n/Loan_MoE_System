import sys
import os
import json
import time

# 設定路徑以便 import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import mongo_db
from src.rag_service import rag_engine

def seed_database():
    print("🚀 開始執行資料庫重灌程序 (Seed DB) - 完整資料版...")
    
    # 1. 定義資料路徑
    DATA_FILE = "data/full_history_data.json"
    
    # 檢查檔案是否存在
    if not os.path.exists(DATA_FILE):
        print(f"⚠️ 找不到 {DATA_FILE}，請確認檔案路徑。")
        # 這裡為了方便您測試，如果沒檔案，我直接寫入您剛剛提供的這筆範例
        raw_data = [
            {
                "caseId": "CASE_00001",
                "creationDate": "2025-11-12T00:00:00Z",
                "customerIdentity": {
                    "身分證字號": "A123456789",
                    "申請人姓名": "林大衛"
                },
                "applicationData": {
                    "申請金額": 700000,
                    "申請用途_官方": "子女教育金"
                },
                "creditReportData": {
                    "系統原始信用評分": 600,
                    "現有總負債金額": 864000,
                    "歷史違約紀錄": "無",
                    "信用報告查詢次數_近3月": 1
                },
                "historicalData": {
                    "歷史月薪": 60000,
                    "歷史職業": "公立高中教師",
                    "歷史公司名稱": "XX市立高中",
                    "歷史聯絡電話": "0920-987-654",
                    "歷史資金用途": "子女教育金"
                },
                "expectedOutputs": {
                    "dve_risk_label": "LOW",
                    "fre_decision_label": "核准",
                    "fre_decision_code": "APR001"
                }
            }
        ]
        print("   👉 使用內建範例資料進行演示...")
    else:
        print(f"📂 讀取資料檔: {DATA_FILE}")
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

    # 2. 清空現有 Collection (確保環境乾淨)
    try:
        col = mongo_db.get_collection("user_history")
        del_res = col.delete_many({})
        print(f"🗑️ 已清空舊資料庫: 刪除 {del_res.deleted_count} 筆紀錄")
    except Exception as e:
        print(f"❌ 清空資料庫失敗: {e}")
        return

    # 3. 資料轉換與寫入
    print("🌊 開始轉換資料並生成向量 (Embedding)...")
    
    success_count = 0
    start_time = time.time()

    for i, case in enumerate(raw_data):
        try:
            # --- A. 提取資料 ---
            identity = case.get("customerIdentity", {})
            history = case.get("historicalData", {})
            credit = case.get("creditReportData", {})
            app_data = case.get("applicationData", {})
            expected = case.get("expectedOutputs", {})
            
            user_id = identity.get("身分證字號")
            name = identity.get("申請人姓名")
            
            if not user_id:
                print(f"⚠️ 跳過第 {i+1} 筆: 缺少身分證字號")
                continue

            # --- B. 組合 Content (RAG 的核心知識) ---
            # 這裡我們只放「銀行內部事實」，不放「口述資料(Provided Data)」
            # 這樣 DVE 才能拿 User 說的話來跟這段文字做比對
            content_text = (
                f"【銀行內部存檔】\n"
                f"客戶姓名：{name} (身分證: {user_id})\n"
                f"職業紀錄：任職於「{history.get('歷史公司名稱', '未知')}」，職稱為「{history.get('歷史職業', '未知')}」。\n"
                f"財務紀錄：歷史月薪 {history.get('歷史月薪', 0)} 元。現有負債 {credit.get('現有總負債金額', 0)} 元。\n"
                f"聯絡資訊：留存電話 {history.get('歷史聯絡電話', '未知')}。\n"
                f"信用評分：{credit.get('系統原始信用評分', '未知')} 分。違約紀錄：{credit.get('歷史違約紀錄', '無')}。"
            )

            # --- C. 準備 Metadata (擴充版) ---
            # 保留完整的數據結構，方便未來做混合檢索或自動化測試
            metadata = {
                "case_id": case.get("caseId"),
                "name": name,
                "job": history.get("歷史職業"),
                "company": history.get("歷史公司名稱"),
                "income": history.get("歷史月薪"),
                "score": credit.get("系統原始信用評分"),
                # 存入預期結果，方便未來測試腳本驗證準確度
                "expected_risk": expected.get("dve_risk_label"),
                "expected_decision": expected.get("fre_decision_label")
            }

            # --- D. 寫入 MongoDB ---
            rag_engine.add_document(user_id=user_id, content=content_text, metadata=metadata)
            success_count += 1
            
            if success_count % 10 == 0:
                print(f"   已處理 {success_count} 筆資料...")

        except Exception as e:
            print(f"❌ 處理 caseId {case.get('caseId', 'Unknown')} 時發生錯誤: {e}")

    duration = time.time() - start_time
    print("\n" + "="*50)
    print(f"✅ 資料重灌完成！")
    print(f"📊 成功寫入: {success_count} / {len(raw_data)} 筆")
    print(f"⏱️ 總耗時: {duration:.2f} 秒")
    print("="*50)

if __name__ == "__main__":
    seed_database()