import logging
from typing import Dict, Any

from .utils import normalize_tw_phone

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    對話管理器
    負責處理資料收集階段的對話流程
    """
    
    def __init__(self, session_mgr, field_schema, gemini_client):
        self.session_mgr = session_mgr
        self.schema = field_schema
        self.gemini = gemini_client

    def handle_turn(self, user_id: str, user_input: str) -> Dict[str, Any]:
        """
        處理單輪對話
        
        Returns:
            {
                "status": "COLLECTING" | "READY_FOR_MOE",
                "response": "回覆內容",
                "profile": {...},
                "missing_fields": [...] | None,
                "summary": {...} | None
            }
        """
        
        # === 1️⃣ 載入當前狀態 ===
        state = self.session_mgr.get_profile()
        
        # === 2️⃣ 先讀取歷史 ===
        history = self.session_mgr.get_history(limit=10)
        
        # === 3️⃣ 找出缺少的欄位 ===
        missing_before = self.schema.get_missing_fields(state)
        
        logger.info(f"[User: {user_id}] Missing fields: {missing_before}")
        
        # === 4️⃣ 用 Gemini 抽取欄位 ===
        extracted = self.gemini.extract_slots(
            user_input, 
            missing_before, 
            history
        )
        
        logger.info(f"[Gemini Extracted]: {extracted}")
        
        # === 4.5️⃣ 現在才把使用者輸入存入歷史 ===
        self.session_mgr.add_message("user", user_input)
        
        # === 5️⃣ 特殊欄位處理與驗證 ===
        validated_data = {}
        
        for field_name, value in extracted.items():
            if field_name not in self.schema.fields:
                continue
                
            field_def = self.schema.fields[field_name]
            
            # 電話號碼特殊處理
            if field_name == "phone":
                normalized = normalize_tw_phone(value)
                if normalized:
                    validated_data[field_name] = normalized
                else:
                    logger.warning(f"Invalid phone format: {value}")
                    state["last_asked_field"] = field_name
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    continue
            
            # 數字類型驗證
            elif field_def.type == int:
                try:
                    validated_data[field_name] = int(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid integer for {field_name}: {value}")
                    continue
            
            # 其他欄位直接接受
            else:
                validated_data[field_name] = value
        
        # === 6️⃣ 更新 Profile ===
        if validated_data:
            state = self.session_mgr.update_profile(validated_data)
            logger.info(f"[Profile Updated]: {validated_data}")
        
        # === 7️⃣ 再次檢查缺少的欄位 ===
        missing_after = self.schema.get_missing_fields(state)
        
        # === 8️⃣ 還有欄位缺失 → 繼續詢問 ===
        if missing_after:
            next_field = missing_after[0]
            
            # 防止鬼打牆邏輯
            last_asked = state.get("last_asked_field")
            retry_count = state.get("retry_count", 0)
            
            variant = "standard"
            
            if last_asked == next_field:
                retry_count += 1
                if retry_count >= 2:
                    variant = "retry"
                    logger.warning(f"Retry count reached {retry_count} for field: {next_field}")
            else:
                retry_count = 0
            
            question = self.gemini.ask_question(next_field, variant=variant)
            
            self.session_mgr.update_profile({
                "last_asked_field": next_field,
                "retry_count": retry_count
            })
            
            self.session_mgr.add_message("assistant", question)
            
            return {
                "status": "COLLECTING",
                "response": question,
                "profile": state,
                "missing_fields": missing_after
            }
        
        # === 9️⃣ 全部收集完成 → 準備進入 MoE ===
        summary = {
            k: v for k, v in state.items()
            if v is not None and k not in ["last_asked_field", "retry_count", "created_at", "updated_at"]
        }
        
        # 更新狀態為 pending
        self.session_mgr.update_profile({"verification_status": "pending"})
        
        completion_msg = "感謝您提供完整資訊！我們將為您進行評估。"
        self.session_mgr.add_message("assistant", completion_msg)
        
        logger.info(f"✅ [Collection Complete] User: {user_id}")
        
        return {
            "status": "READY_FOR_MOE",
            "response": completion_msg,
            "profile": state,
            "summary": summary
        }