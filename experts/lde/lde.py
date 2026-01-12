"""
LDE Expert (Loan Desk Expert) - 貸款徵審專家
整合版 - 保留原架構 + Gemini 替代 OpenAI

兩種模式:
- Mode A (Consult): 使用 Fine-tuned Model 進行專業諮詢
- Mode B (Guide): 使用 Gemini API 進行資料補強與引導
"""

import json
import logging
from google import genai

# 從上層導入
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    LDE_ADAPTER_PATH,
    LDE_SYSTEM_INSTRUCTION,
    LDE_PROMPT_TEMPLATE,
    ENABLE_FINETUNED_MODELS
)
from llm_utils import LocalLLMManager
from experts.base import BaseExpert

logger = logging.getLogger(__name__)

# 初始化 Gemini Client (模組層級,只初始化一次)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


class LDE_Expert(BaseExpert):
    """
    LDE: 貸款徵審專家 (Loan Desk Expert)
    Mode A: Local Fine-tuned Model (諮詢)
    Mode B: Gemini API (資料抽取與引導)
    """
    
    def __init__(self):
        """初始化 LDE Expert"""
        # 只在啟用 fine-tuned models 時才初始化 LLM
        if ENABLE_FINETUNED_MODELS:
            super().__init__()  # 繼承 BaseExpert,會初始化 self.llm
            logger.info("✅ LDE Expert 初始化完成 (含 Fine-tuned Model)")
        else:
            logger.info("ℹ️  LDE Expert 初始化 (僅 Gemini 模式)")
            self.llm = None
        
        logger.info("✅ LDE Expert 就緒")
    
    def process(self, task_data, history=[]):
        """
        處理 LDE 任務
        
        Args:
            task_data: {
                "user_query": "使用者問題",
                "profile_state": {...},
                "verification_status": "unknown|pending|verified|mismatch"
            }
            history: 對話歷史
        
        Returns:
            {
                "expert": "LDE (Consult)" or "LDE (Guide)",
                "response": "回覆內容",
                "updated_profile": {...} or None,
                "next_step": "下一步建議"
            }
        """
        
        query = task_data.get("user_query", "")
        profile = task_data.get("profile_state", {})
        verification_status = task_data.get("verification_status", "unknown")
        
        logger.info(f"📍 LDE 處理: query='{query[:50]}...', status={verification_status}")
        
        # === 決定模式 ===
        mode = self._decide_mode(query, profile, verification_status)
        
        logger.info(f"🎯 選擇模式: {mode}")
        
        # === Mode A: 諮詢模式 ===
        if mode == "consult":
            return self._consult_mode(query, profile)
        
        # === Mode B: 引導模式 ===
        else:
            return self._guide_mode(query, profile, history)
    
    def _decide_mode(self, query, profile, verification_status):
        """
        決定使用哪種模式
        
        邏輯:
        1. 資料很少 (≤2 個欄位) + 諮詢問題 → Consult
        2. 資料不完整 (unknown/pending) → Guide
        3. 資料有問題 (mismatch) → Guide
        4. 資料完整 (verified) + 問問題 → Consult
        
        Returns:
            "consult" or "guide"
        """
        
        # 計算已填寫欄位數
        filled_count = sum(1 for v in profile.values() if v is not None)
        
        # 諮詢關鍵字
        consult_keywords = [
            "多少", "利率", "什麼", "資格", "可以嗎",
            "試算", "好過", "推薦", "怎麼", "如何",
            "條件", "審核", "期限", "費用", "划算"
        ]
        
        is_consult_question = any(kw in query for kw in consult_keywords)
        
        # === 決策邏輯 ===
        
        # 情況 1: 資料很少 (≤2) + 諮詢問題 → Consult
        if filled_count <= 2 and is_consult_question:
            logger.debug("決策: 資料少 + 諮詢問題 → Consult")
            return "consult"
        
        # 情況 2: 狀態是 unknown/pending/mismatch → Guide (需要補資料)
        if verification_status in ["unknown", "pending", "mismatch"]:
            logger.debug(f"決策: 狀態={verification_status} → Guide")
            return "guide"
        
        # 情況 3: 資料已驗證 (verified) + 諮詢問題 → Consult
        if verification_status == "verified" and is_consult_question:
            logger.debug("決策: 已驗證 + 諮詢問題 → Consult")
            return "consult"
        
        # 預設: Guide Mode
        logger.debug("決策: 預設 → Guide")
        return "guide"
    
    def _consult_mode(self, query, profile):
        """
        Mode A: 諮詢模式
        使用 Fine-tuned Local Model 回答專業問題
        """
        
        logger.info("🤖 LDE Mode A (Consult): Local Fine-tuned Model")
        
        try:
            # === 構建 Prompt ===
            # 如果有客戶資訊,加入 context
            context = ""
            if profile:
                filled = {k: v for k, v in profile.items() if v is not None}
                if filled:
                    context = f"【客戶資訊】\n{json.dumps(filled, ensure_ascii=False)}\n\n"
            
            # 構建完整輸入
            input_text = f"{context}【客戶問題】\n{query}"
            
            # === 呼叫 Local LLM ===
            ai_response = self.llm.get_expert_response(
                adapter_path=LDE_ADAPTER_PATH,
                instruction=LDE_SYSTEM_INSTRUCTION,
                user_input=input_text,
                max_new_tokens=256,
                temperature=0.3,
                top_p=0.9,
                template=LDE_PROMPT_TEMPLATE
            )
            
            logger.info(f"✅ Local Model 回覆: {ai_response[:100]}...")
            
            return {
                "expert": "LDE (Consult)",
                "mode": "consult",
                "response": ai_response,
                "updated_profile": None,
                "next_step": "等待客戶後續意願"
            }
            
        except Exception as e:
            logger.error(f"❌ Consult Mode 失敗: {e}", exc_info=True)
            
            # Fallback: 使用 Gemini
            logger.warning("⚠️  降級使用 Gemini 進行諮詢")
            return self._consult_with_gemini(query, profile)
    
    def _consult_with_gemini(self, query, profile):
        """
        使用 Gemini 進行諮詢 (Fallback)
        """
        
        logger.info("🤖 使用 Gemini 進行諮詢 (Fallback)")
        
        # 構建 context
        context = ""
        if profile:
            filled = {k: v for k, v in profile.items() if v is not None}
            if filled:
                context = f"\n【客戶已提供資訊】\n{json.dumps(filled, ensure_ascii=False)}"
        
        # 使用訓練時的指令
        prompt = f"""{LDE_SYSTEM_INSTRUCTION}
{context}

【客戶問題】
{query}

請用專業、中立的語氣回答客戶的問題。"""
        
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt
            )
            
            ai_response = response.text.strip()
            
            logger.info(f"✅ Gemini 回覆: {ai_response[:100]}...")
            
            return {
                "expert": "LDE (Consult via Gemini)",
                "mode": "consult",
                "response": ai_response,
                "updated_profile": None,
                "next_step": "等待客戶後續意願"
            }
            
        except Exception as e:
            logger.error(f"❌ Gemini 諮詢失敗: {e}", exc_info=True)
            
            return {
                "expert": "LDE (Consult)",
                "mode": "consult",
                "response": "抱歉,系統目前繁忙,請稍後再試。",
                "updated_profile": None,
                "next_step": "系統錯誤"
            }
    
    def _guide_mode(self, query, profile, history):
        """
        Mode B: 引導模式
        使用 Gemini 進行資料抽取與引導
        """
        
        logger.info("🤖 LDE Mode B (Guide): Gemini Extract & Guide")
        
        # === 呼叫 Gemini 進行抽取 ===
        extraction_result = self._gemini_extract(query, profile, history)
        
        # === 更新 Profile ===
        updated_profile = extraction_result.get("updated_profile", {})
        current_full_profile = profile.copy()
        
        if updated_profile:
            current_full_profile.update(updated_profile)
            logger.info(f"📝 抽取到: {updated_profile}")
        
        # === 檢查缺少的欄位 ===
        # 注意: 這裡要用 MoE 訓練時的欄位名 (purpose 而非 loan_purpose)
        required = ["name", "id", "job", "income", "purpose", "amount"]
        missing = [k for k in required if not current_full_profile.get(k)]
        
        # === 生成回覆 ===
        response_text = extraction_result.get("reply_to_user")
        
        if not response_text:
            # 如果 Gemini 沒有生成回覆,使用預設邏輯
            if missing:
                # 映射回對話時的欄位名
                field_name_map = {
                    "name": "姓名",
                    "id": "身分證字號",
                    "job": "職業",
                    "income": "月收入",
                    "purpose": "貸款用途",
                    "amount": "貸款金額"
                }
                next_field = field_name_map.get(missing[0], missing[0])
                response_text = f"收到。還需要請問您的{next_field}是?"
            else:
                response_text = "感謝您提供完整資訊!我們將為您進行審核。"
        
        # === 決定下一步 ===
        next_step = "等待補件" if missing else "資料完整,待驗證"
        
        return {
            "expert": "LDE (Guide)",
            "mode": "guide",
            "response": response_text,
            "updated_profile": updated_profile if updated_profile else None,
            "next_step": next_step
        }
    
    def _gemini_extract(self, query, current_profile, history):
        """
        使用 Gemini API 進行資料抽取
        替代原本的 OpenAI
        
        Args:
            query: 使用者當前輸入
            current_profile: 目前的 profile 狀態
            history: 對話歷史
        
        Returns:
            {
                "updated_profile": {...},
                "reply_to_user": "..."
            }
        """
        
        # === 構建對話歷史 ===
        history_text = ""
        if history:
            for msg in history[-5:]:  # 只取最近 5 輪
                role = msg.get("role", "user")
                content = msg.get("content", "")
                role_name = "User" if role == "user" else "Assistant"
                history_text += f"{role_name}: {content}\n"
        
        # === 構建 Prompt ===
        system_prompt = f"""你是一個專業的貸款申請引導機器人。

【對話歷史】
{history_text if history_text else "(無歷史)"}

【當前資料狀態】
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

【當前使用者輸入】
User: {query}

【任務】
1. 從使用者輸入中抽取任何可用的欄位資訊
2. 生成友善、專業的回覆,引導使用者提供缺少的資訊

目標欄位: name (姓名), id (身分證), job (職業), income (月收入), purpose (貸款用途), amount (貸款金額)

注意事項:
- 金額請自動轉換 (例如 "5萬" → 50000)
- 電話號碼去除空格和破折號
- 回覆要簡潔、專業,不要使用表情符號

【輸出格式】
請輸出純 JSON,格式:
{{
  "updated_profile": {{
    "欄位名": "抽取到的值"
  }},
  "reply_to_user": "友善的回覆文字"
}}

範例 1:
輸入: "我叫王小明,月薪大概5萬"
輸出: {{"updated_profile": {{"name": "王小明", "income": 50000}}, "reply_to_user": "王小明先生您好,已記錄您的月收入為5萬元。請問您的身分證字號是?"}}

範例 2:
輸入: "想借60萬買車"
輸出: {{"updated_profile": {{"amount": 600000, "purpose": "購車"}}, "reply_to_user": "了解,貸款金額60萬元用於購車已記錄。請問您的職業是?"}}

現在請開始處理:"""
        
        try:
            # === 呼叫 Gemini ===
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=system_prompt
            )
            
            raw_output = response.text.strip()
            logger.debug(f"Gemini 原始輸出: {raw_output}")
            
            # === 解析 JSON ===
            import re
            
            # 清理 markdown code block
            clean_output = re.sub(r'```json\s*', '', raw_output)
            clean_output = re.sub(r'```\s*', '', clean_output)
            
            result = json.loads(clean_output)
            
            logger.info(f"✅ Gemini 抽取成功")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失敗: {e}\n原始輸出: {raw_output}")
            
            # Fallback
            return {
                "updated_profile": {},
                "reply_to_user": "收到您的訊息。請問您的姓名是?"
            }
        
        except Exception as e:
            logger.error(f"❌ Gemini 抽取失敗: {e}", exc_info=True)
            
            # Fallback
            return {
                "updated_profile": {},
                "reply_to_user": "系統忙碌中,請稍後再試。"
            }