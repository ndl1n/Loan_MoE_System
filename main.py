"""
Loan MoE System - 主入口檔案
貸款審核 Mixture of Experts 系統

流程:
1. 對話階段 (Conversation) - 使用 Gemini + Redis 收集資料
2. MoE 路由 - 根據資料狀態分流
3. 專家處理 - LDE/DVE/FRE 各司其職
"""

import logging
from typing import Dict, Any, Optional

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoanMoESystem:
    """
    貸款 MoE 系統主類別
    
    整合:
    - ConversationManager (對話收集)
    - MoERouter (路由分流)
    - LDE/DVE/FRE Experts (專家處理)
    """
    
    def __init__(self):
        """初始化系統"""
        logger.info("🚀 初始化 Loan MoE System...")
        
        # 延遲載入各模組
        self._conversation_managers = {}  # user_id -> ConversationManager
        self._moe_router = None
        self._experts = {}
        
        logger.info("✅ Loan MoE System 初始化完成")
    
    def _get_conversation_manager(self, user_id: str):
        """取得或建立對話管理器"""
        if user_id not in self._conversation_managers:
            from conversation import (
                ConversationManager, 
                UserSessionManager, 
                FieldSchema, 
                GeminiClient
            )
            
            session_mgr = UserSessionManager(user_id)
            field_schema = FieldSchema()
            gemini_client = GeminiClient()
            
            self._conversation_managers[user_id] = ConversationManager(
                session_mgr, field_schema, gemini_client
            )
        
        return self._conversation_managers[user_id]
    
    def _get_moe_router(self):
        """取得 MoE 路由器"""
        if self._moe_router is None:
            from moe import MoERouter
            self._moe_router = MoERouter()
        return self._moe_router
    
    def _get_expert(self, expert_name: str):
        """取得專家實例"""
        if expert_name not in self._experts:
            if expert_name == "LDE":
                from experts import LDEExpert
                self._experts["LDE"] = LDEExpert()
            elif expert_name == "DVE":
                from experts import DVEExpert
                self._experts["DVE"] = DVEExpert()
            elif expert_name == "FRE":
                from experts import FREExpert
                self._experts["FRE"] = FREExpert()
            else:
                raise ValueError(f"未知的專家: {expert_name}")
        
        return self._experts[expert_name]
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        處理使用者訊息 - 主要入口
        
        Args:
            user_id: 使用者 ID
            message: 使用者訊息
        
        Returns:
            {
                "stage": "CONVERSATION" | "MOE_ROUTING" | "EXPERT_PROCESSING",
                "expert": "LDE" | "DVE" | "FRE" | None,
                "response": "回覆內容",
                "profile": {...},
                "routing_info": {...} | None,
                "next_step": "下一步"
            }
        """
        
        logger.info(f"📨 收到訊息 [User: {user_id}]: {message[:50]}...")
        
        # === 階段 1: 對話收集 ===
        conv_mgr = self._get_conversation_manager(user_id)
        conv_result = conv_mgr.handle_turn(user_id, message)
        
        # 如果還在收集階段
        if conv_result["status"] == "COLLECTING":
            logger.info(f"📝 [對話階段] 繼續收集資料")
            return {
                "stage": "CONVERSATION",
                "expert": None,
                "response": conv_result["response"],
                "profile": conv_result["profile"],
                "missing_fields": conv_result.get("missing_fields", []),
                "routing_info": None,
                "next_step": "CONTINUE_COLLECTING"
            }
        
        # === 階段 2: MoE 路由 ===
        logger.info(f"🎯 [MoE 路由] 資料收集完成，開始路由...")
        
        profile = conv_result["profile"]
        
        router = self._get_moe_router()
        expert_name, confidence, reason, routing_info = router.route(
            profile=profile,
            user_query=message,
            is_collection_complete=True
        )
        
        logger.info(f"🎯 路由結果: {expert_name} (信心度: {confidence:.2f})")
        
        # === 階段 3: 專家處理 ===
        logger.info(f"🤖 [{expert_name}] 開始處理...")
        
        expert = self._get_expert(expert_name)
        
        # 準備 task_data
        task_data = {
            "user_query": message,
            "profile_state": profile,
            "verification_status": routing_info.get("verification_status", "pending")
        }
        
        # 如果是 FRE，需要 DVE 結果
        if expert_name == "FRE":
            task_data["dve_result"] = routing_info
        
        # 取得對話歷史
        session_mgr = conv_mgr.session_mgr
        history = session_mgr.get_history(limit=10)
        
        # 呼叫專家
        expert_result = expert.process(task_data, history)
        
        logger.info(f"✅ [{expert_name}] 處理完成: {expert_result.get('next_step')}")
        
        # === 處理後續流程 ===
        next_step = expert_result.get("next_step", "")
        
        # 如果 DVE 建議轉 FRE
        if next_step == "TRANSFER_TO_FRE" and expert_name == "DVE":
            logger.info("🔄 DVE → FRE 轉接...")
            
            fre_expert = self._get_expert("FRE")
            fre_task_data = {
                "user_query": message,
                "profile_state": profile,
                "verification_status": "verified",
                "dve_result": expert_result
            }
            
            fre_result = fre_expert.process(fre_task_data, history)
            
            return {
                "stage": "EXPERT_PROCESSING",
                "expert": "FRE",
                "response": fre_result["response"],
                "profile": profile,
                "routing_info": routing_info,
                "expert_result": fre_result,
                "next_step": fre_result.get("next_step")
            }
        
        # 如果需要回到 LDE 釐清
        if next_step == "FORCE_LDE_CLARIFY":
            # 更新狀態為 mismatch
            session_mgr.update_profile({"verification_status": "mismatch"})
        
        return {
            "stage": "EXPERT_PROCESSING",
            "expert": expert_name,
            "response": expert_result["response"],
            "profile": profile,
            "routing_info": routing_info,
            "expert_result": expert_result,
            "next_step": next_step
        }
    
    def reset_user_session(self, user_id: str):
        """重置使用者 session"""
        if user_id in self._conversation_managers:
            conv_mgr = self._conversation_managers[user_id]
            conv_mgr.session_mgr.clear_session()
            del self._conversation_managers[user_id]
            logger.info(f"🗑️ 已重置 User: {user_id} 的 session")


def main():
    """測試用主函數"""
    print("=" * 60)
    print("🏦 Loan MoE System - Interactive Demo")
    print("=" * 60)
    print("輸入 'quit' 退出, 'reset' 重置對話")
    print("-" * 60)
    
    system = LoanMoESystem()
    user_id = "demo_user_001"
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("👋 感謝使用，再見！")
                break
            
            if user_input.lower() == 'reset':
                system.reset_user_session(user_id)
                print("🔄 對話已重置")
                continue
            
            # 處理訊息
            result = system.process_message(user_id, user_input)
            
            # 顯示結果
            print(f"\n🤖 系統 [{result.get('expert', '對話')}]: {result['response']}")
            
            if result.get('next_step') in ['CASE_CLOSED_SUCCESS', 'CASE_CLOSED_REJECT', 'HUMAN_HANDOVER']:
                print(f"\n📋 案件狀態: {result['next_step']}")
                print("輸入 'reset' 開始新的申請")
        
        except KeyboardInterrupt:
            print("\n\n👋 感謝使用，再見！")
            break
        except Exception as e:
            logger.error(f"❌ 處理失敗: {e}", exc_info=True)
            print(f"\n❌ 系統錯誤: {str(e)}")


if __name__ == "__main__":
    main()
