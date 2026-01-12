"""
Base Expert - 專家基類
所有專家 (LDE, DVE, FRE) 的共同父類
"""

import sys
import os

# 確保可以找到上層模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils import LocalLLMManager


class BaseExpert:
    """
    專家基類
    
    提供:
    - 共用的 LLM Manager (Singleton)
    - 統一的介面定義
    """
    
    def __init__(self):
        """
        初始化基類
        所有專家共用同一個 LLM 實例,節省記憶體
        """
        self.llm = LocalLLMManager.get_instance()
    
    def process(self, task_data, history=[]):
        """
        處理專家任務 (子類必須實作)
        
        Args:
            task_data: {
                "user_query": "使用者問題",
                "profile_state": {...},
                "verification_status": "unknown|pending|verified|mismatch"
            }
            history: 對話歷史
        
        Returns:
            {
                "expert": "專家名稱",
                "mode": "模式",
                "response": "回覆內容",
                "updated_profile": {...} or None,
                "next_step": "下一步建議"
            }
        """
        raise NotImplementedError("子類必須實作 process() 方法")
    
    def _call_local_llm(
        self,
        adapter_path,
        system_prompt,
        user_query,
        template=None,
        max_new_tokens=256
    ):
        """
        呼叫本地微調模型的便捷方法
        
        Args:
            adapter_path: LoRA adapter 路徑
            system_prompt: 系統指令
            user_query: 使用者問題
            template: Prompt template (可選)
            max_new_tokens: 最大生成長度
        
        Returns:
            生成的文字
        """
        return self.llm.get_expert_response(
            adapter_path=adapter_path,
            instruction=system_prompt,
            user_input=user_query,
            template=template,
            max_new_tokens=max_new_tokens
        )