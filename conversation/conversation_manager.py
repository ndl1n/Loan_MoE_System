from conversation.utils import normalize_tw_phone

class ConversationManager:
    def __init__(self, session_mgr, field_schema, gemini_client):
        self.session_mgr = session_mgr  # 改名 session_mgr 比較語意化
        self.schema = field_schema
        self.gemini = gemini_client

    def handle_turn(self, user_id, user_input):
        # 0️⃣ 讀取目前狀態 & 歷史
        # [Fix] load -> get_profile
        state = self.session_mgr.get_profile()
        history = self.session_mgr.get_history(limit=5) # 讀取最近對話

        # 初始化必要欄位
        state.setdefault("last_asked_field", None)

        # 1️⃣ 找出目前缺的欄位
        missing_before = self.schema.get_missing_fields(state)

        # 2️⃣ 用 Gemini 抽取欄位
        # [Fix] 加入 history，讓模型知道上下文
        extracted = self.gemini.extract_slots(user_input, missing_before, history)

        # 3️⃣ 特殊欄位處理（phone）
        if "phone" in extracted:
            normalized = normalize_tw_phone(extracted["phone"])
            if normalized:
                extracted["phone"] = normalized
            else:
                extracted.pop("phone") # 無效電話丟掉

        # 4️⃣ 若有抽到任何東西 → 更新 profile
        if extracted:
            # [Fix] update -> update_profile
            state = self.session_mgr.update_profile(extracted)
            
            # 也要記得把使用者的話存入歷史，這樣下次才接得上
            self.session_mgr.add_message("user", user_input)

        # 5️⃣ 再次檢查缺欄位
        missing_after = self.schema.get_missing_fields(state)

        # 6️⃣ 還沒收集完 → 問下一題
        if missing_after:
            next_field = missing_after[0]
            
            # 🛡️ 避免鬼打牆邏輯
            variant = "standard"
            if state.get("last_asked_field") == next_field:
                variant = "retry" # 如果上一題問過一樣的，這次要換個語氣追問

            question = self.gemini.ask_question(
                next_field,
                variant=variant
            )

            # 更新狀態
            self.session_mgr.update_profile({"last_asked_field": next_field})
            # 機器人的問題也要存入歷史
            self.session_mgr.add_message("assistant", question)

            return {
                "status": "COLLECTING",
                "response": question,
                "profile": state
            }

        # 7️⃣ 全部收集完成 → 準備進 MoE
        summary = {
            k: v for k, v in state.items()
            if v is not None and k != "last_asked_field"
        }

        return {
            "status": "READY_FOR_MOE",
            "profile": state,
            "summary": summary
        }