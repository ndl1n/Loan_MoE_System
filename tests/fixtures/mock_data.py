"""
測試用 Mock 資料與假資料生成器
"""

import json
import random
from typing import Dict, List, Any
from datetime import datetime


# ==========================================
# 📝 樣本資料
# ==========================================

SAMPLE_NAMES = ["王小明", "李大華", "張美玲", "陳志偉", "林淑芬", "黃建國"]

SAMPLE_JOBS = {
    "low_risk": ["工程師", "醫師", "律師", "教師", "公務員", "銀行員"],
    "medium_risk": ["業務員", "店員", "司機", "廚師", "美容師"],
    "high_risk": ["無業", "學生", "臨時工", "自由業", "攤販"]
}

SAMPLE_PURPOSES = {
    "low_risk": ["購屋", "購車", "教育", "醫療"],
    "medium_risk": ["裝潢", "結婚", "旅遊"],
    "high_risk": ["投資", "債務整合", "週轉", "其他"]
}

SAMPLE_INCOMES = {
    "high": [150000, 200000, 300000],
    "medium": [50000, 60000, 80000],
    "low": [25000, 30000, 35000]
}


# ==========================================
# 🏭 資料生成器
# ==========================================

class ProfileGenerator:
    """Profile 資料生成器"""
    
    @staticmethod
    def generate_id() -> str:
        """生成假身分證字號"""
        letters = "ABCDEFGHJKLMNPQRSTUVXYWZIO"
        first = random.choice(letters)
        second = random.choice("12")
        rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{first}{second}{rest}"
    
    @staticmethod
    def generate_phone() -> str:
        """生成假手機號碼"""
        prefix = "09"
        rest = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{prefix}{rest}"
    
    @classmethod
    def generate_complete_profile(cls, risk_level: str = "medium") -> Dict:
        """
        生成完整 Profile
        
        Args:
            risk_level: "low", "medium", "high"
        """
        if risk_level == "low":
            job = random.choice(SAMPLE_JOBS["low_risk"])
            income = random.choice(SAMPLE_INCOMES["high"])
            purpose = random.choice(SAMPLE_PURPOSES["low_risk"])
            amount = random.randint(300000, 800000)
        elif risk_level == "high":
            job = random.choice(SAMPLE_JOBS["high_risk"])
            income = random.choice(SAMPLE_INCOMES["low"])
            purpose = random.choice(SAMPLE_PURPOSES["high_risk"])
            amount = random.randint(500000, 2000000)
        else:
            job = random.choice(SAMPLE_JOBS["medium_risk"])
            income = random.choice(SAMPLE_INCOMES["medium"])
            purpose = random.choice(SAMPLE_PURPOSES["medium_risk"])
            amount = random.randint(200000, 600000)
        
        return {
            "name": random.choice(SAMPLE_NAMES),
            "id": cls.generate_id(),
            "phone": cls.generate_phone(),
            "job": job,
            "income": income,
            "loan_purpose": purpose,
            "amount": amount,
            "company": f"{job}公司",
            "verification_status": None,
            "last_asked_field": None,
            "retry_count": 0
        }
    
    @classmethod
    def generate_partial_profile(cls, filled_fields: List[str]) -> Dict:
        """
        生成部分填寫的 Profile
        
        Args:
            filled_fields: 要填寫的欄位列表
        """
        complete = cls.generate_complete_profile()
        partial = {k: None for k in complete.keys()}
        
        for field in filled_fields:
            if field in complete:
                partial[field] = complete[field]
        
        return partial


class ConversationGenerator:
    """對話資料生成器"""
    
    QUESTIONS = {
        "name": "請問您的姓名是?",
        "id": "請問您的身分證字號是?",
        "phone": "請問您的手機號碼是?",
        "job": "請問您目前的職業是?",
        "income": "請問您每月大約收入是多少?",
        "loan_purpose": "請問您本次貸款的主要用途是?",
        "amount": "請問您希望申請的貸款金額是多少?"
    }
    
    @classmethod
    def generate_conversation_flow(cls, profile: Dict) -> List[Dict]:
        """
        根據 profile 生成完整對話流程
        """
        history = []
        timestamp = 1700000000
        
        field_order = ["name", "id", "phone", "job", "income", "loan_purpose", "amount"]
        
        for field in field_order:
            if field in cls.QUESTIONS and profile.get(field):
                # 機器人問題
                history.append({
                    "role": "assistant",
                    "content": cls.QUESTIONS[field],
                    "timestamp": timestamp
                })
                timestamp += 5
                
                # 使用者回答
                value = profile[field]
                if field == "income":
                    answer = f"大概{value // 10000}萬"
                elif field == "amount":
                    answer = f"想借{value // 10000}萬"
                else:
                    answer = str(value)
                
                history.append({
                    "role": "user",
                    "content": answer,
                    "timestamp": timestamp
                })
                timestamp += 10
        
        return history


class RAGDataGenerator:
    """RAG 歷史資料生成器"""
    
    @staticmethod
    def generate_history_record(
        user_id: str,
        profile: Dict,
        risk_level: str = "LOW"
    ) -> Dict:
        """生成 RAG 歷史紀錄"""
        return {
            "user_id": user_id,
            "content": f"【銀行內部存檔】客戶: {profile.get('name', 'Unknown')}",
            "metadata": {
                "name": profile.get("name"),
                "hist_job": profile.get("job"),
                "hist_income": str(profile.get("income", 0)),
                "hist_phone": profile.get("phone"),
                "hist_purpose": profile.get("loan_purpose"),
                "hist_company": profile.get("company"),
                "default_record": "無",
                "inquiry_count": str(random.randint(1, 5)),
                "last_risk_level": risk_level
            },
            "created_at": datetime.now().timestamp()
        }
    
    @staticmethod
    def generate_mismatched_record(
        user_id: str,
        profile: Dict
    ) -> Dict:
        """生成與當前資料不符的歷史紀錄"""
        return {
            "user_id": user_id,
            "content": f"【銀行內部存檔】客戶: {profile.get('name', 'Unknown')}",
            "metadata": {
                "name": profile.get("name"),
                "hist_job": "完全不同的職業",  # 故意不符
                "hist_income": str(profile.get("income", 0) * 2),  # 故意不符
                "hist_phone": "0999-999-999",  # 故意不符
                "hist_purpose": profile.get("loan_purpose"),
                "hist_company": "不同公司",
                "default_record": "有",  # 有違約紀錄
                "inquiry_count": "10",
                "last_risk_level": "HIGH"
            }
        }


# ==========================================
# 📊 測試案例集
# ==========================================

TEST_CASES = {
    "conversation_extraction": [
        {
            "input": "我叫王小明",
            "expected_field": "name",
            "expected_value": "王小明"
        },
        {
            "input": "月薪大概5萬",
            "expected_field": "income",
            "expected_value": 50000
        },
        {
            "input": "想借50萬買車",
            "expected_fields": {"amount": 500000, "loan_purpose": "購車"}
        },
        {
            "input": "A123456789",
            "expected_field": "id",
            "expected_value": "A123456789"
        },
        {
            "input": "0912345678",
            "expected_field": "phone",
            "expected_value": "0912-345-678"
        }
    ],
    
    "moe_routing": [
        {
            "description": "unknown 狀態 → LDE",
            "verification_status": "unknown",
            "expected_expert": "LDE"
        },
        {
            "description": "pending 狀態 → DVE",
            "verification_status": "pending",
            "expected_expert": "DVE"
        },
        {
            "description": "verified 狀態 → FRE",
            "verification_status": "verified",
            "expected_expert": "FRE"
        },
        {
            "description": "mismatch 狀態 → LDE",
            "verification_status": "mismatch",
            "expected_expert": "LDE"
        }
    ],
    
    "risk_assessment": [
        {
            "job": "醫師",
            "income": 200000,
            "expected_risk": "low"
        },
        {
            "job": "工程師",
            "income": 70000,
            "expected_risk": "medium"
        },
        {
            "job": "無業",
            "income": 20000,
            "expected_risk": "high"
        }
    ]
}


# ==========================================
# 🧪 驗證函數
# ==========================================

def validate_profile_structure(profile: Dict) -> List[str]:
    """
    驗證 Profile 結構
    
    Returns:
        錯誤訊息列表 (空列表表示通過)
    """
    errors = []
    required_fields = ["name", "id", "phone", "job", "income", "loan_purpose", "amount"]
    
    for field in required_fields:
        if field not in profile:
            errors.append(f"缺少必要欄位: {field}")
    
    # 類型檢查
    if profile.get("income") is not None:
        if not isinstance(profile["income"], (int, float)):
            errors.append("income 必須是數字")
    
    if profile.get("amount") is not None:
        if not isinstance(profile["amount"], (int, float)):
            errors.append("amount 必須是數字")
    
    return errors


def validate_expert_response(response: Dict, expert_type: str) -> List[str]:
    """
    驗證專家回應結構
    
    Args:
        response: 專家回應
        expert_type: "LDE", "DVE", "FRE"
    
    Returns:
        錯誤訊息列表
    """
    errors = []
    
    required_fields = ["expert", "response", "next_step"]
    for field in required_fields:
        if field not in response:
            errors.append(f"缺少必要欄位: {field}")
    
    # 專家特定檢查
    if expert_type == "DVE":
        if "risk_level" not in response and "dve_raw_report" not in response:
            errors.append("DVE 回應應包含 risk_level 或 dve_raw_report")
    
    if expert_type == "FRE":
        if "financial_metrics" not in response:
            errors.append("FRE 回應應包含 financial_metrics")
    
    return errors
