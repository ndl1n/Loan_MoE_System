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


def parse_tw_amount(amount_str: str) -> Optional[int]:
    """
    解析台灣常見的金額表達方式
    
    支援:
    - "5萬" → 50000
    - "50萬" → 500000
    - "100k" → 100000
    - "1.5M" → 1500000
    - "3,000,000" → 3000000
    
    改進:
    - 更完整的格式支援
    - 錯誤處理
    """
    if not amount_str:
        return None
    
    # 如果已經是數字,直接回傳
    if isinstance(amount_str, (int, float)):
        return int(amount_str)
    
    amount_str = str(amount_str).strip()
    
    # 移除空格和逗號
    amount_str = amount_str.replace(',', '').replace(' ', '')
    
    # 處理「萬」
    if '萬' in amount_str:
        try:
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 10000)
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse amount with 萬: {amount_str}")
            return None
    
    # 處理 k/K (千)
    if amount_str.lower().endswith('k'):
        try:
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 1000)
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse amount with k: {amount_str}")
            return None
    
    # 處理 m/M (百萬)
    if amount_str.lower().endswith('m'):
        try:
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 1000000)
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse amount with m: {amount_str}")
            return None
    
    # 處理「億」(台灣也常用)
    if '億' in amount_str:
        try:
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 100000000)
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse amount with 億: {amount_str}")
            return None
    
    # 純數字
    try:
        return int(float(amount_str))
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse amount as number: {amount_str}")
        return None

