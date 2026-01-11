import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def normalize_tw_phone(raw: str) -> Optional[str]:
    """
    正規化台灣手機號碼
    
    接受格式:
    - 0912345678
    - 0912-345-678
    - 0912 345 678
    - +886912345678
    - +886-912-345-678
    
    回傳: 0912-345-678 或 None
    
    改進:
    - 更詳細的驗證
    - 加入 logging
    """
    if not raw:
        return None

    # 移除所有非數字字元
    digits = re.sub(r"\D", "", str(raw))

    # 處理國際格式 +886
    if digits.startswith("886"):
        digits = "0" + digits[3:]

    # 驗證長度和開頭
    if len(digits) != 10:
        logger.warning(f"Invalid phone length: {raw} (digits: {digits})")
        return None
    
    if not digits.startswith("09"):
        logger.warning(f"Invalid phone prefix: {raw} (must start with 09)")
        return None

    # 格式化為 0912-345-678
    formatted = f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
    
    logger.debug(f"Phone normalized: {raw} → {formatted}")
    
    return formatted

        return None

    return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
