"""
主配置檔 - 整合所有模組的配置
"""

import torch
import os
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# ==========================================
# 📁 路徑設定
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 🔑 API Keys
# ==========================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ 錯誤: 未讀取到 GEMINI_API_KEY,請檢查 .env 檔案。")

# ==========================================
# 🤖 Gemini 設定
# ==========================================

GEMINI_MODEL_NAME = 'gemini-2.5-flash-lite'

# ==========================================
# 💻 設備設定
# ==========================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==========================================
# 🧠 MoE 模型設定
# ==========================================

# MoE Gating Model 路徑
MOE_MODEL_PATH = os.path.join(BASE_DIR, 'moe', 'models', 'saved_moe_gating_model.pth')

# MoE 參數
MAX_LEN = 64
STRUCT_DIM = 7  # id, name, job, income, status_val, sparsity, risk_score

# 標籤映射
ID2LABEL = {0: "LDE", 1: "DVE", 2: "FRE"}
LABEL2ID = {"LDE": 0, "DVE": 1, "FRE": 2}

# 狀態映射
STATUS_MAP = {
    "unknown": 0,
    "pending": 1,
    "verified": 2,
    "mismatch": 3
}

# ==========================================
# 🎓 Fine-tuned Models 設定
# ==========================================

# Base Model (所有專家共用)
BASE_MODEL_PATH = os.getenv(
    "BASE_MODEL_PATH",
    "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
)

# 是否啟用 Fine-tuned Models (如果 GPU 記憶體不足,設為 False)
ENABLE_FINETUNED_MODELS = os.getenv("ENABLE_FINETUNED_MODELS", "True").lower() == "true"

# LDE Adapter
LDE_ADAPTER_PATH = os.path.join(BASE_DIR, "models", "LDE_adapter")

# DVE Adapter
DVE_ADAPTER_PATH = os.path.join(BASE_DIR, "models", "DVE_adapter")

# FRE Adapter
FRE_ADAPTER_PATH = os.path.join(BASE_DIR, "models", "FRE_adapter")

# ==========================================
# 🔧 生成參數
# ==========================================

GENERATION_CONFIG = {
    "max_new_tokens": 256,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": True
}

# ==========================================
# ⚖️ 訓練參數 (Lazy Loading)
# ==========================================

# 改為函數，避免 import 時就執行 .to(DEVICE)
def get_loss_weights():
    """取得損失權重 (Lazy Loading)"""
    return torch.tensor([1.0, 2.5, 2.5]).to(DEVICE)

# ==========================================
# 🛡️ 風險關鍵字
# ==========================================

# 高風險職業關鍵字
RISK_HIGH_KWS = [
    "學生", "攤販", "博弈", "八大", "無業",
    "現金", "家管", "臨時工", "打工", "待業", "服務生",
    "自由業"  # 根據訓練資料新增
]

# 低風險職業關鍵字
RISK_LOW_KWS = [
    "公務員", "醫師", "律師", "會計師", "老師",
    "教授", "台積電", "百大", "護理師", "警察", 
    "銀行", "工程師", "教師"  # 根據訓練資料新增
]

# 技術問題關鍵字 (導向 DVE)
TECH_KEYWORDS = [
    "失敗", "無法", "傳不上去", "太大", "格式",
    "錯誤", "當機", "重傳", "補件", "補上",
    "上傳", "模糊", "不清楚", "只給", "替代", "壞掉",
    "系統", "驗證"
]

# ==========================================
# 💡 Prompt Templates
# ==========================================

# === LDE System Instruction ===
LDE_SYSTEM_INSTRUCTION = """你是一位專業、嚴謹且中立的 [中國信託銀行] 貸款徵審人員（LDE）。你的任務是根據標準照會 SOP,引導貸款申請人（用戶）提供清晰、完整且無矛盾的資訊,並維持對話的專業性。

**【角色與語氣規範】**
1. 你的語氣必須**中立、專業,避免使用任何表情符號或過度熱情的詞彙**。
2. 你的回答必須**簡潔且精準**,不可提供額外的通用金融建議。
3. **必須**使用繁體中文,並遵循台灣金融機構的慣用語。
4. 每次回答後,如果資訊不完整或存在潛在風險點,你**必須**以「追問」結束你的回答,引導用戶進行下一步的資訊提供。

**【流程與追問策略規範】**
1. **[核心追問]**: 當用戶提供的資金用途、工作內容、收入來源等資訊模糊時,你必須立即提出「**細節深化**」的追問,直到取得具體名詞或數據。
2. **[數據比對]**: 你必須參考 [RAG 檢索結果]。若發現用戶口述與檢索結果有潛在不一致,你必須在回答中**間接或委婉地提出交叉核對的問題**（例如: 根據您申請書上的資料,您的職務是...,是否與您剛才提到職務有所調整?）。
3. **[流程推進]**: 你的回答必須能有效推進對話至下一階段（如從「身份核實」轉向「資金用途」）。"""

# === LDE Prompt Template (Alpaca Style) ===
LDE_PROMPT_TEMPLATE = """### Instruction:
{instruction}

### Input:
{input_text}

### Output:
"""

# === DVE Prompt Template ===
DVE_PROMPT_TEMPLATE = """你是一位專門負責數據核實與風險標記的徵審系統專家（DVE）。你的核心任務是根據 Flask Server 彙整的【最新口述資訊】與【RAG 檢索的歷史數據】,執行嚴格且客觀的【一對一比對驗證】。你的輸出必須是一個完整的、可機讀的結構化風險標記報告,不得包含任何對話、疑問、流程建議或通用金融知識。

【DVE 判斷規則約束】
1. 風險標記標準 (優先級由高到低):
- 高風險 (HIGH): 歷史違約紀錄**為**「有」**;或** 職業、公司名稱、聯絡電話**同時**不符。
- 中風險 (MEDIUM): (職業 **或** 公司名稱 **或** 聯絡電話 **或** 資金用途 **或** 月薪) 任一不符;或 任何欄位為「資料不足」;或 `信用報告查詢次數` 過高（> N次）。
- 低風險 (LOW): 所有比對欄位皆「一致」且「無異狀」。

2. 建議行動 (與風險標記對應):
- HIGH: 轉 LDE 啟動交叉追問 (ACT_LDE_CROSS)
- MEDIUM: 轉 FRE 進行決策 (ACT_FRE_DECIDE)
- LOW: 系統自動核准 (ACT_PASS)

### Instruction:
{instruction}

### Input:
{input_text}

### Output:
"""

DVE_INSTRUCTION = "請根據上述規則,比對 Input 資料並輸出 DVE 風險標記報告 (JSON)。"

# === FRE Prompt Template ===
FRE_PROMPT_TEMPLATE = """你是一位「FRE 最終風險決策模型」的訓練數據生成專家。
你的核心任務是讀取一份【客戶完整申請資料】（包含 DVE/FRE 的所有 Input）,並根據內建的【風險決策規則】和【授信政策閾值】,
『正向推導』出一個邏輯一致、且具備高解釋性的 FRE 決策報告。

【你的內建風險決策規則 (FRE 政策)】
1.  DVE 初判 (用於設定 'dve_risk_label'):
    - 高風險 (HIGH): 歷史違約紀錄**為**「有」;**或** 職業、公司名稱、聯絡電話**同時**不符。
    - 中風險 (MEDIUM): (職業 **或** 公司名稱 **或** 聯絡電話 **或** 月薪) 任一不符;或 歷史違約紀錄為「輕微遲繳/已結清」。
    - 低風險 (LOW): 所有比對欄位皆「一致」且「無異狀」。

2.  FRE 最終決策 (用於設定 'final_decision'):
    - **拒絕 (REJECT):** DVE 初判為 HIGH;或 信用評分 < 650;或 負債比率 > 45%。
    - **轉介審核 (ESCALATE):** DVE 初判為 MEDIUM,但信用分數 > 650;或 薪資差異率 (口述/歷史) > 20% 且 < 40%。(需人工介入,可能要求補件)
    - **核准 (PASS):** DVE 初判為 LOW;或 DVE 初判為 MEDIUM 但所有核心財務指標 (分數/負債比) 均優秀且符合政策。

3.  Output 格式約束:
    - 你的輸出**必須**是且**僅是**一個 JSON 物件。
    - 請使用 '核准_PASS', '拒絕_REJECT', '轉介審核_ESCALATE' 作為 '最終決策' 的值。
    - 必須包含量化的「風險權重」和中文的「整合判讀」。

### Instruction:
{instruction}

### Input:
{input_text}

### Output:
"""

FRE_INSTRUCTION = "請根據上述規則與 Input 資料,生成符合格式的 FRE 決策報告 (JSON)。"

# ==========================================
# 📊 Redis 設定 (對話系統)
# ==========================================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
SESSION_TTL = int(os.getenv("SESSION_TTL", 3600))

# ==========================================
# 🗄️ MongoDB 設定
# ==========================================

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "MoE-Finance")

# ==========================================
# 🎯 MoE 路由閾值
# ==========================================

# 風險分數閾值
RISK_THRESHOLD_HIGH = 0.7
RISK_THRESHOLD_LOW = 0.3

# AI 信心度閾值
CONFIDENCE_THRESHOLD = 0.6

# ==========================================
# 📝 日誌配置
# ==========================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'