import torch
import logging
import os
from typing import Dict, Tuple
from transformers import DistilBertTokenizer

from .config import (
    DEVICE, MODEL_PATH, STRUCT_DIM, MAX_LEN,
    ID2LABEL, STATUS_MAP, CONFIDENCE_THRESHOLD
)
from .model_arch import StateFirstGatingModel

logger = logging.getLogger(__name__)


class MoEGateKeeper:
    """
    MoE 閘門守衛 (根據實際訓練資料優化)
    """
    
    def __init__(self):
        logger.info("🔄 初始化 MoE GateKeeper...")
        
        self.tokenizer = DistilBertTokenizer.from_pretrained(
            'distilbert-base-multilingual-cased'
        )
        
        self.model = StateFirstGatingModel(n_classes=3, struct_dim=STRUCT_DIM)
        self._load_weights()
        self.model.to(DEVICE)
        self.model.eval()
        
        logger.info("✅ MoE GateKeeper 準備就緒!")

    def _load_weights(self):
        """載入預訓練權重"""
        if os.path.exists(MODEL_PATH):
            self.model.load_state_dict(
                torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
            )
            logger.info(f"✅ 載入模型權重: {MODEL_PATH}")
        else:
            raise FileNotFoundError(
                f"❌ 找不到模型權重檔: {MODEL_PATH}\n"
                f"請確認已將 .pth 檔案放入 models 資料夾。"
            )

    def calculate_risk_score(self, profile: Dict) -> float:
        """
        計算風險分數 (根據訓練資料優化)
        
        考慮因素:
        1. 職業穩定性
        2. 收入水平
        3. 貸款用途
        4. 負債比 (DTI)
        
        Returns:
            0.0 ~ 1.0 (0 = 低風險, 1 = 高風險)
        """
        
        job = str(profile.get("job", "")).lower()
        income = profile.get("income", 0)
        purpose = str(profile.get("purpose", "")).lower()
        amount = profile.get("amount", 0)
        
        # === 維度 1: 職業風險 (40% 權重) ===
        job_risk = 0.5
        
        # 根據訓練資料的職業分布
        # 高風險職業
        high_risk_jobs = [
            "自由業", "無業", "待業", "臨時工", "打零工",
            "攤販", "家管", "學生", "兼職"
        ]
        # 低風險職業
        low_risk_jobs = [
            "公務員", "教師", "醫師", "律師", "會計師",
            "工程師", "主管", "經理", "金融", "科技"
        ]
        
        for kw in high_risk_jobs:
            if kw in job:
                job_risk = 0.9
                break
        
        for kw in low_risk_jobs:
            if kw in job:
                job_risk = 0.1
                break
        
        # === 維度 2: 收入風險 (30% 權重) ===
        income_risk = 0.5
        
        if income > 0:
            if income < 30000:
                income_risk = 0.9
            elif income < 50000:
                income_risk = 0.6
            elif income < 70000:
                income_risk = 0.4
            elif income < 100000:
                income_risk = 0.2
            else:
                income_risk = 0.1
        
        # === 維度 3: 貸款用途風險 (20% 權重) ===
        purpose_risk = 0.5
        
        # 低風險用途
        low_risk_purposes = [
            "房屋", "購屋", "頭期款", "教育", "醫療", "創業"
        ]
        # 中高風險用途
        high_risk_purposes = [
            "投資", "債務整合", "週轉", "其他"
        ]
        
        for kw in low_risk_purposes:
            if kw in purpose:
                purpose_risk = 0.2
                break
        
        for kw in high_risk_purposes:
            if kw in purpose:
                purpose_risk = 0.7
                break
        
        # === 維度 4: 負債比風險 (10% 權重) ===
        dti_risk = 0.5
        
        if income > 0 and amount > 0:
            # 假設 5 年期,月還款
            monthly_payment = amount / 60
            dti = monthly_payment / income
            
            if dti > 0.5:
                dti_risk = 1.0
            elif dti > 0.4:
                dti_risk = 0.8
            elif dti > 0.3:
                dti_risk = 0.6
            elif dti > 0.2:
                dti_risk = 0.3
            else:
                dti_risk = 0.1
        
        # === 綜合評分 (加權平均) ===
        risk_score = (
            job_risk * 0.4 +
            income_risk * 0.3 +
            purpose_risk * 0.2 +
            dti_risk * 0.1
        )
        
        logger.info(
            f"📊 風險評分: {risk_score:.2f} "
            f"(職業:{job_risk:.2f}, 收入:{income_risk:.2f}, "
            f"用途:{purpose_risk:.2f}, DTI:{dti_risk:.2f})"
        )
        
        return risk_score

    def predict(self, json_input: Dict) -> Tuple[str, float, str]:
        """
        預測路由目標
        
        Args:
            json_input: {
                "profile_state": {...},
                "verification_status": "unknown|pending|verified|mismatch",
                "user_query": "當前使用者問題"
            }
        
        Returns:
            (expert, confidence, reason)
        """
        
        profile = json_input.get("profile_state", {})
        status_str = json_input.get("verification_status", "unknown")
        text = json_input.get("user_query", "")
        
        # 計算風險分數
        risk_score = self.calculate_risk_score(profile)

        # ==========================
        # 1. 邏輯護欄層 (Guardrails)
        # ==========================
        
        # [A] 資料不完整: unknown → LDE
        if status_str == "unknown":
            logger.info("🛡️  Guardrail: 資料未完成 → LDE")
            return "LDE", 1.0, "Guardrail: Incomplete Data (unknown status)"
        
        # [B] 缺少必要欄位: → LDE
        # 根據訓練資料,name 必須有 (id 可以 null)
        if not profile.get("name"):
            logger.info("🛡️  Guardrail: 缺少姓名 → LDE")
            return "LDE", 1.0, "Guardrail: Missing Name"
        
        # [C] 已驗證: verified → FRE (進行風險評估)
        if status_str == "verified":
            logger.info("🛡️  Guardrail: 已驗證 → FRE")
            return "FRE", 1.0, "Guardrail: Verified Status → Risk Assessment"
        
        # [D] 欄位不符: mismatch → LDE (讓專員處理)
        if status_str == "mismatch":
            logger.info("🛡️  Guardrail: 資料不符 → LDE")
            return "LDE", 1.0, "Guardrail: Data Mismatch → Agent Review"
        
        # [E] 技術問題: → DVE
        tech_keywords = [
            "系統", "錯誤", "無法", "bug", "故障", "異常",
            "補件", "驗證", "確認", "資料"
        ]
        if any(kw in text for kw in tech_keywords):
            logger.info("🛡️  Guardrail: 技術/補件問題 → DVE")
            return "DVE", 0.95, "Guardrail: Technical/Verification Issue"
        
        # [F] pending 狀態下的路由邏輯
        if status_str == "pending":
            # pending + 高風險 → DVE (先嚴格驗證)
            if risk_score >= 0.7:
                logger.info("🛡️  Guardrail: Pending + 高風險 → DVE")
                return "DVE", 0.90, "Guardrail: High Risk Verification"
            
            # pending + 極低風險 → DVE (但可能快速通過)
            # 注意: 根據訓練資料,pending 通常會到 DVE
            if risk_score <= 0.3:
                logger.info("🛡️  Guardrail: Pending + 低風險 → DVE")
                return "DVE", 0.85, "Guardrail: Low Risk Quick Verification"
        
        # [G] 額度相關問題: verified → FRE
        quota_keywords = ["額度", "申覆", "金額", "多少錢", "可以貸"]
        if any(kw in text for kw in quota_keywords) and status_str == "verified":
            logger.info("🛡️  Guardrail: 額度問題 → FRE")
            return "FRE", 0.95, "Guardrail: Quota/Amount Inquiry"

        # ==========================
        # 2. AI 推理層
        # ==========================
        logger.info("🤖 進入 AI 推理層...")
        return self._ai_inference(text, profile, status_str, risk_score)

    def _ai_inference(
        self,
        text: str,
        profile: Dict,
        status_str: str,
        risk_score: float
    ) -> tuple:
        """
        AI 模型推理
        """
        
        try:
            # === 準備文字特徵 ===
            encoding = self.tokenizer.encode_plus(
                text,
                max_length=MAX_LEN,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            # === 準備結構特徵 (7 維) ===
            # 根據訓練時的特徵工程
            
            # 1. 欄位存在性
            has_id = 1.0 if profile.get("id") else 0.0
            has_name = 1.0 if profile.get("name") else 0.0
            has_job = 1.0 if profile.get("job") else 0.0
            has_income = 1.0 if profile.get("income") else 0.0
            
            # 2. 狀態值
            status_val = STATUS_MAP.get(status_str, 0)
            
            # 3. 資料完整度
            all_fields = ["name", "id", "job", "income", "purpose", "amount"]
            filled = sum(1 for f in all_fields if profile.get(f) is not None)
            sparsity = filled / len(all_fields)
            
            # 4. 風險分數
            # 已經計算好了
            
            # 組裝特徵向量
            struct_features = torch.tensor([
                has_id,
                has_name,
                has_job,
                has_income,
                status_val / 4.0,  # 正規化 (0~4 → 0~1)
                sparsity,
                risk_score
            ], dtype=torch.float).unsqueeze(0).to(DEVICE)
            
            logger.debug(f"結構特徵: {struct_features.cpu().numpy()}")
            
            # === 模型推理 ===
            input_ids = encoding['input_ids'].to(DEVICE)
            attention_mask = encoding['attention_mask'].to(DEVICE)

            with torch.no_grad():
                outputs = self.model(input_ids, attention_mask, struct_features)
                probs = torch.nn.functional.softmax(outputs, dim=1)
                pred_idx = torch.argmax(probs, dim=1).item()
                confidence = probs[0][pred_idx].item()
            
            expert = ID2LABEL[pred_idx]
            
            logger.info(
                f"🎯 AI 推理: {expert} (信心度: {confidence:.2f}), "
                f"機率分布: {probs.cpu().numpy()}"
            )
            
            # === 信心度檢查 ===
            if confidence < CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"⚠️  信心度過低 ({confidence:.2f}), 使用規則式 Fallback"
                )
                return self._rule_based_fallback(profile, status_str, risk_score)
            
            return expert, confidence, "AI Model Inference"
        
        except Exception as e:
            logger.error(f"❌ AI 推理失敗: {e}", exc_info=True)
            return self._rule_based_fallback(profile, status_str, risk_score)
    
    def _rule_based_fallback(
        self,
        profile: Dict,
        status_str: str,
        risk_score: float
    ) -> Tuple[str, float, str]:
        """
        規則式 Fallback
        """
        
        logger.info("🔧 使用規則式 Fallback")
        
        if status_str == "unknown":
            return "LDE", 0.75, "Rule Fallback: Unknown → LDE"
        elif status_str == "pending":
            return "DVE", 0.75, "Rule Fallback: Pending → DVE"
        elif status_str == "verified":
            return "FRE", 0.75, "Rule Fallback: Verified → FRE"
        elif status_str == "mismatch":
            return "LDE", 0.75, "Rule Fallback: Mismatch → LDE"
        else:
            return "LDE", 0.5, "Rule Fallback: Default → LDE"