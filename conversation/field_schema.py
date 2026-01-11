import re
from typing import Any, Callable, Optional

class Field:
    """
    欄位定義類別
    
    改進:
    - 加入 validator 函數支援
    - 加入錯誤訊息
    - 加入優先級設定
    """
    def __init__(
        self,
        name: str,
        required: bool = True,
        ftype: type = str,
        validator: Optional[Callable] = None,
        error_msg: str = None,
        priority: int = 0
    ):
        self.name = name
        self.required = required
        self.type = ftype
        self.validator = validator
        self.error_msg = error_msg or f"{name} 格式不正確"
        self.priority = priority  # 數字越小越優先

class FieldSchema:

    def __init__(self):
        self.fields = {
            "name": Field("name"),
            "id": Field("id"),
            "phone": Field("phone", validator="phone"),
            "loan_purpose": Field("loan_purpose"),
            "job": Field("job"),
            "income": Field("income", ftype=int),
            "amount": Field("amount", ftype=int)
        }

    def get_missing_fields(self, profile_state):
        missing = []
        for k, field in self.fields.items():
            if field.required and not profile_state.get(k):
                missing.append(k)
        return missing

    def all_required_filled(self, profile_state):
        return len(self.get_missing_fields(profile_state)) == 0
