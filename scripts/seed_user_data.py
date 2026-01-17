import sys
import os
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import mongo_db
from src.rag_service import rag_engine

def seed_database():
    print("🚀 開始執行資料庫重灌程序 (針對 DVE 優化版)...")
    
    DATA_FILE = "data/full_history_data.json"
    
    # 檢查檔案
    if not os.path.exists(DATA_FILE):
        print(f"⚠️ 找不到 {DATA_FILE}，請先建立檔案並貼上您的資料。")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 清空舊資料
    try:
        col = mongo_db.get_collection("user_history")
        col.delete_many({})
        print("🗑️ 已清空舊資料庫。")
    except Exception as e:
        print(f"❌ 資料庫連線失敗: {e}")
        return

    print("🌊 開始轉換資料...")
    success_count = 0

    for case in raw_data:
        try:
            # --- 1. 提取原始資料 ---
            identity = case.get("customerIdentity", {})
            history = case.get("historicalData", {})
            credit = case.get("creditReportData", {})
            
            user_id = identity.get("身分證字號")
            name = identity.get("申請人姓名")
            
            if not user_id: continue

            # --- 2. 建立 Content (給語意搜尋用，保持人類可讀) ---
            content_text = (
                f"【銀行內部存檔】客戶：{name} ({user_id})。\n"
                f"職業：{history.get('歷史職業')} @ {history.get('歷史公司名稱')}。\n"
                f"財務：月薪 {history.get('歷史月薪')}，負債 {credit.get('現有總負債金額')}。\n"
                f"違約：{credit.get('歷史違約紀錄')}。"
            )

            # --- 3. 建立 Metadata (給 DVE 精準組裝用) ---
            # 關鍵：在這裡就把 DVE 需要的所有欄位準備好
            metadata = {
                "case_id": case.get("caseId"),
                "name": name,
                
                # [職業與收入]
                "hist_job": history.get("歷史職業"),
                "hist_company": history.get("歷史公司名稱"),
                "hist_income": history.get("歷史月薪"),
                
                # [關鍵比對欄位 - DVE 指定需求]
                "hist_phone": history.get("歷史聯絡電話"),
                "hist_purpose": history.get("歷史資金用途"), # 對應 "上次貸款資金用途"
                "default_record": credit.get("歷史違約紀錄"),
                "inquiry_count": credit.get("信用報告查詢次數_近3月"),
            }

            # --- 4. 寫入 ---
            rag_engine.add_document(user_id=user_id, content=content_text, metadata=metadata)
            success_count += 1

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"✅ 完成！共寫入 {success_count} 筆。Metadata 已優化。")

if __name__ == "__main__":
    seed_database()