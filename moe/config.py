"""
MoE 模型配置檔
(從主配置檔導入)
"""

import sys
import os

# 確保可以找到主配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DEVICE,
    MOE_MODEL_PATH as MODEL_PATH,
    STRUCT_DIM,
    MAX_LEN,
    ID2LABEL,
    LABEL2ID,
    STATUS_MAP,
    RISK_HIGH_KWS,
    RISK_LOW_KWS,
    TECH_KEYWORDS,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_LOW,
    CONFIDENCE_THRESHOLD
)

# 導出給其他模組使用
__all__ = [
    'DEVICE',
    'MODEL_PATH',
    'STRUCT_DIM',
    'MAX_LEN',
    'ID2LABEL',
    'LABEL2ID',
    'STATUS_MAP',
    'RISK_HIGH_KWS',
    'RISK_LOW_KWS',
    'TECH_KEYWORDS',
    'RISK_THRESHOLD_HIGH',
    'RISK_THRESHOLD_LOW',
    'CONFIDENCE_THRESHOLD'
]

# ==========================================
# 💡 訓練資料範例 (供參考)
# ==========================================

TRAINING_EXAMPLES = [
    {
        "description": "資料不完整 (id=null) → LDE",
        "input": {
            "user_query": "我們家是單親家庭,媽媽一個人賺錢很辛苦,有什麼貸款可以減輕負擔嗎?",
            "profile_state": {
                "name": "吳俊彥",
                "id": None,
                "job": "公務員",
                "income": 75000,
                "purpose": "醫療費用",
                "amount": 700000
            },
            "verification_status": "unknown"
        },
        "label": "LDE"
    },
    {
        "description": "補件需求 (pending) → DVE",
        "input": {
            "user_query": "補件",
            "profile_state": {
                "name": "周志遠",
                "id": "A122333444",
                "job": "教師",
                "income": 60000,
                "purpose": "房屋頭期款",
                "amount": 750000
            },
            "verification_status": "pending"
        },
        "label": "DVE"
    },
    {
        "description": "額度申覆 (verified) → FRE",
        "input": {
            "user_query": "額度太低,想申覆",
            "profile_state": {
                "name": "劉宇軒",
                "id": "K177788899",
                "job": "自由業",
                "income": 70000,
                "purpose": "教育費",
                "amount": 700000
            },
            "verification_status": "verified"
        },
        "label": "FRE"
    }
]

# ==========================================
# 🧪 測試配置
# ==========================================

# 是否啟用規則式 Fallback
ENABLE_RULE_FALLBACK = True

# 是否記錄詳細推理過程
ENABLE_INFERENCE_LOGGING = True

# 測試模式 (跳過模型載入)
TEST_MODE = False