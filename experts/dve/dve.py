"""
DVE Expert (Data Verification Expert) - 資料查核專家
遷移版 - 保持原有邏輯,調整路徑

特色:
1. Regex JSON 提取 (防止字串內括號干擾)
2. 自動清洗 Hallucination
3. 動態存檔 (修復寫死欄位的 Bug)
4. MongoDB + RAG 比對歷史資料
"""

import json
import torch
import logging
import re
from datetime import datetime
from transformers import TextStreamer
from peft import PeftModel

# 從上層導入
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    DVE_ADAPTER_PATH,
    DVE_PROMPT_TEMPLATE,
    DVE_INSTRUCTION,
    DEVICE,
    ENABLE_FINETUNED_MODELS
)
from services.rag_service import rag_engine
from experts.base import BaseExpert

logger = logging.getLogger(__name__)


class DVE_Expert(BaseExpert):
    """
    DVE: 資料查核專家 (Ultimate Robust Version)
    
    職責:
    - 比對使用者口述資料與歷史紀錄
    - 標記風險等級 (LOW/MEDIUM/HIGH)
    - 自動封存本次申請資料
    """
    
    def __init__(self):
        """初始化 DVE Expert"""
        # 只在啟用 fine-tuned models 時才初始化 LLM
        if ENABLE_FINETUNED_MODELS:
            super().__init__()
            logger.info("✅ DVE Expert 初始化完成 (含 Fine-tuned Model)")
        else:
            logger.warning("⚠️  DVE Expert: Fine-tuned Model 未啟用")
            self.llm = None
        
        logger.info("✅ DVE Expert 就緒")
    
    def process(self, task_data, history=[]):
        """
        處理 DVE 任務
        
        Args:
            task_data: {
                "user_query": "使用者問題",
                "profile_state": {...},
                "verification_status": "pending"
            }
            history: 對話歷史
        
        Returns:
            {
                "expert": "DVE (風險等級)",
                "response": "回覆內容",
                "dve_raw_report": {...},
                "next_step": "下一步建議"
            }
        """
        
        query = task_data.get("user_query", "")
        profile = task_data.get("profile_state", {})
        
        logger.info(f"📍 DVE 處理: user_id={profile.get('id', 'UNKNOWN')}")
        
        # === 1. 技術障礙攔截 (Rule-based) ===
        tech_keywords = ["傳不上", "失敗", "格式錯誤", "太慢", "當機", "無法"]
        if any(k in query for k in tech_keywords):
            logger.info("🛡️  DVE 偵測到技術問題")
            return {
                "expert": "DVE (Tech Support)",
                "mode": "tech_support",
                "response": "偵測到技術問題。請確認圖片格式為 JPG/PNG 且小於 5MB。",
                "next_step": "等待技術排除"
            }
        
        logger.info("🛡️  DVE 啟動 AI 查核模式 (Loading from MongoDB)...")
        
        # === 2. 準備 RAG 資料 (Context) ===
        user_id = profile.get("id", "UNKNOWN")
        user_name = profile.get("name", "Guest")
        
        # 從 MongoDB 撈取歷史紀錄
        history_records = rag_engine.get_user_history_by_id(user_id)
        
        rag_context = {}
        
        if history_records:
            logger.info(f"🔍 發現 {len(history_records)} 筆歷史紀錄")
            latest_record = history_records[-1]  # 取最新
            meta = latest_record.get("metadata", {})
            
            # 直接從 Metadata 對應到 DVE 需要的 Key
            rag_context = {
                "檔案中紀錄職業": meta.get("hist_job", "無紀錄"),
                "上次貸款資金用途": meta.get("hist_purpose", "無紀錄"),
                "檔案中聯絡電話": meta.get("hist_phone", "無紀錄"),
                "歷史違約紀錄": meta.get("default_record", "無"),
                "檔案中服務公司名稱": meta.get("hist_company", "無紀錄"),
                "檔案中年薪/月薪": str(meta.get("hist_income", "0")),
                "信用報告查詢次數": str(meta.get("inquiry_count", "0")),
                "地址變動次數": str(meta.get("addr_change_count", "0"))
            }
        else:
            logger.warning("⚠️  新用戶 (無歷史紀錄)")
            rag_context = {
                "檔案中紀錄職業": "無紀錄 (新戶)",
                "上次貸款資金用途": "無紀錄",
                "檔案中聯絡電話": "無紀錄",
                "歷史違約紀錄": "無",
                "檔案中服務公司名稱": "無紀錄",
                "檔案中年薪/月薪": "0",
                "信用報告查詢次數": "0",
                "地址變動次數": "0"
            }
        
        # === 3. 組建 Input JSON ===
        # 提取變數以便後續存檔
        q_job = profile.get("job", "待業中")
        q_purpose = profile.get("purpose", "一般週轉")
        q_phone = profile.get("phone", "09xx-xxx-xxx")
        q_company = profile.get("company", "未提供")
        q_income = str(profile.get("income", "0"))
        
        dve_input_data = {
            "核心識別資訊": {
                "申請人姓名": user_name,
                "身分證字號": user_id
            },
            "最新口述資訊 (Query) 擷取": {
                "職業": q_job,
                "資金用途": q_purpose,
                "聯絡電話": q_phone,
                "服務公司名稱": q_company,
                "月薪": q_income
            },
            "RAG 檢索的歷史數據 (Context) 擷取": rag_context
        }
        
        input_json_str = json.dumps(dve_input_data, ensure_ascii=False)
        
        logger.debug(f"📝 DVE Input JSON:\n{json.dumps(dve_input_data, indent=2, ensure_ascii=False)}")
        
        # === 4. 呼叫 LLM 進行驗證 ===
        if not ENABLE_FINETUNED_MODELS or self.llm is None:
            logger.warning("⚠️  Fine-tuned Model 未啟用,使用規則式驗證")
            return self._rule_based_verification(
                profile, rag_context, q_job, q_purpose, q_phone, q_company, q_income
            )
        
        try:
            report = self._ai_verification(
                input_json_str,
                user_name,
                user_id,
                q_job,
                q_purpose,
                q_phone,
                q_company,
                q_income,
                rag_context
            )
            
            return self._process_verification_result(
                report,
                user_name,
                user_id,
                q_job,
                q_purpose,
                q_phone,
                q_company,
                q_income,
                rag_context
            )
            
        except Exception as e:
            logger.error(f"❌ DVE AI 驗證失敗: {e}", exc_info=True)
            
            # Fallback 規則式驗證
            return self._rule_based_verification(
                profile, rag_context, q_job, q_purpose, q_phone, q_company, q_income
            )
    
    def _ai_verification(
        self,
        input_json_str,
        user_name,
        user_id,
        q_job,
        q_purpose,
        q_phone,
        q_company,
        q_income,
        rag_context
    ):
        """
        AI 模型驗證
        使用 Fine-tuned Model
        """
        
        logger.info("🤖 DVE AI 驗證模式 (Fine-tuned Model)")
        
        # 載入模型
        model = PeftModel.from_pretrained(self.llm._base_model, DVE_ADAPTER_PATH)
        model.eval()
        
        tokenizer = self.llm._tokenizer
        
        # 構建 Prompt
        prompt = DVE_PROMPT_TEMPLATE.format(
            instruction=DVE_INSTRUCTION,
            input_text=input_json_str
        )
        
        inputs = tokenizer(prompt, return_tensors="pt")
        
        # 移動到正確設備
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Stream 模式生成
        streamer = TextStreamer(tokenizer, skip_prompt=True)
        
        logger.info("🌊 開始生成 DVE 報告 (Stream Mode)...")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                streamer=streamer,
                max_new_tokens=512,
                temperature=0.1,
                repetition_penalty=1.2,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 解碼完整文字
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # 解析 JSON
        report = self._parse_dve_output(full_text)
        
        return report
    
    def _parse_dve_output(self, full_text):
        """
        解析 DVE 模型輸出
        使用 Regex 提取 JSON
        """
        
        try:
            # Step A: 粗略切割
            if "<|end_of_text|>" in full_text:
                full_text = full_text.split("<|end_of_text|>")[0]
            
            if "### Output:" in full_text:
                generated_text = full_text.split("### Output:")[1].strip()
            else:
                generated_text = full_text
            
            # Step B: 清洗已知的怪異 Token
            generated_text = generated_text.replace("Portály", "")
            
            # Step C: JSON 提取 (Regex 優先)
            match = re.search(r"(\{.*\})", generated_text, re.DOTALL)
            
            json_str = ""
            if match:
                json_str = match.group(1)
            else:
                # Fallback: find/rfind
                start_idx = generated_text.find("{")
                end_idx = generated_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_str = generated_text[start_idx:end_idx+1]
            
            if not json_str:
                raise ValueError("無法提取 JSON 結構")
            
            # Step D: JSON 載入與修復
            try:
                report = json.loads(json_str)
            except json.JSONDecodeError:
                # 嘗試修復引號
                if json_str.count('"') % 2 != 0:
                    json_str = json_str.replace('"}', '"}')
                report = json.loads(json_str)
            
            logger.info(f"✅ DVE 報告解析成功: {str(report)[:100]}...")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ DVE 報告解析失敗: {e}")
            raise
    
    def _process_verification_result(
        self,
        report,
        user_name,
        user_id,
        q_job,
        q_purpose,
        q_phone,
        q_company,
        q_income,
        rag_context
    ):
        """
        處理驗證結果並自動存檔
        """
        
        # 讀取結果
        check_status = report.get("核實狀態", "UNKNOWN")
        risk_level = report.get("風險標記", "MEDIUM")
        
        # 強制邏輯: 如果有 MISMATCH_FOUND,風險不可能是 LOW
        if check_status == "MISMATCH_FOUND" and risk_level == "LOW":
            risk_level = "MEDIUM"
            logger.warning("⚠️  強制修正: MISMATCH_FOUND 不應為 LOW 風險")
        
        # === 自動存檔機制 ===
        logger.info(f"💾 正在封存本次申請資料至 MongoDB ({user_name})...")
        
        archive_content = (
            f"【銀行內部存檔】\n"
            f"存檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"客戶姓名: {user_name} ({user_id})\n"
            f"職業紀錄: 任職於「{q_company}」,職稱為「{q_job}」\n"
            f"財務紀錄: 口述月薪 {q_income} 元\n"
            f"查核結果: 本次 DVE 查核風險為 {risk_level}"
        )
        
        # Metadata 動態寫入
        archive_meta = {
            "name": user_name,
            "hist_job": q_job,
            "hist_company": q_company,
            "hist_income": q_income,
            "hist_phone": q_phone,
            "hist_purpose": q_purpose,
            "default_record": "無",
            "inquiry_count": str(int(rag_context.get("信用報告查詢次數", "0")) + 1),
            "last_risk_level": risk_level,
            "check_status": check_status
        }
        
        # 寫入資料庫
        rag_engine.add_document(user_id, archive_content, metadata=archive_meta)
        
        logger.info("✅ 資料封存完成!")
        
        # === 決定回覆與下一步 ===
        if risk_level == "LOW":
            user_res = "資料驗證無誤,正在為您進行試算。"
            next_step = "TRANSFER_TO_FRE"
        elif risk_level == "HIGH":
            user_res = "系統偵測到您的資料與紀錄有出入,請說明目前狀況。"
            next_step = "FORCE_LDE_CLARIFY"
        else:  # MEDIUM
            user_res = "資料已受理,將轉由人工覆核。"
            next_step = "TRANSFER_TO_FRE"
        
        return {
            "expert": f"DVE ({risk_level})",
            "mode": "ai_verification",
            "response": user_res,
            "dve_raw_report": report,
            "next_step": next_step,
            "risk_level": risk_level,
            "check_status": check_status
        }
    
    def _rule_based_verification(
        self,
        profile,
        rag_context,
        q_job,
        q_purpose,
        q_phone,
        q_company,
        q_income
    ):
        """
        規則式驗證 (Fallback)
        當 AI 模型不可用時使用
        """
        
        logger.info("🔧 DVE 規則式驗證模式 (Fallback)")
        
        # 簡單規則比對
        mismatches = []
        
        # 比對職業
        hist_job = rag_context.get("檔案中紀錄職業", "")
        if hist_job != "無紀錄" and hist_job != "無紀錄 (新戶)" and hist_job != q_job:
            mismatches.append(f"職業不符 (歷史: {hist_job}, 口述: {q_job})")
        
        # 比對收入
        hist_income = rag_context.get("檔案中年薪/月薪", "0")
        if hist_income != "0" and abs(int(hist_income) - int(q_income)) > int(q_income) * 0.2:
            mismatches.append(f"收入差異過大 (歷史: {hist_income}, 口述: {q_income})")
        
        # 比對電話
        hist_phone = rag_context.get("檔案中聯絡電話", "")
        if hist_phone != "無紀錄" and hist_phone != q_phone:
            mismatches.append(f"電話不符 (歷史: {hist_phone}, 口述: {q_phone})")
        
        # 判斷風險等級
        if len(mismatches) >= 2:
            risk_level = "HIGH"
            user_res = "系統偵測到您的資料與紀錄有多處不符,請說明。"
            next_step = "FORCE_LDE_CLARIFY"
        elif len(mismatches) == 1:
            risk_level = "MEDIUM"
            user_res = "資料已受理,將轉由人工覆核。"
            next_step = "TRANSFER_TO_FRE"
        else:
            risk_level = "LOW"
            user_res = "資料驗證無誤,正在為您進行試算。"
            next_step = "TRANSFER_TO_FRE"
        
        logger.info(f"🔧 規則式驗證結果: {risk_level}, 不符項目: {len(mismatches)}")
        
        return {
            "expert": f"DVE ({risk_level})",
            "mode": "rule_based",
            "response": user_res,
            "dve_raw_report": {
                "風險標記": risk_level,
                "核實狀態": "CHECKED",
                "不符項目": mismatches
            },
            "next_step": next_step,
            "risk_level": risk_level
        }