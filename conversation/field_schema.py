import re
from typing import Any, Callable, Optional, Dict, List, Tuple


class Field:
    """
    欄位定義類別
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
        self.priority = priority

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        驗證欄位值
        回傳: (是否有效, 錯誤訊息)
        """
        if value is None:
            if self.required:
                return False, f"{self.name} 為必填欄位"
            return True, None

        # 類型檢查
        try:
            if self.type == int:
                value = int(value)
            elif self.type == float:
                value = float(value)
            elif self.type == str:
                value = str(value)
        except (ValueError, TypeError):
            return False, f"{self.name} 必須是 {self.type.__name__} 類型"

        # 自定義驗證
        if self.validator:
            if callable(self.validator):
                is_valid = self.validator(value)
                if not is_valid:
                    return False, self.error_msg
            elif self.validator == "phone":
                if not self._validate_phone(value):
                    return False, "手機號碼格式不正確"
            elif self.validator == "id":
                if not self._validate_tw_id(value):
                    return False, "身分證字號格式不正確"

        return True, None

    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """驗證台灣手機號碼"""
        digits = re.sub(r'\D', '', str(phone))
        
        if digits.startswith('886'):
            digits = '0' + digits[3:]
        
        return len(digits) == 10 and digits.startswith('09')

    @staticmethod
    def _validate_tw_id(id_str: str) -> bool:
        """驗證台灣身分證字號"""
        if not id_str or len(id_str) != 10:
            return False
        
        if not id_str[0].isalpha():
            return False
        
        if not id_str[1:].isdigit():
            return False
        
        return True


class FieldSchema:
    """
    欄位 Schema 管理
    """

    def __init__(self):
        self.fields = {
            "name": Field(
                "name",
                priority=1,
                error_msg="請提供您的完整姓名"
            ),
            "id": Field(
                "id",
                priority=2,
                validator="id",
                error_msg="身分證字號格式應為 1 個英文字母 + 9 個數字"
            ),
            "phone": Field(
                "phone",
                priority=3,
                validator="phone",
                error_msg="手機號碼格式應為 09 開頭的 10 碼數字"
            ),
            "job": Field(
                "job",
                priority=4,
                error_msg="請提供您的職業或職稱"
            ),
            "income": Field(
                "income",
                ftype=int,
                priority=5,
                validator=lambda x: x > 0,
                error_msg="月收入必須大於 0"
            ),
            "loan_purpose": Field(
                "loan_purpose",
                priority=6,
                error_msg="請說明貸款用途"
            ),
            "amount": Field(
                "amount",
                ftype=int,
                priority=7,
                validator=lambda x: x > 0,
                error_msg="貸款金額必須大於 0"
            )
        }

    def get_missing_fields(self, profile_state: Dict) -> List[str]:
        """
        取得缺少的必填欄位，並按優先級排序
        """
        missing = []
        
        for k, field in self.fields.items():
            value = profile_state.get(k)
            
            if field.required:
                if value is None or value == "":
                    missing.append(k)
        
        missing.sort(key=lambda x: self.fields[x].priority)
        
        return missing

    def all_required_filled(self, profile_state: Dict) -> bool:
        """檢查是否所有必填欄位都已填寫"""
        return len(self.get_missing_fields(profile_state)) == 0

    def validate_all(self, profile_state: Dict) -> Dict:
        """驗證所有欄位"""
        results = {}
        
        for field_name, field_def in self.fields.items():
            value = profile_state.get(field_name)
            is_valid, error_msg = field_def.validate(value)
            results[field_name] = {
                "valid": is_valid,
                "error": error_msg
            }
        
        return results

    def get_validation_errors(self, profile_state: Dict) -> Dict:
        """只回傳有錯誤的欄位"""
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
