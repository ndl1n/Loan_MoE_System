import sys
import os
import time
import torch

# 把 src 資料夾加入路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_utils import LocalLLMManager
from src.config import LDE_ADAPTER_PATH

def test_llm():
    print("🚀 開始測試：載入 Local LLM 與 Adapter...")
    
    # 檢查 VRAM 狀態
    if torch.cuda.is_available():
        vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"📊 偵測到 GPU VRAM 總量: {vram_total:.2f} GB")
        if vram_total < 6.0:
            print("⚠️ 警告: VRAM 小於 6GB，Llama-3 8B 極可能無法載入 (OOM)。")
            print("   (不用擔心，先讓它跑跑看，失敗了我們有備案)")
    
    start_time = time.time()
    
    try:
        # 1. 測試載入 Base Model
        print(f"⏳ 正在載入基底模型 (Base Model)... 請耐心等待")
        llm = LocalLLMManager.get_instance()
        print(f"✅ Base Model 載入成功！ (耗時: {time.time() - start_time:.2f} 秒)")
        
        # 2. 測試推論 (Inference)
        print("⏳ 正在嘗試生成回應...")
        # 這裡故意用一個不需要 Adapter 的簡單測試，先測底層能不能跑
        res = llm._tokenizer.decode(llm._base_model.generate(
            llm._tokenizer.encode("Hello", return_tensors="pt").to("cuda"), 
            max_new_tokens=10
        )[0])
        print(f"✅ 簡單推論成功: {res}")

        # 3. 測試 Adapter (如果上面沒掛掉的話)
        print(f"⏳ 正在掛載 Adapter: {LDE_ADAPTER_PATH}")
        res_expert = llm.get_expert_response(LDE_ADAPTER_PATH, "請問貸款利率多少？", max_new_tokens=50)
        
        print("\n=== 測試結果 ===")
        print(f"🤖 Expert Response: {res_expert}")
            
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print("\n❌ 【記憶體不足 (OOM)】")
            print("您的 MX350 顯卡記憶體不足以載入這個模型。")
            print("💡 建議方案：我們之後可以改用 'CPU 模式' (較慢) 或 '純 OpenAI 模式'。")
        else:
            print(f"\n❌ 發生其他錯誤: {e}")
    except Exception as e:
        print(f"\n❌ 發生異常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()