import torch
import numpy as np
from transformers import DistilBertTokenizer
from .config import *
from .model_arch import StateFirstGatingModel

class MoEGateKeeper:
    def __init__(self):
        print("🔄 初始化 MoE GateKeeper...")
        self.tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-multilingual-cased')
        self.model = StateFirstGatingModel(n_classes=3, struct_dim=STRUCT_DIM)
        self._load_weights()
        self.model.to(DEVICE)
        self.model.eval()
        print("✅ MoE GateKeeper 準備就緒！")

    def _load_weights(self):
        if os.path.exists(MODEL_PATH):
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        else:
            raise FileNotFoundError(f"❌ 找不到模型權重檔：{MODEL_PATH}\n請確認已將 .pth 檔案放入 models 資料夾。")

    def calculate_risk_score(self, profile):
        job = str(profile.get("job", ""))
        income = str(profile.get("income", ""))
        blob = job + income
        
        # 簡單規則引擎
        for kw in RISK_HIGH_KWS:
            if kw in blob: return 1.0
        for kw in RISK_LOW_KWS:
            if kw in blob: return 0.0
        return 0.5

    def predict(self, json_input):
        profile = json_input.get("profile_state", {})
        status_str = json_input.get("verification_status", "unknown")
        text = json_input.get("user_query", "")
        
        risk_score = self.calculate_risk_score(profile)

        # ==========================
        # 1. 邏輯護欄層 (Guardrails)
        # ==========================
        
        # [A] 安全底線: 缺件必退
        if not profile.get("id") or not profile.get("name"):
            return "LDE", 1.0, "Guardrail: Safety Floor"

        # [B] 狀態直通: 已核准
        if status_str == "verified":
            return "FRE", 1.0, "Guardrail: State Bypass"

        # [C] 技術攔截: 系統故障
        if any(kw in text for kw in TECH_KEYWORDS):
            return "DVE", 0.95, "Guardrail: Tech Interceptor"

        # [D] 紅色通道: 高風險阻擋
        if risk_score == 1.0 and status_str == "pending":
            return "DVE", 0.95, "Guardrail: Red Channel"

        # [E] 綠色通道: 低風險直通
        if risk_score == 0.0 and status_str == "pending":
            return "FRE", 0.95, "Guardrail: Green Channel"

        # ==========================
        # 2. 混合 AI 推理層
        # ==========================
        return self._ai_inference(text, profile, status_str, risk_score)

    def _ai_inference(self, text, profile, status_str, risk_score):
        # 準備文字特徵
        encoding = self.tokenizer.encode_plus(
            text, max_length=MAX_LEN, padding='max_length', truncation=True, return_tensors='pt'
        )
        
        # 準備結構特徵
        has_id = 1.0 if profile.get("id") else 0.0
        has_name = 1.0 if profile.get("name") else 0.0
        has_job = 1.0 if profile.get("job") else 0.0
        has_income = 1.0 if profile.get("income") else 0.0
        status_val = STATUS_MAP.get(status_str, 0)
        
        filled = sum(1 for k, v in profile.items() if v is not None)
        sparsity = filled / 6.0
        
        struct_features = torch.tensor([
            has_id, has_name, has_job, has_income, status_val / 3.0, sparsity, risk_score
        ], dtype=torch.float).unsqueeze(0).to(DEVICE)
        
        input_ids = encoding['input_ids'].to(DEVICE)
        attention_mask = encoding['attention_mask'].to(DEVICE)

        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask, struct_features)
            probs = torch.nn.functional.softmax(outputs, dim=1)
            pred_idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][pred_idx].item()
        
        return ID2LABEL[pred_idx], confidence, "AI Model Inference"