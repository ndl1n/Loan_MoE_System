"""
config.py 單元測試
測試配置載入與參數設定
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestConfig:
    """配置測試"""
    
    def test_device_detection(self):
        """測試設備檢測"""
        from config import DEVICE
        import torch
        
        # 應該是 cuda 或 cpu
        assert DEVICE.type in ["cuda", "cpu"]
        
        # 如果有 GPU，應該檢測到
        if torch.cuda.is_available():
            assert DEVICE.type == "cuda"
        else:
            assert DEVICE.type == "cpu"
    
    def test_path_configuration(self):
        """測試路徑配置"""
        from config import BASE_DIR, MOE_MODEL_PATH, LDE_ADAPTER_PATH
        
        assert os.path.isabs(BASE_DIR), "BASE_DIR 應該是絕對路徑"
        assert "moe" in MOE_MODEL_PATH, "MOE_MODEL_PATH 應該包含 moe"
        assert "LDE" in LDE_ADAPTER_PATH, "LDE_ADAPTER_PATH 應該包含 LDE"
    
    def test_label_mappings(self):
        """測試標籤映射"""
        from config import ID2LABEL, LABEL2ID
        
        # 應該有 3 個專家
        assert len(ID2LABEL) == 3
        assert len(LABEL2ID) == 3
        
        # 雙向映射應該一致
        for idx, label in ID2LABEL.items():
            assert LABEL2ID[label] == idx
        
        # 必須包含所有專家
        assert "LDE" in LABEL2ID
        assert "DVE" in LABEL2ID
        assert "FRE" in LABEL2ID
    
    def test_status_mapping(self):
        """測試狀態映射"""
        from config import STATUS_MAP
        
        required_statuses = ["unknown", "pending", "verified", "mismatch"]
        for status in required_statuses:
            assert status in STATUS_MAP, f"STATUS_MAP 應該包含 {status}"
    
    def test_prompt_templates(self):
        """測試 Prompt Templates"""
        from config import (
            LDE_PROMPT_TEMPLATE,
            DVE_PROMPT_TEMPLATE,
            FRE_PROMPT_TEMPLATE
        )
        
        # 每個 template 應該有佔位符
        assert "{instruction}" in LDE_PROMPT_TEMPLATE
        assert "{input_text}" in LDE_PROMPT_TEMPLATE
        
        assert "{instruction}" in DVE_PROMPT_TEMPLATE
        assert "{input_text}" in DVE_PROMPT_TEMPLATE
        
        assert "{instruction}" in FRE_PROMPT_TEMPLATE
        assert "{input_text}" in FRE_PROMPT_TEMPLATE
    
    def test_threshold_values(self):
        """測試閾值設定"""
        from config import (
            RISK_THRESHOLD_HIGH,
            RISK_THRESHOLD_LOW,
            CONFIDENCE_THRESHOLD
        )
        
        # 閾值應該在合理範圍
        assert 0 < RISK_THRESHOLD_LOW < RISK_THRESHOLD_HIGH < 1
        assert 0 < CONFIDENCE_THRESHOLD < 1
    
    def test_risk_keywords(self):
        """測試風險關鍵字"""
        from config import RISK_HIGH_KWS, RISK_LOW_KWS
        
        assert len(RISK_HIGH_KWS) > 0, "高風險關鍵字不應為空"
        assert len(RISK_LOW_KWS) > 0, "低風險關鍵字不應為空"
        
        # 確保沒有重疊
        overlap = set(RISK_HIGH_KWS) & set(RISK_LOW_KWS)
        assert len(overlap) == 0, f"高低風險關鍵字不應重疊: {overlap}"
    
    def test_get_loss_weights(self):
        """測試損失權重函數"""
        from config import get_loss_weights, DEVICE
        
        weights = get_loss_weights()
        
        assert weights.shape[0] == 3, "應該有 3 個權重 (對應 3 個專家)"
        assert weights.device.type == DEVICE.type, "權重應該在正確的設備上"


class TestConfigEnvironment:
    """環境變數測試"""
    
    def test_gemini_api_key_loaded(self):
        """測試 Gemini API Key 載入"""
        # 這個測試需要 .env 檔案存在
        # 在 CI 環境可能會失敗，標記為可選
        try:
            from config import GEMINI_API_KEY
            assert GEMINI_API_KEY is not None
            assert len(GEMINI_API_KEY) > 0
        except ValueError:
            pytest.skip("GEMINI_API_KEY 未設定")
    
    def test_redis_config(self):
        """測試 Redis 配置"""
        from config import REDIS_HOST, REDIS_PORT, REDIS_DB, SESSION_TTL
        
        assert isinstance(REDIS_HOST, str)
        assert isinstance(REDIS_PORT, int)
        assert isinstance(REDIS_DB, int)
        assert isinstance(SESSION_TTL, int)
        assert SESSION_TTL > 0
