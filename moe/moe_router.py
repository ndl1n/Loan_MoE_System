import logging
from typing import Dict, Tuple, List

logger = logging.getLogger(__name__)


class ProfileAdapter:
    """
    欄位適配器 - 處理對話收集欄位 vs MoE 訓練欄位的映射
    
    關鍵映射:
    - loan_purpose (對話) → purpose (MoE)
    """
    
    # 對話欄位 → MoE 訓練欄位的映射
    FIELD_MAPPING = {
        "name": "name",
        "id": "id",
        "phone": "phone",
        "job": "job",
        "income": "income",
        "loan_purpose": "purpose",  # ⚠️ 關鍵映射
        "purpose": "purpose",       # 兼容直接使用 purpose
        "amount": "amount",
        "company": "company",
        "verification_status": "verification_status"  # 新增: 狀態也需要傳遞
    }
    
    # MoE 必須的欄位 (根據訓練資料)
    REQUIRED_FIELDS = ["name", "job", "income", "purpose"]
    
    @staticmethod
    def adapt(conversation_profile: Dict) -> Dict:
        """
        將對話收集的 profile 轉換為 MoE 訓練時的格式
        
        Example:
            Input:  {"name": "王小明", "loan_purpose": "購車", ...}
            Output: {"name": "王小明", "purpose": "購車", ...}
        """
        adapted = {}
        
        for conv_field, moe_field in ProfileAdapter.FIELD_MAPPING.items():
            value = conversation_profile.get(conv_field)
            
            # 保留所有非 None 的值
            if value is not None:
                adapted[moe_field] = value
        
        logger.debug(f"欄位適配: {conversation_profile} → {adapted}")
        
        return adapted
    
    @staticmethod
    def validate_for_moe(profile: Dict) -> Tuple[bool, List[str]]:
        """
        驗證 profile 是否符合 MoE 最低要求
        
        根據訓練資料，至少需要: name, job, income, purpose
        (id 可以是 null)
        """
        missing = []
        
        for field in ProfileAdapter.REQUIRED_FIELDS:
            if not profile.get(field):
                missing.append(field)
        
        is_valid = len(missing) == 0
        
        if not is_valid:
            logger.warning(f"Profile 驗證失敗，缺少: {missing}")
        
        return is_valid, missing


class VerificationStatusManager:
    """
    驗證狀態管理器
    負責推斷和更新 verification_status
    
    狀態定義:
    - unknown: 資料未收集完成
    - pending: 資料收集完成，等待 DVE 驗證
    - verified: DVE 驗證通過
    - mismatch: DVE 發現欄位不符
    """
    
    VALID_STATUSES = ["unknown", "pending", "verified", "mismatch"]
    
    @staticmethod
    def infer_status(profile: Dict, is_collection_complete: bool) -> str:
        """
        根據當前狀態推斷 verification_status
        
        邏輯:
        1. 如果 profile 中已有明確狀態，直接使用
        2. 資料未收集完成 → unknown
        3. 資料收集完成，未經 DVE → pending
        """
        
        # 優先使用明確的狀態
        explicit_status = profile.get("verification_status")
        
        if explicit_status in VerificationStatusManager.VALID_STATUSES:
            return explicit_status
        
        # 推斷狀態
        if not is_collection_complete:
            return "unknown"
        else:
            return "pending"
    
    @staticmethod
    def update_status(session_mgr, new_status: str) -> bool:
        """
        更新 verification_status 到 Redis
        
        由 DVE 呼叫，更新為 verified 或 mismatch
        
        Returns:
            是否更新成功
        """
        if new_status not in VerificationStatusManager.VALID_STATUSES:
            logger.error(f"無效的狀態: {new_status}")
            return False
        
        try:
            session_mgr.update_profile({"verification_status": new_status})
            logger.info(f"✅ 更新 verification_status → {new_status}")
            return True
        except Exception as e:
            logger.error(f"❌ 更新狀態失敗: {e}")
            return False


class MoERouter:
    """
    MoE 路由器 (修正版)
    """
    
    def __init__(self):
        # 延遲載入 GateKeeper (避免循環引用)
        self.gatekeeper = None
        logger.info("✅ MoE Router 初始化完成")
    
    def _lazy_load_gatekeeper(self):
        """延遲載入 GateKeeper"""
        if self.gatekeeper is None:
            from moe.gating_engine import MoEGateKeeper
            self.gatekeeper = MoEGateKeeper()
    
    def route(
        self,
        profile: Dict,
        user_query: str,
        is_collection_complete: bool = True
    ) -> Tuple[str, float, str, Dict]:
        """
        路由到對應的專家
        
        Args:
            profile: 對話收集的完整 profile
            user_query: 使用者當前的問題/訊息
            is_collection_complete: 是否已完成資料收集
        
        Returns:
            (expert, confidence, reason, routing_info)
        """
        
        self._lazy_load_gatekeeper()
        
        # === 1. 適配欄位 ===
        adapted_profile = ProfileAdapter.adapt(profile)
        
        # === 2. 驗證欄位完整性 ===
        is_valid, missing = ProfileAdapter.validate_for_moe(adapted_profile)
        
        if not is_valid:
            logger.warning(f"⚠️ Profile 不完整，缺少: {missing}")
            return "LDE", 1.0, f"Missing fields: {missing}", {
                "missing_fields": missing,
                "verification_status": "unknown"
            }
        
        # === 3. 推斷 verification_status ===
        verification_status = VerificationStatusManager.infer_status(
            profile, 
            is_collection_complete
        )
        
        logger.info(f"📍 驗證狀態: {verification_status}")
        
        # === 4. 準備 MoE 輸入 ===
        moe_input = {
            "profile_state": adapted_profile,
            "verification_status": verification_status,
            "user_query": user_query if user_query else "使用者已完成資料填寫"
        }
        
        logger.info(f"🎯 MoE 輸入: {moe_input}")
        
        # === 5. 呼叫 MoE 進行路由 ===
        try:
            expert, confidence, reason = self.gatekeeper.predict(moe_input)
            
            routing_info = {
                "expert": expert,
                "confidence": confidence,
                "reason": reason,
                "verification_status": verification_status,
                "profile_completeness": self._calculate_completeness(adapted_profile),
                "risk_score": self.gatekeeper.calculate_risk_score(adapted_profile)
            }
            
            logger.info(
                f"✅ 路由結果: {expert} "
                f"(信心度: {confidence:.2f}, 原因: {reason})"
            )
            
            return expert, confidence, reason, routing_info
            
        except Exception as e:
            logger.error(f"❌ MoE 路由失敗: {e}", exc_info=True)
            return "LDE", 0.5, f"Error: {str(e)}", {"error": str(e)}
    
    def _calculate_completeness(self, profile: Dict) -> float:
        """
        計算資料完整度
        """
        training_fields = ["name", "id", "job", "income", "purpose", "amount"]
        
        filled_count = sum(
            1 for field in training_fields
            if profile.get(field) is not None
        )
        
        return filled_count / len(training_fields)