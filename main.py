import json
import torch
from src.config import DEVICE, STATUS_MAP
from src.gating_engine import MoEGateKeeper
from src.experts import get_expert_handler

# 模擬前端傳來的 JSON 資料 (測試案例)
TEST_CASES = [
    # Case 1: 綠色通道 (VIP 醫師，資料完整) -> 預期：FRE (Risk Engine)
    {
        "user_query": "我想要申請貸款，資料都填好了，請盡快撥款。",
        "profile_state": {
            "id": "A123456789", "name": "柯文哲", "job": "台大醫師", 
            "income": "300000", "amount": "2000000", "risk_score": 0.0
        },
        "verification_status": "pending"
    },
    # Case 2: 技術攔截 (使用者抱怨上傳失敗) -> 預期：DVE (Tech Support)
    {
        "user_query": "為什麼財力證明一直傳不上去？系統是不是壞了？",
        "profile_state": {
            "id": "B123456789", "name": "王小明", "job": "工程師",
            "income": "50000", "amount": "500000"
        },
        "verification_status": "pending"
    },
    # Case 3: LDE 引導 (缺件且在問問題) -> 預期：LDE (Consultant)
    {
        "user_query": "請問你們的利率大概多少？我也還沒填身分證。",
        "profile_state": {
            "job": "服務業", "amount": "100000" 
        },
        "verification_status": "unknown"
    },
    # Case 4: LDE 補件 (被 LDE 發現缺件) -> 預期：LDE (Guide)
    {
        "user_query": "我叫李大同，想借十萬。",
        "profile_state": {
            "name": "李大同", "amount": "100000"
        },
        "verification_status": "pending"
    }
]

def main():
    print(f"🚀 啟動 MoE 貸款風險智慧分流系統 (Device: {DEVICE})")
    
    # 1. 初始化門控模型 (Gating Network)
    # 載入訓練好的權重，準備進行路由
    gate_keeper = MoEGateKeeper()
    
    print("\n" + "="*50)
    print("🧪 開始執行測試案例 (Simulating API Requests)")
    print("="*50 + "\n")

    for i, request_data in enumerate(TEST_CASES):
        print(f"🔹 [Case {i+1}] User Query: {request_data['user_query']}")
        
        # 2. 門控決策 (Routing)
        # 輸入：User Query + Profile State
        # 輸出：專家標籤 (LDE/DVE/FRE), 信心度, 決策理由
        expert_label, confidence, reason = gate_keeper.predict(request_data)
        
        print(f"   └── 🤖 Gating Decision: \033[92m{expert_label}\033[0m (Conf: {confidence:.2f})")
        print(f"   └── 📝 Reason: {reason}")
        
        # 3. 專家調度 (Dispatching)
        # 根據標籤實例化對應的 Expert Class
        expert = get_expert_handler(expert_label.split()[0]) # 取前綴 LDE/DVE/FRE
        
        if expert:
            # 4. 專家執行 (Execution)
            # Expert 內部會呼叫 Local LLM 或 OpenAI
            print(f"   └── ⚙️  Calling {expert_label}...")
            result = expert.process(request_data)
            
            # 5. 輸出結果
            print(f"   └── 💬 Response: {result['response']}")
            print(f"   └── ⏭️  Next Step: {result['next_step']}")
            
            # 若有資料更新 (如 LDE 萃取了新欄位)，這裡模擬寫回資料庫
            if "updated_profile" in result:
                print(f"   └── 💾 Database Update: {result['updated_profile']}")
        else:
            print(f"   └── ❌ Error: No handler found for {expert_label}")
            
        print("-" * 50)

if __name__ == "__main__":
    main()