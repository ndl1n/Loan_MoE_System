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
# 🧪 測試配置
# ==========================================

# 是否啟用規則式 Fallback
ENABLE_RULE_FALLBACK = True

# 是否記錄詳細推理過程
ENABLE_INFERENCE_LOGGING = True

# 測試模式 (跳過模型載入)
TEST_MODE = False
