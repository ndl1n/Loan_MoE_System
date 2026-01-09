import re

def normalize_tw_phone(raw: str):
    """
    接受：
    - 0912345678
    - 0912-345-678
    - 0912 345 678
    - +886912345678
    回傳：
    - 09xx-xxx-xxx 或 None
    """
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)

    if digits.startswith("886"):
        digits = "0" + digits[3:]

    if len(digits) != 10 or not digits.startswith("09"):
        return None

    return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
