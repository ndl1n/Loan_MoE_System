from .lde import LDE_Expert
from .dve import DVE_Expert
from .fre import FRE_Expert

# 工廠模式：根據名字回傳對應的專家實例
def get_expert_handler(name):
    if name == "LDE": return LDE_Expert()
    if name == "DVE": return DVE_Expert()
    if name == "FRE": return FRE_Expert()
    return None