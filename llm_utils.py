"""
Local LLM Manager - 本地模型管理器
使用 Singleton 模式管理所有專家共用的 Base Model
"""

import torch
import os
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

from config import BASE_MODEL_PATH, DEVICE, ENABLE_FINETUNED_MODELS

logger = logging.getLogger(__name__)


class LocalLLMManager:
    """
    本地 LLM 管理器 (Singleton)
    
    職責:
    - 載入並管理 Base Model
    - 動態切換不同的 LoRA Adapter
    - 執行推理
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """取得 Singleton 實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        初始化 Base Model
        只會執行一次 (Singleton)
        """
        
        if LocalLLMManager._instance is not None:
            raise RuntimeError("請使用 get_instance() 取得實例")
        
        # 檢查是否啟用 Fine-tuned Models
        if not ENABLE_FINETUNED_MODELS:
            logger.warning("⚠️  Fine-tuned Models 未啟用，LocalLLMManager 將不載入模型")
            self._tokenizer = None
            self._base_model = None
            self._loaded_adapters = {}
            self.terminators = []
            return
        
        logger.info(f"🔄 [LocalLLM] 載入 Base Model: {BASE_MODEL_PATH}...")
        
        # === 配置 4-bit 量化 ===
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        
        # === 載入 Tokenizer ===
        self._tokenizer = AutoTokenizer.from_pretrained(
            BASE_MODEL_PATH,
            trust_remote_code=True
        )
        
        # === 載入 Base Model ===
        self._base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            quantization_config=bnb_config,
            device_map="auto",  # 自動分配到 GPU
            trust_remote_code=True
        )
        
        # === 設定終止符號 ===
        self.terminators = [
            self._tokenizer.eos_token_id,
            self._tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]
        
        logger.info("✅ Base Model 載入完成")
    
    def get_expert_response(
        self,
        adapter_path: str,
        instruction: str,
        user_input: str,
        max_new_tokens: int = 256,
        temperature: float = 0.3,
        top_p: float = 0.9,
        template: str = None
    ) -> str:
        """
        使用指定的 Adapter 進行推理
        
        Args:
            adapter_path: LoRA Adapter 路徑
            instruction: 系統指令
            user_input: 使用者輸入
            max_new_tokens: 最大生成長度
            temperature: 溫度參數
            top_p: Top-p 採樣
            template: Prompt Template (可選)
        
        Returns:
            生成的文字
        """
        
        # === 1. 檢查 Adapter 是否存在 ===
        adapter_file = os.path.join(adapter_path, "adapter_model.safetensors")
        
        if not os.path.exists(adapter_file):
            logger.error(f"❌ 找不到 Adapter: {adapter_file}")
            return "系統錯誤: 找不到模型權重檔"
        
        logger.debug(f"📂 載入 Adapter: {adapter_path}")
        
        # === 2. 掛載 Adapter ===
        try:
            model = PeftModel.from_pretrained(self._base_model, adapter_path)
            model.eval()
        except Exception as e:
            logger.error(f"❌ Adapter 載入失敗: {e}", exc_info=True)
            return f"系統錯誤: 模型載入失敗 ({str(e)})"
        
        # === 3. 格式化輸入 ===
        if template:
            # 使用提供的 template
            # 注意: template 應該有 {instruction} 和 {input_text} 兩個佔位符
            try:
                formatted_prompt = template.format(
                    instruction=instruction,
                    input_text=user_input
                )
            except KeyError:
                # 如果 template 格式不對,使用預設格式
                logger.warning("⚠️  Template 格式錯誤,使用預設格式")
                formatted_prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{user_input}\n\n### Output:\n"
        else:
            # 預設 Alpaca 格式
            formatted_prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{user_input}\n\n### Output:\n"
        
        logger.debug(f"Prompt 前 200 字: {formatted_prompt[:200]}...")
        
        # === 4. Tokenize ===
        inputs = self._tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        # 移動到正確的設備
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # === 5. 生成回應 ===
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    use_cache=True,
                    eos_token_id=self.terminators,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True if temperature > 0 else False
                )
        except Exception as e:
            logger.error(f"❌ 生成失敗: {e}", exc_info=True)
            return f"系統錯誤: 生成失敗 ({str(e)})"
        
        # === 6. 解碼與切割 ===
        full_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            # 嘗試切割 "### Output:" 後的內容
            if "### Output:" in full_text:
                generated_text = full_text.split("### Output:")[1].strip()
                
                # 如果模型自己又生成了下一個 Instruction,切掉
                if "### Instruction:" in generated_text:
                    generated_text = generated_text.split("### Instruction:")[0].strip()
            else:
                # 如果沒有 "### Output:",可能是 template 不同
                # 嘗試找到 input 之後的內容
                generated_text = full_text
        
        except Exception as e:
            logger.warning(f"⚠️  文字切割失敗,返回完整輸出: {e}")
            generated_text = full_text
        
        logger.debug(f"生成文字: {generated_text[:100]}...")
        
        return generated_text.strip()