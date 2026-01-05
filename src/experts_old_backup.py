import openai
import json
from .config import *
from .llm_utils import LocalLLMManager

# 初始化 OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class BaseExpert:
    def __init__(self):
        self.llm_manager = LocalLLMManager.get_instance()

    def process(self, task_data):
        raise NotImplementedError

    def _call_local_llm(self, adapter_path, system_prompt, user_query):
        """呼叫本地微調模型"""
        full_prompt = f"System: {system_prompt}\nUser: {user_query}\nAssistant:"
        return self.llm_manager.get_expert_response(adapter_path, full_prompt)

class LDE_Expert(BaseExpert):
    """
    LDE: 貸款徵審專家 (Loan Default Expert)
    ---------------------------------------------------
    Mode A (Consult): Local LLM (金融知識問答) - 使用微調過的 Llama-3
    Mode B (Guide):   OpenAI API (資料萃取與正規化) - 負責填寫申請表
    """

    def process(self, task_data, history=[]):
        query = task_data.get("user_query", "")
        profile = task_data.get("profile_state", {})
        
        # 1. 判斷模式邏輯
        # 計算已填寫的欄位數量 (排除 None 或空字串)
        filled_count = sum(1 for v in profile.values() if v)
        
        # 關鍵字偵測：判斷用戶是否在問問題
        keywords = ["多少", "利率", "什麼", "資格", "可以嗎", "試算", "好過", "推薦"]
        is_question = any(x in query for x in keywords)
        
        # === Mode A: 諮詢模式 (使用 Local LLM) ===
        # 觸發條件：資料還沒填多少 (filled_count <= 2) 且 用戶在問問題
        if filled_count <= 2 and is_question:
            print(f"🤖 LDE 進入 Mode A (Local LLM): 回答金融問題")
            
            # 呼叫我們剛剛修好的 Alpaca 格式推論函數
            # LDE_SYSTEM_INSTRUCTION 來自 config.py
            ai_response = self.llm.get_expert_response(
                adapter_path=LDE_ADAPTER_PATH,
                instruction=LDE_SYSTEM_INSTRUCTION, 
                user_input=query,
                max_new_tokens=256
            )
            
            return {
                "expert": "LDE (Consult)",
                "response": ai_response,
                "updated_profile": None, # 諮詢模式通常不更新個資
                "next_step": "等待申請意願"
            }
            
        # === Mode B: 引導模式 (使用 OpenAI 進行資料萃取) ===
        # 觸發條件：用戶沒在問問題，或是已經進入填表階段
        else:
            print("🤖 LDE 進入 Mode B (OpenAI): 進行資料萃取...")
            
            # 傳入歷史紀錄給 OpenAI 進行 Context 判讀
            extraction_result = self._openai_extract(query, profile, history)
            
            # 判斷還缺哪些欄位
            required_fields = ["name", "id", "job", "income", "amount"]
            updated_profile = extraction_result.get("updated_profile", {})
            
            # 合併新舊資料來檢查缺件
            # 注意：這裡只是為了檢查缺件，實際更新交給 main/app.py
            current_full_profile = profile.copy()
            if updated_profile:
                current_full_profile.update(updated_profile)
                
            missing = [k for k in required_fields if not current_full_profile.get(k)]
            
            if not missing:
                # 資料全齊
                response_text = "感謝您！您的基本資料已收集完畢，系統將立即為您進行風險評估。"
                next_action = "資料完整，轉送 DVE/FRE"
            else:
                # 還缺件，使用 OpenAI 生成的引導語 (reply_to_user)
                response_text = extraction_result.get("reply_to_user")
                if not response_text:
                    # 防呆：如果 OpenAI 沒回話，手動補一句
                    response_text = f"收到。為了評估您的額度，還需要請問您的：{missing[0]}？"
                next_action = "等待補件"

            return {
                "expert": "LDE (Guide)",
                "response": response_text,
                "updated_profile": updated_profile, # 回傳給 Main 更新 Redis
                "next_step": next_action
            }

    def _openai_extract(self, query, current_profile, history):
        """
        利用 OpenAI 根據「歷史對話」與「當前缺件」決定回應與萃取
        """
        # 將 Redis 的歷史紀錄轉為 OpenAI Message 格式
        # 這裡從 history 取出 content，假設 history 格式為 [{"role":..., "content":...}]
        
        system_prompt = f"""
        你是一個專業的貸款申請引導機器人。
        1. 當前資料狀態 (State): {json.dumps(current_profile, ensure_ascii=False)}
        2. 你的目標：引導用戶填滿所有欄位 (name, id, job, income, amount)。
        3. 規則：
           - 如果缺欄位，請根據對話歷史，自然的追問下一個欄位。
           - 如果用戶提供了資料，請萃取並更新 State。
           - 每次只問一個問題，不要一次問太多。
           - 若用戶說的話與貸款無關，請禮貌地拉回主題。
        4. 輸出格式 (JSON):
           {{
             "updated_profile": {{"job": "工程師", "income": "100萬"...(僅包含本次更新欄位)}},
             "reply_to_user": "給用戶的回應文字 (繁體中文)"
           }}
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 插入最近 5 輪對話歷史 (Context)
        # 需確保 history 格式正確，若 history 內有非 dict 物件需過濾
        if history:
            messages.extend(history[-5:])
        
        # 插入當前用戶輸入
        messages.append({"role": "user", "content": query})

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2 # 低溫以確保 JSON 格式穩定
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ OpenAI Extract Error: {e}")
            return {"updated_profile": {}, "reply_to_user": "系統繁忙，請再輸入一次。"}

class DVE_Expert(BaseExpert):
    """
    DVE: 資料查核驗證專家 [cite: 90]
    任務：處理技術故障、高風險攔截、解釋審核結果
    """
    def process(self, task_data):
        query = task_data.get("user_query", "")
        # 使用 DVE Adapter 生成回應
        system_prompt = "你是資料審核專員。若用戶遇到技術問題，提供上傳建議。若為審核查詢，說明目前進度。"
        
        # 簡單分類是用戶抱怨還是純粹查核
        if any(x in query for x in TECH_KEYWORDS):
            prompt_suffix = " (用戶遇到技術困難，請安撫並提供替代方案)"
        else:
            prompt_suffix = " (用戶正在等待審核，請說明需要人工驗證)"

        ai_response = self._call_local_llm(DVE_ADAPTER_PATH, system_prompt, query + prompt_suffix)
        
        return {
            "expert": "DVE (Verification)",
            "action": "查核與支援",
            "response": ai_response,
            "next_step": "Pending Verification"
        }

class FRE_Expert(BaseExpert):
    """
    FRE: 財務風險評估專家 [cite: 96]
    任務：產出最終核貸報告 (Green Channel 快速通過)
    """
    def process(self, task_data):
        profile = task_data.get("profile_state", {})
        # 構建 Prompt 讓模型生成專業報告
        input_text = f"申請人資料：職業 {profile.get('job')}, 收入 {profile.get('income')}, 申請金額 {profile.get('amount')}。"
        system_prompt = "你是銀行的高級風險分析師。請根據客戶資料，生成一份簡短的核貸評估報告，包含建議利率與額度。"
        
        ai_response = self._call_local_llm(FRE_ADAPTER_PATH, system_prompt, input_text)
        
        return {
            "expert": "FRE (Risk Engine)",
            "action": "產出評估報告",
            "response": ai_response,
            "next_step": "Disbursement"
        }

# 專家工廠
def get_expert_handler(expert_name):
    experts = {
        "LDE": LDE_Expert(),
        "DVE": DVE_Expert(),
        "FRE": FRE_Expert()
    }
    return experts.get(expert_name)