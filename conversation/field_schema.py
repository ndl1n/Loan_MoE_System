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

    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """驗證台灣手機號碼"""
        # 移除所有非數字字元
        digits = re.sub(r'\D', '', str(phone))
        
        # 處理 +886 開頭
        if digits.startswith('886'):
            digits = '0' + digits[3:]
        
        # 必須是 10 碼且以 09 開頭
        return len(digits) == 10 and digits.startswith('09')

    @staticmethod
    def _validate_tw_id(id_str: str) -> bool:
        """驗證台灣身分證字號"""
        if not id_str or len(id_str) != 10:
            return False
        
        # 第一碼必須是英文字母
        if not id_str[0].isalpha():
            return False
        
        # 後面 9 碼必須是數字
        if not id_str[1:].isdigit():
            return False
        
        # 可以加入更嚴格的檢查碼驗證...
        return True


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

    def get_validation_errors(self, profile_state: dict) -> dict:
        """
        只回傳有錯誤的欄位
        """
        all_results = self.validate_all(profile_state)
        
        errors = {
            field: info["error"]
            for field, info in all_results.items()
            if not info["valid"]
        }
        
        return errors

    def get_field_info(self, field_name: str) -> Optional[Field]:
        """取得特定欄位的定義"""
        return self.fields.get(field_name)