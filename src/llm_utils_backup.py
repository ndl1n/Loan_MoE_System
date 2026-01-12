import torch
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from .config import BASE_MODEL_PATH, DEVICE, LDE_PROMPT_TEMPLATE

class LocalLLMManager:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        print(f"🔄 [WSL2] Loading Base Model: {BASE_MODEL_PATH}...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)
        self._base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            quantization_config=bnb_config,
            device_map=DEVICE,
            trust_remote_code=True
        )
        self.terminators = [
            self._tokenizer.eos_token_id,
            self._tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]
        print("✅ Base Model Loaded.")

    def get_expert_response(self, adapter_path, instruction, user_input, 
                          max_new_tokens=256, temperature=0.3, top_p=0.9, template=None):
        """
        通用專家推論函數
        """
        if not os.path.exists(os.path.join(adapter_path, "adapter_model.safetensors")):
             return "系統錯誤：找不到模型權重檔"
        
        # 1. 掛載 Adapter
        model = PeftModel.from_pretrained(self._base_model, adapter_path)
        model.eval()
        
        # 2. 格式化輸入
        # 如果有傳入特定的 template (如 DVE_PROMPT_TEMPLATE) 就用它，否則用預設的
        if template:
            formatted_prompt = template.format(instruction, user_input)
        else:
            # 預設 fallback (如果沒傳 template)
            formatted_prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{user_input}\n\n### Output:\n"
        
        inputs = self._tokenizer(formatted_prompt, return_tensors="pt").to(DEVICE)
        
        # 3. 生成回應
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                use_cache=True,
                eos_token_id=self.terminators,
                temperature=temperature,  # 動態調整
                top_p=top_p
            )
        
        # 4. 解碼與切割
        full_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        try:
            generated_text = full_text.split("### Output:")[1].strip()
            # DVE 修正：有時候模型會自己吐出下一個 ### Instruction，要切掉
            if "### Instruction:" in generated_text:
                generated_text = generated_text.split("### Instruction:")[0].strip()
        except IndexError:
            generated_text = full_text
            
        return generated_text