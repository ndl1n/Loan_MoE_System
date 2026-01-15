# 測試套件說明

## 📁 目錄結構

```
tests/
├── __init__.py              # 測試套件入口
├── conftest.py              # pytest 配置與共用 fixtures
├── fixtures/                # 測試資料
│   ├── __init__.py
│   └── mock_data.py         # Mock 資料生成器
├── unit/                    # 單元測試
│   ├── __init__.py
│   ├── test_config.py       # 配置測試
│   ├── test_conversation.py # 對話模組測試
│   ├── test_moe.py          # MoE 路由測試
│   ├── test_experts.py      # 專家模組測試
│   └── test_services.py     # 服務模組測試
├── integration/             # 整合測試
│   ├── __init__.py
│   ├── test_conversation_moe.py  # 對話→MoE 整合
│   └── test_expert_system.py     # 專家系統整合
└── e2e/                     # 端到端測試
    ├── __init__.py
    ├── test_full_flow.py    # 完整流程測試
    └── test_user_journey.py # 使用者旅程測試
```

## 🧪 測試類型說明

### 單元測試 (Unit Tests)
測試各模組的獨立功能，不依賴外部服務。

| 檔案 | 測試內容 |
|------|----------|
| `test_config.py` | 配置載入、參數設定、標籤映射 |
| `test_conversation.py` | 欄位驗證、對話管理、工具函數 |
| `test_moe.py` | Profile 適配、狀態管理、路由邏輯 |
| `test_experts.py` | LDE/DVE/FRE 各專家的核心邏輯 |
| `test_services.py` | MongoDB、RAG 服務 |

### 整合測試 (Integration Tests)
測試模組間的串接是否正確。

| 檔案 | 測試內容 |
|------|----------|
| `test_conversation_moe.py` | 對話系統 → MoE 路由的資料傳遞 |
| `test_expert_system.py` | LDE ↔ DVE ↔ FRE 之間的協作 |

### 端到端測試 (E2E Tests)
測試完整的使用者流程。

| 檔案 | 測試內容 |
|------|----------|
| `test_full_flow.py` | 完整申請流程、邊界情況、系統韌性 |
| `test_user_journey.py` | 使用者對話模擬、回應驗證 |

## 🚀 執行測試

### 使用測試執行器
```bash
# 執行所有測試
python run_tests.py

# 只執行單元測試
python run_tests.py unit

# 只執行整合測試
python run_tests.py integration

# 只執行端到端測試
python run_tests.py e2e

# 執行特定檔案
python run_tests.py -f tests/unit/test_config.py

# 計算覆蓋率
python run_tests.py -c
```

### 直接使用 pytest
```bash
# 執行所有測試
pytest tests/ -v

# 執行特定目錄
pytest tests/unit/ -v

# 執行特定檔案
pytest tests/unit/test_config.py -v

# 執行特定測試類別
pytest tests/unit/test_config.py::TestConfig -v

# 執行特定測試函數
pytest tests/unit/test_config.py::TestConfig::test_device_detection -v

# 使用標記過濾
pytest -m "unit" -v
pytest -m "not requires_redis" -v
```

## 📋 測試標記 (Markers)

| 標記 | 說明 |
|------|------|
| `@pytest.mark.unit` | 單元測試 |
| `@pytest.mark.integration` | 整合測試 |
| `@pytest.mark.e2e` | 端到端測試 |
| `@pytest.mark.slow` | 執行較慢的測試 |
| `@pytest.mark.requires_redis` | 需要 Redis |
| `@pytest.mark.requires_mongodb` | 需要 MongoDB |
| `@pytest.mark.requires_llm` | 需要本地 LLM |
| `@pytest.mark.requires_gemini` | 需要 Gemini API |

## 🔧 Fixtures 說明

### conftest.py 中的 Fixtures

```python
# 完整 Profile
@pytest.fixture
def sample_profile_complete():
    return {"name": "王小明", "id": "A123456789", ...}

# 不完整 Profile
@pytest.fixture
def sample_profile_incomplete():
    return {"name": "李大華", "id": None, ...}

# Mock Redis
@pytest.fixture
def mock_redis():
    return MagicMock()

# Mock MongoDB
@pytest.fixture
def mock_mongodb():
    return MagicMock()
```

### fixtures/mock_data.py 中的工具

```python
# 生成隨機 Profile
ProfileGenerator.generate_complete_profile(risk_level="low")

# 生成對話流程
ConversationGenerator.generate_conversation_flow(profile)

# 生成 RAG 歷史資料
RAGDataGenerator.generate_history_record(user_id, profile)
```

## ⚠️ 測試注意事項

1. **環境變數**: 確保 `.env` 檔案存在，或設定 `GEMINI_API_KEY`
2. **外部服務**: 部分測試需要 Redis/MongoDB，無法連線時會跳過
3. **LLM 模型**: 需要 Fine-tuned Model 的測試在 CPU 環境會自動跳過
4. **API 配額**: Gemini API 測試可能消耗配額

## 📊 覆蓋率報告

執行 `python run_tests.py -c` 會產生覆蓋率報告：

```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
config.py                           50      5    90%
conversation/conversation_manager   80     10    88%
moe/moe_router.py                   60      8    87%
experts/lde/lde_expert.py          100     15    85%
...
-----------------------------------------------------
TOTAL                              500     60    88%
```

## 🔄 CI/CD 整合

可在 GitHub Actions 中使用：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt pytest
      - run: python run_tests.py unit
```
