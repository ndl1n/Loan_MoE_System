import openai
import json
from ..config import OPENAI_API_KEY, OPENAI_MODEL, LDE_ADAPTER_PATH, LDE_SYSTEM_INSTRUCTION
from .base import BaseExpert

client = openai.OpenAI(api_key=OPENAI_API_KEY)

class LDE_Expert(BaseExpert):
    """
    LDE: 貸款徵審專家 (Loan Default Expert)
    Mode A: Local LLM (諮詢)
    Mode B: OpenAI (資料萃取)
    """
    def process(self, task_data, history=[]):
        query = task_data.get("user_query", "")
        profile = task_data.get("profile_state", {})
        
        filled_count = sum(1 for v in profile.values() if v)
        keywords = ["多少", "利率", "什麼", "資格", "可以嗎", "試算", "好過", "推薦"]
        is_question = any(x in query for x in keywords)
        
        # === Mode A: 諮詢模式 ===
        if filled_count <= 2 and is_question:
            print(f"🤖 LDE Mode A (Consult): Local LLM")
            ai_response = self.llm.get_expert_response(
                adapter_path=LDE_ADAPTER_PATH,
                instruction=LDE_SYSTEM_INSTRUCTION, 
                user_input=query,
                max_new_tokens=256
            )
            return {
                "expert": "LDE (Consult)",
                "response": ai_response,
                "updated_profile": None,
                "next_step": "等待申請意願"
            }
            
        # === Mode B: 引導模式 ===
        else:
            print("🤖 LDE Mode B (Guide): OpenAI Extract")
            extraction_result = self._openai_extract(query, profile, history)
            
            updated_profile = extraction_result.get("updated_profile", {})
            current_full_profile = profile.copy()
            if updated_profile:
                current_full_profile.update(updated_profile)
                
            required = ["name", "id", "job", "income", "amount"]
            missing = [k for k in required if not current_full_profile.get(k)]
            
            response_text = extraction_result.get("reply_to_user")
            if not response_text:
                response_text = f"收到。還需要請問您的：{missing[0]}？" if missing else "資料已收集完畢。"
            
            return {
                "expert": "LDE (Guide)",
                "response": response_text,
                "updated_profile": updated_profile,
                "next_step": "等待補件" if missing else "資料完整"
            }

    def _openai_extract(self, query, current_profile, history):
        system_prompt = f"""
        你是一個專業的貸款申請引導機器人。
        1. 當前資料狀態: {json.dumps(current_profile, ensure_ascii=False)}
        2. 目標: 引導填滿 (name, id, job, income, amount)。
        3. 輸出 JSON: {{"updated_profile": {{...}}, "reply_to_user": "..."}}
        """
        messages = [{"role": "system", "content": system_prompt}]
        if history: messages.extend(history[-5:])
        messages.append({"role": "user", "content": query})

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"updated_profile": {}, "reply_to_user": "系統忙碌中，請稍後再試。"}