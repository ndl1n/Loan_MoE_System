# MongoDB 資料架構與 RAG 設定指南

## 📋 概述

本系統使用兩個 MongoDB Collection，各司其職：

| Collection | 用途 | 查詢方式 | 使用者 |
|:-----------|:-----|:---------|:-------|
| `user_history` | 每個用戶的申請紀錄 | 精確查詢 (by user_id) | **DVE** |
| `case_library` | 匿名歷史案例 (RAG) | Vector Search | **FRE** |

### 各 Expert 的資料使用

| Expert | 資料來源 | 說明 |
|:-------|:---------|:-----|
| **LDE** | 無 | 只負責問答和引導，不使用資料庫 |
| **DVE** | `user_history` | 精確查詢「這個人」的歷史，驗證資料一致性 |
| **FRE** | `case_library` | Vector Search 找「相似案例」，輔助決策 |

---

## 🗄️ Collection 結構

### 1. user_history (DVE 驗證用)

存放每個用戶的申請紀錄，用於 DVE 驗證資料一致性。

```json
{
  "_id": "ObjectId",
  "user_id": "A123456789",
  "content": "職業:軟體工程師，月薪:80000...",
  "metadata": {
    "hist_job": "軟體工程師",
    "hist_income": 80000,
    "hist_phone": "0912345678",
    "hist_company": "台積電",
    "has_default_record": false,
    "last_risk_level": "LOW"
  },
  "doc_type": "verification",
  "created_at": 1704067200.0
}
```

**查詢方式**: 精確查詢 (不需要 Vector Index)
```python
# DVE 驗證時
history = rag_engine.get_user_history_by_id("A123456789")
result = rag_engine.verify_against_history("A123456789", current_data)
```

### 2. case_library (FRE RAG 用)

存放匿名化的歷史案例，供 FRE 決策時參考。

```json
{
  "_id": "ObjectId",
  "case_id": "seed_00001",
  "content": "職業:軟體工程師，月薪:80000，貸款金額:500000，用途:購車，審核結果:核准_PASS",
  "embedding": [0.023, -0.118, 0.045, ...],  // 384 維向量
  "metadata": {
    "hist_job": "軟體工程師",
    "hist_income": 80000,
    "amount": 500000,
    "approved_amount": 500000,
    "rate": 2.5,
    "final_decision": "核准_PASS",
    "job_stability": "high"
  },
  "created_at": 1704067200.0
}
```

**查詢方式**: Vector Search (需要建立 Vector Index)
```python
# FRE 決策時
result = rag_engine.get_reference_for_decision(
    profile={"job": "工程師", "income": 80000, "amount": 500000},
    dve_risk_level="LOW"
)
```

---

## 🔧 設定步驟

### 1. 建立 MongoDB Atlas 帳號

1. 前往 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. 建立 M0 Cluster (免費)
3. 設定 Database Access
4. 設定 Network Access

### 2. 建立 Collections

在 Atlas Console 建立：
- Database: `MoE-Finance`
- Collections: `user_history`, `case_library`

### 3. 建立 Vector Search Index (case_library 專用)

⚠️ **只有 case_library 需要 Vector Index**，user_history 不需要。

1. 進入 Atlas Console → Database → Browse Collections
2. 選擇 `MoE-Finance.case_library`
3. 點擊 **Search Indexes** → **Create Search Index**
4. 選擇 **JSON Editor**，貼上：

```json
{
  "name": "vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 384,
        "similarity": "cosine"
      }
    ]
  }
}
```

### 4. (可選) 建立 Text Index

為 case_library 建立文字索引作為備援：

```python
db.case_library.create_index([("content", "text")])
```

---

## 🌱 產生種子資料

為了讓 FRE 有案例可以參考，需要先產生種子資料：

```bash
# 產生 100 筆模擬案例到 case_library
python scripts/seed_rag_data.py

# 產生 500 筆
python scripts/seed_rag_data.py -n 500

# 清除舊資料後重新產生
python scripts/seed_rag_data.py --clear -n 200

# 只測試查詢
python scripts/seed_rag_data.py --test-only
```

### 輸出範例

```
🌱 開始產生 100 筆種子資料到 case_library...
==================================================
  ✓ 已產生 10/100 筆...
  ...
==================================================
✅ 完成！成功: 100, 失敗: 0

📊 審核結果分布:
   核准_PASS: 65 (65.0%)
   拒絕_REJECT: 25 (25.0%)
   轉介審核_ESCALATE: 10 (10.0%)

📚 測試 case_library RAG 查詢 (FRE 用)
==================================================

🔍 查詢 Profile: {'job': '軟體工程師', 'income': 80000, ...}
   核准率: 80%
   平均核准金額: 520,000
   建議: 相似案例核准率 80%，建議核准
   相似案例 (3 筆):
      1. 軟體工程師 / 85000 / 核准_PASS (相似度: 92%)
      2. 資深工程師 / 90000 / 核准_PASS (相似度: 87%)
```

---

## 📊 使用方式

### DVE 驗證 (user_history)

```python
from services.rag_service import rag_engine

# 查詢用戶歷史
history = rag_engine.get_user_history_by_id("A123456789")

# 驗證資料一致性
result = rag_engine.verify_against_history(
    user_id="A123456789",
    current_data={
        "job": "軟體工程師",
        "income": 85000,
        "phone": "0912345678"
    }
)

print(result)
# {
#     "has_history": True,
#     "mismatches": [],
#     "risk_level": "LOW"
# }
```

### FRE 決策參考 (case_library)

```python
from services.rag_service import rag_engine

# 取得相似案例參考
result = rag_engine.get_reference_for_decision(
    profile={
        "job": "軟體工程師",
        "income": 80000,
        "amount": 500000,
        "purpose": "購車"
    },
    dve_risk_level="LOW",
    top_k=3
)

print(f"核准率: {result['approval_rate']:.0%}")
print(f"平均核准金額: {result['avg_approved_amount']:,.0f}")
print(f"建議: {result['recommendation']}")

# 核准率: 80%
# 平均核准金額: 520,000
# 建議: 相似案例核准率 80%，建議核准
```

---

## ⚠️ 常見問題

### Q1: Vector Search 報錯

**原因**: 尚未在 case_library 建立 `vector_index`

**解決**: 按照上面步驟 3 建立索引

### Q2: user_history 需要 Vector Index 嗎？

**不需要**！user_history 只用精確查詢 (by user_id)，不需要語意搜尋。

### Q3: 兩個 Collection 有關聯嗎？

目前設計是獨立的：
- `user_history`: 個人化資料，含 user_id
- `case_library`: 匿名案例，不含 user_id

未來可考慮：當用戶申請結束後，將匿名化的資料也存入 case_library。

---

## 📁 相關檔案

| 檔案 | 說明 |
|:-----|:-----|
| `services/rag_service.py` | RAG 服務 (管理兩個 Collection) |
| `services/database.py` | MongoDB 連線 |
| `scripts/seed_case_data.py` | case 資料產生器 |
| `scripts/seed_user_data.py` | user 資料寫入器 |
| `experts/dve/dve_expert.py` | DVE (使用 user_history) |
| `experts/fre/fre_expert.py` | FRE (使用 case_library) |

---

## 🔗 參考資源

- [MongoDB Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/)
- [all-MiniLM-L6-v2 模型](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
