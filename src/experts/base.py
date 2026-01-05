from ..llm_utils import LocalLLMManager

class BaseExpert:
    def __init__(self): 
        # 所有專家共用同一個 LLM 實例，節省記憶體
        self.llm = LocalLLMManager.get_instance()
    
    def process(self, task_data, history=[]): 
        """所有子類別都必須實作這個方法"""
        raise NotImplementedError
    
    def _call_local_llm(self, adapter_path, system_prompt, user_query):
        """呼叫本地微調模型"""
        full_prompt = f"System: {system_prompt}\nUser: {user_query}\nAssistant:"
        return self.llm_manager.get_expert_response(adapter_path, full_prompt)