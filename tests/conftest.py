"""
測試配置與共用工具
conftest.py - pytest 自動載入
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# 確保可以 import 專案模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==========================================
# 📦 Fixtures - 測試資料
# ==========================================

@pytest.fixture
def sample_profile_complete():
    """完整的使用者 Profile"""
    return {
        "name": "王小明",
        "id": "A123456789",
        "phone": "0912-345-678",
        "job": "軟體工程師",
        "income": 80000,
        "loan_purpose": "購車",
        "amount": 500000,
        "company": "台積電",
        "verification_status": None,
        "last_asked_field": None,
        "retry_count": 0
    }


@pytest.fixture
def sample_profile_incomplete():
    """不完整的使用者 Profile"""
    return {
        "name": "李大華",
        "id": None,
        "phone": None,
        "job": None,
        "income": None,
        "loan_purpose": None,
        "amount": None,
        "verification_status": None
    }


@pytest.fixture
def sample_profile_high_risk():
    """高風險 Profile"""
    return {
        "name": "張三",
        "id": "B987654321",
        "phone": "0987-654-321",
        "job": "無業",
        "income": 20000,
        "loan_purpose": "債務整合",
        "amount": 1000000,
        "verification_status": "pending"
    }


@pytest.fixture
def sample_profile_low_risk():
    """低風險 Profile"""
    return {
        "name": "陳醫師",
        "id": "C111222333",
        "phone": "0911-222-333",
        "job": "醫師",
        "income": 200000,
        "loan_purpose": "購屋頭期款",
        "amount": 500000,
        "verification_status": "pending"
    }


@pytest.fixture
def sample_moe_input():
    """MoE 路由的標準輸入"""
    return {
        "profile_state": {
            "name": "王小明",
            "id": "A123456789",
            "job": "工程師",
            "income": 70000,
            "purpose": "購車",
            "amount": 500000
        },
        "verification_status": "pending",
        "user_query": "我想申請貸款"
    }


@pytest.fixture
def sample_conversation_history():
    """對話歷史"""
    return [
        {"role": "assistant", "content": "請問您的姓名是?", "timestamp": 1700000000},
        {"role": "user", "content": "我是王小明", "timestamp": 1700000010},
        {"role": "assistant", "content": "請問您的身分證字號是?", "timestamp": 1700000020},
        {"role": "user", "content": "A123456789", "timestamp": 1700000030},
    ]


@pytest.fixture
def sample_rag_history():
    """RAG 歷史紀錄 (user_history)"""
    return [
        {
            "user_id": "A123456789",
            "content": "歷史申請紀錄",
            "metadata": {
                "name": "王小明",
                "hist_job": "工程師",
                "hist_income": "70000",
                "hist_phone": "0912-345-678",
                "hist_purpose": "購車",
                "hist_company": "科技公司",
                "default_record": "無",
                "inquiry_count": "2"
            }
        }
    ]


@pytest.fixture
def sample_case_library():
    """RAG 案例庫 (case_library)"""
    return [
        {
            "content": "職業:軟體工程師，月薪:80000，貸款金額:500000，審核結果:核准_PASS",
            "embedding": [0.1] * 384,
            "metadata": {
                "hist_job": "軟體工程師",
                "hist_income": 80000,
                "amount": 500000,
                "approved_amount": 500000,
                "final_decision": "核准_PASS",
                "rate": 2.5
            },
            "score": 0.92
        },
        {
            "content": "職業:業務員，月薪:45000，貸款金額:800000，審核結果:拒絕_REJECT",
            "embedding": [0.1] * 384,
            "metadata": {
                "hist_job": "業務員",
                "hist_income": 45000,
                "amount": 800000,
                "approved_amount": 0,
                "final_decision": "拒絕_REJECT"
            },
            "score": 0.75
        }
    ]


@pytest.fixture
def sample_fre_task_data():
    """FRE 專用 task_data"""
    return {
        "user_query": "請幫我審核",
        "profile_state": {
            "name": "王小明",
            "id": "A123456789",
            "job": "軟體工程師",
            "income": 80000,
            "purpose": "購車",
            "amount": 500000,
            "company": "台積電"
        },
        "verification_status": "verified",
        "dve_result": {
            "risk_level": "LOW",
            "check_status": "CHECKED",
            "mismatches": []
        }
    }


# ==========================================
# 🔧 Mock Fixtures
# ==========================================

@pytest.fixture
def mock_redis():
    """Mock Redis Client"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.ping.return_value = True
    mock.pipeline.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB Collection"""
    mock = MagicMock()
    mock.find.return_value = []
    mock.insert_one.return_value = MagicMock(inserted_id="mock_id")
    mock.aggregate.return_value = []
    return mock


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API Response"""
    mock = MagicMock()
    mock.text = '{"name": "王小明", "income": 50000}'
    return mock


@pytest.fixture
def mock_llm_manager():
    """Mock LLM Manager"""
    mock = MagicMock()
    mock.get_expert_response.return_value = "這是一個測試回應"
    mock._tokenizer = MagicMock()
    mock._base_model = MagicMock()
    return mock


# ==========================================
# 🛠️ Helper Functions
# ==========================================

def create_task_data(
    user_query: str = "測試問題",
    profile: Dict = None,
    verification_status: str = "pending"
) -> Dict[str, Any]:
    """建立標準 task_data"""
    if profile is None:
        profile = {
            "name": "測試用戶",
            "id": "T123456789",
            "job": "工程師",
            "income": 60000,
            "purpose": "週轉",
            "amount": 300000
        }
    
    return {
        "user_query": user_query,
        "profile_state": profile,
        "verification_status": verification_status
    }


def assert_expert_response_structure(response: Dict):
    """驗證專家回應的結構"""
    required_keys = ["expert", "response", "next_step"]
    for key in required_keys:
        assert key in response, f"回應缺少必要欄位: {key}"
    
    assert isinstance(response["response"], str), "response 必須是字串"
    assert len(response["response"]) > 0, "response 不能為空"


def assert_routing_result_structure(result: tuple):
    """驗證路由結果的結構"""
    assert len(result) == 4, "路由結果必須有 4 個元素"
    expert, confidence, reason, info = result
    
    assert expert in ["LDE", "DVE", "FRE"], f"無效的專家: {expert}"
    assert 0 <= confidence <= 1, f"信心度必須在 0~1 之間: {confidence}"
    assert isinstance(reason, str), "reason 必須是字串"
    assert isinstance(info, dict), "info 必須是字典"
