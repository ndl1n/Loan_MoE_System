"""
Gemini Client
使用 Gemini API 進行欄位抽取和問題生成
"""

import json
import logging
import re
from google import genai

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API 客戶端"""
    
    def __init__(self):
        self.model = client.models
        self.logger = logger

    def ask_question(self, field_name: str, variant: str = "standard") -> str:
        """
        根據欄位產生問句，支援不同語氣變體
        """
        prompts = {
            "name": {
                "standard": "請問您的姓名是?",
                "retry": "不好意思，我需要確認您的完整姓名，請問該怎麼稱呼您?"
            },
            "id": {
                "standard": "請問您的身分證字號是?",
                "retry": "身分證字號格式似乎不太對，請您再確認一下(例如 A123456789):"
            },
            "phone": {
                "standard": "請問您的手機號碼是?",
                "retry": "手機號碼需要是 09 開頭的 10 碼數字，請您再提供一次:"
            },
            "loan_purpose": {
                "standard": "請問您本次貸款的主要用途是?(例如:投資、購車、周轉)",
                "retry": "了解。能請您再具體說明一下資金用途嗎?這有助於審核:"
            },
            "job": {
                "standard": "請問您目前的職業是?",
                "retry": "請問您的具體職稱或工作內容是?"
            },
            "income": {
                "standard": "請問您每月大約收入是多少?(請以新台幣計算)",
                "retry": "不好意思，我們需要一個具體的數字來評估額度，請問月薪大約是多少元?"
            },
            "amount": {
                "standard": "請問您希望申請的貸款金額是多少?(請以新台幣計算)",
                "retry": "請問您具體想貸多少金額呢?(例如:50萬元)"
            }
        }

        field_prompts = prompts.get(field_name, {})
        return field_prompts.get(variant, field_prompts.get("standard", f"請提供 {field_name}"))

    def extract_slots(self, user_input: str, missing_fields: list, history: list = None) -> dict:
        """
        從對話中抽取欄位，需考慮 history 上下文
        """
        if history is None:
            history = []
            
        if not missing_fields:
            return {}

        # === 構建對話歷史文字 ===
        history_text = ""
        last_question = None
        
        for msg in history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"
            
            if msg["role"] == "assistant" and "?" in msg["content"]:
                last_question = msg["content"]

        # === 構建欄位說明 ===
        field_descriptions = {
            "name": "使用者的姓名",
            "id": "身分證字號 (格式: A123456789)",
            "phone": "手機號碼 (10位數字,09開頭)",
            "loan_purpose": "貸款用途 (如: 投資、購車、周轉)",
            "job": "職業或職稱",
            "income": "月收入 (純數字,單位:元)",
            "amount": "貸款金額 (純數字,單位:元)"
        }
        
        missing_desc = "\n".join([
            f"- {field}: {field_descriptions.get(field, '')}"
            for field in missing_fields
        ])

        is_first_turn = len(history) <= 1
        
        context_hint = ""
        if last_question:
            context_hint = f"\n【上一個問題】\nAssistant 剛問: {last_question}"
        elif is_first_turn:
            context_hint = "\n【特別注意】這是對話的第一輪,使用者可能直接提供資訊而不是在回答問題。"

        prompt = f"""你是一個專業的資訊擷取助手。

【對話歷史】
{history_text if history_text else "(這是第一輪對話)"}
{context_hint}

【當前使用者輸入】
User: {user_input}

【任務說明】
請從「對話歷史」和「當前輸入」中,擷取以下尚未收集的欄位:
{missing_desc}

【重要規則】
1. **上下文理解**: 
   - 如果有上一個問題,使用者很可能是在回答該問題
   - 例如: 上一句問「月收入」,使用者回「5萬」→ 擷取為 income: 50000
   - 如果是第一輪對話,使用者可能直接說出姓名,請直接擷取
   
2. **模糊表達處理**:
   - "5萬多" / "大概5萬" → 50000 (取整數)
   - "50萬左右" → 500000
   - "月薪5萬" → 5萬指的是月收入,擷取為 income: 50000
   
3. **金額轉換**: 自動處理台灣常用單位
   - "5萬" → 50000
   - "50萬" → 500000
   - "100k" → 100000
   - "1M" → 1000000
   
4. **資料清洗**: 
   - 電話號碼去除空格、破折號 (例: 0912-345-678 → 0912345678)
   - 積極擷取明確或暗示的資訊
   
5. **輸出格式**: 
   - 必須是純 JSON,不要包含任何其他文字
   - 格式: {{"field_name": value}}
   - 若真的無法擷取任何欄位,才回傳空物件 {{}}

【範例】
Input: "王小明" (第一輪)
→ {{"name": "王小明"}}

Input: "月薪大概5萬多" (上一題問收入)
→ {{"income": 50000}}

Input: "我想借50萬來買車"  
→ {{"amount": 500000, "loan_purpose": "購車"}}

Input: "A123456789" (上一題問身分證)
→ {{"id": "A123456789"}}

現在請開始擷取:"""

        try:
            response = self.model.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
            )
            
            raw_output = response.text.strip()
            self.logger.info(f"🔍 [Gemini Raw Output]: {raw_output}")
            
            json_str = self._extract_json(raw_output)
            extracted = json.loads(json_str)
            
            # 後處理: 確保金額轉換正確
            if "income" in extracted:
                extracted["income"] = self._parse_amount(str(extracted["income"]))
            if "amount" in extracted:
                extracted["amount"] = self._parse_amount(str(extracted["amount"]))
            
            return extracted
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}\nRaw: {raw_output}")
            return {}
        except Exception as e:
            self.logger.error(f"Slot extraction failed: {e}")
            return {}

    def _extract_json(self, text: str) -> str:
        """從 Gemini 回應中提取 JSON"""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            return text[start:end+1]
        
        return text

    def _parse_amount(self, amount_str):
        """解析台灣常見的金額表達方式"""
        if isinstance(amount_str, (int, float)):
            return int(amount_str)
        
        amount_str = str(amount_str).strip().replace(',', '')
        
        if '萬' in amount_str:
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 10000)
        
        if amount_str.lower().endswith('k'):
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 1000)
        
        if amount_str.lower().endswith('m'):
            num = re.findall(r'[\d.]+', amount_str)
            if num:
                return int(float(num[0]) * 1000000)
        
        try:
            return int(float(amount_str))
        except ValueError:
            return None
