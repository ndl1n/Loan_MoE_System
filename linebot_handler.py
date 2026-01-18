"""
LINE Bot 模組
包含 LINE 特定功能、Flex Message 模板等

Features:
- Rich Menu 設定
- Flex Message 模板
- 快速回覆按鈕
- 推播通知
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ==========================================
# LINE Bot SDK Import (Optional)
# ==========================================
try:
    from linebot.v3.messaging import (
        FlexMessage,
        FlexContainer,
        FlexBubble,
        FlexBox,
        FlexText,
        FlexButton,
        FlexSeparator,
        FlexImage,
        QuickReply,
        QuickReplyItem,
        MessageAction,
        URIAction
    )
    LINEBOT_SDK_AVAILABLE = True
except ImportError:
    LINEBOT_SDK_AVAILABLE = False
    logger.warning("LINE Bot SDK not installed. Flex messages will be disabled.")


# ==========================================
# Flex Message Templates
# ==========================================
class FlexTemplates:
    """LINE Flex Message 模板"""
    
    @staticmethod
    def welcome_message() -> dict:
        """歡迎訊息模板"""
        return {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://via.placeholder.com/1024x512/4A90A4/FFFFFF?text=貸款智能助理",
                "size": "full",
                "aspectRatio": "2:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "歡迎使用貸款智能助理",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#1DB446"
                    },
                    {
                        "type": "text",
                        "text": "我可以幫您快速申請貸款、試算額度",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📋 申請貸款",
                                "size": "sm"
                            },
                            {
                                "type": "text",
                                "text": "💰 試算額度",
                                "size": "sm",
                                "margin": "sm"
                            },
                            {
                                "type": "text",
                                "text": "❓ 常見問題",
                                "size": "sm",
                                "margin": "sm"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "message",
                            "label": "開始申請",
                            "text": "我想申請貸款"
                        },
                        "color": "#1DB446"
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "message",
                            "label": "了解更多",
                            "text": "說明"
                        },
                        "margin": "sm"
                    }
                ]
            }
        }
    
    @staticmethod
    def application_progress(profile: dict, missing_fields: List[str]) -> dict:
        """申請進度模板"""
        # 計算完成度
        total_fields = 7
        filled_fields = total_fields - len(missing_fields)
        progress_percent = int((filled_fields / total_fields) * 100)
        
        # 欄位名稱映射
        field_names = {
            "name": "姓名",
            "id": "身分證",
            "phone": "手機",
            "job": "職業",
            "income": "月收入",
            "loan_purpose": "貸款用途",
            "amount": "申請金額"
        }
        
        # 建立欄位狀態列表
        field_items = []
        for field, name in field_names.items():
            is_filled = profile.get(field) is not None
            icon = "✅" if is_filled else "⬜"
            value = profile.get(field, "-")
            
            # 隱藏敏感資訊
            if field == "id" and is_filled:
                value = f"{str(value)[:3]}****{str(value)[-2:]}"
            elif field == "phone" and is_filled:
                value = f"{str(value)[:4]}****{str(value)[-3:]}"
            elif field == "income" and is_filled:
                value = f"NT$ {value:,}"
            elif field == "amount" and is_filled:
                value = f"NT$ {value:,}"
            
            field_items.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": icon, "size": "sm", "flex": 1},
                    {"type": "text", "text": name, "size": "sm", "flex": 3, "color": "#555555"},
                    {"type": "text", "text": str(value) if is_filled else "-", "size": "sm", "flex": 5, "color": "#111111" if is_filled else "#AAAAAA", "align": "end"}
                ],
                "margin": "sm"
            })
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 申請進度",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": f"完成度 {progress_percent}%", "size": "sm", "color": "#555555"},
                                    {"type": "text", "text": f"{filled_fields}/{total_fields}", "size": "sm", "color": "#111111", "align": "end"}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "margin": "sm",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [],
                                        "backgroundColor": "#1DB446",
                                        "height": "6px",
                                        "width": f"{progress_percent}%"
                                    }
                                ],
                                "backgroundColor": "#E0E0E0",
                                "height": "6px",
                                "cornerRadius": "3px"
                            }
                        ]
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "contents": field_items
                    }
                ]
            }
        }
    
    @staticmethod
    def approval_result(
        decision: str,
        amount: int,
        rate: float = None,
        monthly_payment: int = None,
        term: int = 84
    ) -> dict:
        """審核結果模板"""
        
        is_approved = "PASS" in decision or "核准" in decision
        
        if is_approved:
            header_color = "#1DB446"
            header_text = "✅ 恭喜！初步審核通過"
            result_text = "您的貸款申請已初步核准"
        else:
            header_color = "#FF5551"
            header_text = "❌ 審核未通過"
            result_text = "很抱歉，本次申請未能通過審核"
        
        contents = [
            {
                "type": "text",
                "text": header_text,
                "weight": "bold",
                "size": "lg",
                "color": header_color
            },
            {
                "type": "text",
                "text": result_text,
                "size": "sm",
                "color": "#666666",
                "margin": "md",
                "wrap": True
            },
            {
                "type": "separator",
                "margin": "lg"
            }
        ]
        
        if is_approved:
            detail_items = [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "核准金額", "size": "sm", "color": "#555555", "flex": 2},
                        {"type": "text", "text": f"NT$ {amount:,}", "size": "sm", "color": "#111111", "align": "end", "flex": 3, "weight": "bold"}
                    ]
                }
            ]
            
            if rate:
                detail_items.append({
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": "年利率", "size": "sm", "color": "#555555", "flex": 2},
                        {"type": "text", "text": f"{rate:.2f}%", "size": "sm", "color": "#111111", "align": "end", "flex": 3}
                    ]
                })
            
            if monthly_payment:
                detail_items.append({
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": "月付金額", "size": "sm", "color": "#555555", "flex": 2},
                        {"type": "text", "text": f"NT$ {monthly_payment:,}", "size": "sm", "color": "#111111", "align": "end", "flex": 3}
                    ]
                })
            
            detail_items.append({
                "type": "box",
                "layout": "horizontal",
                "margin": "sm",
                "contents": [
                    {"type": "text", "text": "貸款期數", "size": "sm", "color": "#555555", "flex": 2},
                    {"type": "text", "text": f"{term} 期", "size": "sm", "color": "#111111", "align": "end", "flex": 3}
                ]
            })
            
            contents.append({
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "contents": detail_items
            })
        
        footer_contents = []
        
        if is_approved:
            footer_contents.append({
                "type": "button",
                "style": "primary",
                "action": {
                    "type": "message",
                    "label": "確認申請",
                    "text": "確認申請"
                },
                "color": "#1DB446"
            })
        
        footer_contents.append({
            "type": "button",
            "style": "secondary",
            "action": {
                "type": "message",
                "label": "重新開始",
                "text": "重新開始"
            },
            "margin": "sm" if is_approved else None
        })
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": footer_contents
            }
        }
    
    @staticmethod
    def verification_mismatch(mismatches: List[tuple]) -> dict:
        """資料不符警示模板"""
        mismatch_items = []
        
        field_names = {
            "job": "職業",
            "income": "收入",
            "phone": "電話",
            "company": "公司"
        }
        
        for field, current, historical in mismatches:
            field_name = field_names.get(field, field)
            mismatch_items.append({
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    {"type": "text", "text": f"⚠️ {field_name}", "size": "sm", "color": "#FF5551", "weight": "bold"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "您填寫的:", "size": "xs", "color": "#888888", "flex": 2},
                            {"type": "text", "text": str(current), "size": "xs", "color": "#111111", "flex": 3}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "歷史紀錄:", "size": "xs", "color": "#888888", "flex": 2},
                            {"type": "text", "text": str(historical), "size": "xs", "color": "#111111", "flex": 3}
                        ]
                    }
                ]
            })
        
        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🔍 資料驗證結果",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FF9800"
                    },
                    {
                        "type": "text",
                        "text": "部分資料與系統紀錄不符，請確認",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "contents": mismatch_items
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "message",
                            "label": "資料正確",
                            "text": "資料正確，請繼續審核"
                        },
                        "color": "#1DB446",
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "message",
                            "label": "修改資料",
                            "text": "我要修改資料"
                        },
                        "flex": 1,
                        "margin": "sm"
                    }
                ]
            }
        }


# ==========================================
# Quick Reply Templates
# ==========================================
class QuickReplyTemplates:
    """快速回覆模板"""
    
    @staticmethod
    def loan_purpose_options() -> List[dict]:
        """貸款用途選項"""
        purposes = [
            ("購車", "購車"),
            ("房屋裝修", "房屋裝修"),
            ("週轉金", "週轉金"),
            ("教育", "教育支出"),
            ("醫療", "醫療費用"),
            ("其他", "其他用途")
        ]
        
        return [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": label,
                    "text": text
                }
            }
            for label, text in purposes
        ]
    
    @staticmethod
    def amount_options() -> List[dict]:
        """金額選項"""
        amounts = [
            ("30萬", "30萬"),
            ("50萬", "50萬"),
            ("80萬", "80萬"),
            ("100萬", "100萬"),
            ("150萬", "150萬"),
            ("其他金額", "其他金額")
        ]
        
        return [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": label,
                    "text": text
                }
            }
            for label, text in amounts
        ]
    
    @staticmethod
    def yes_no_options() -> List[dict]:
        """是/否選項"""
        return [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "是",
                    "text": "是"
                }
            },
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "否",
                    "text": "否"
                }
            }
        ]
    
    @staticmethod
    def confirm_options() -> List[dict]:
        """確認選項"""
        return [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "確認",
                    "text": "確認"
                }
            },
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "修改",
                    "text": "我要修改"
                }
            },
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "取消",
                    "text": "取消申請"
                }
            }
        ]


# ==========================================
# Rich Menu Configuration
# ==========================================
RICH_MENU_CONFIG = {
    "size": {
        "width": 2500,
        "height": 843
    },
    "selected": True,
    "name": "貸款助理選單",
    "chatBarText": "選單",
    "areas": [
        {
            "bounds": {
                "x": 0,
                "y": 0,
                "width": 833,
                "height": 843
            },
            "action": {
                "type": "message",
                "text": "我想申請貸款"
            }
        },
        {
            "bounds": {
                "x": 833,
                "y": 0,
                "width": 834,
                "height": 843
            },
            "action": {
                "type": "message",
                "text": "查詢申請進度"
            }
        },
        {
            "bounds": {
                "x": 1667,
                "y": 0,
                "width": 833,
                "height": 843
            },
            "action": {
                "type": "message",
                "text": "說明"
            }
        }
    ]
}


# ==========================================
# LINE Message Builder
# ==========================================
class LineMessageBuilder:
    """LINE 訊息建構器"""
    
    @staticmethod
    def build_flex_message(alt_text: str, contents: dict) -> dict:
        """建構 Flex Message"""
        return {
            "type": "flex",
            "altText": alt_text,
            "contents": contents
        }
    
    @staticmethod
    def build_text_with_quick_reply(text: str, quick_reply_items: List[dict]) -> dict:
        """建構帶有快速回覆的文字訊息"""
        return {
            "type": "text",
            "text": text,
            "quickReply": {
                "items": quick_reply_items
            }
        }
    
    @staticmethod
    def build_response_for_stage(result: dict) -> List[dict]:
        """根據處理結果建構回應訊息"""
        messages = []
        
        stage = result.get("stage", "")
        response = result.get("response", "")
        next_step = result.get("next_step", "")
        profile = result.get("profile", {})
        missing_fields = result.get("missing_fields", [])
        expert_result = result.get("expert_result", {})
        
        # 主要回應文字
        messages.append({
            "type": "text",
            "text": response
        })
        
        # 根據階段添加額外訊息
        if stage == "CONVERSATION" and missing_fields:
            # 顯示進度 (每 3 個欄位顯示一次)
            filled_count = 7 - len(missing_fields)
            if filled_count > 0 and filled_count % 3 == 0:
                progress_flex = FlexTemplates.application_progress(profile, missing_fields)
                messages.append(LineMessageBuilder.build_flex_message(
                    "申請進度",
                    progress_flex
                ))
            
            # 根據下一個欄位添加快速回覆
            next_field = missing_fields[0] if missing_fields else None
            if next_field == "loan_purpose":
                messages[-1] = LineMessageBuilder.build_text_with_quick_reply(
                    response,
                    QuickReplyTemplates.loan_purpose_options()
                )
            elif next_field == "amount":
                messages[-1] = LineMessageBuilder.build_text_with_quick_reply(
                    response,
                    QuickReplyTemplates.amount_options()
                )
        
        # 審核結果
        elif next_step in ["CASE_CLOSED_SUCCESS", "CASE_CLOSED_REJECT"]:
            financial_metrics = expert_result.get("financial_metrics", {})
            
            result_flex = FlexTemplates.approval_result(
                decision=next_step,
                amount=profile.get("amount", 0),
                rate=financial_metrics.get("rate"),
                monthly_payment=financial_metrics.get("monthly_payment"),
                term=84
            )
            messages.append(LineMessageBuilder.build_flex_message(
                "審核結果",
                result_flex
            ))
        
        # 資料不符
        elif next_step == "FORCE_LDE_CLARIFY":
            mismatches = expert_result.get("dve_raw_report", {}).get("mismatches", [])
            if mismatches:
                mismatch_flex = FlexTemplates.verification_mismatch(mismatches)
                messages.append(LineMessageBuilder.build_flex_message(
                    "資料驗證結果",
                    mismatch_flex
                ))
        
        return messages


# ==========================================
# Notification Service
# ==========================================
class LineNotificationService:
    """LINE 推播通知服務"""
    
    def __init__(self, line_api):
        self.line_api = line_api
    
    def send_application_received(self, user_id: str, application_id: str):
        """發送申請已收到通知"""
        message = f"""📩 您的貸款申請已收到

申請編號：{application_id}
狀態：審核中

我們會在 1-3 個工作天內完成審核，届時會再通知您結果。

如有任何問題，請隨時詢問我！"""
        
        self._push_message(user_id, message)
    
    def send_approval_notification(self, user_id: str, amount: int, rate: float):
        """發送核准通知"""
        message = f"""🎉 恭喜！您的貸款已核准

核准金額：NT$ {amount:,}
年利率：{rate:.2f}%

請點選下方按鈕完成後續申請流程。"""
        
        self._push_message(user_id, message)
    
    def send_rejection_notification(self, user_id: str, reason: str = None):
        """發送拒絕通知"""
        message = """很抱歉，您的貸款申請未能通過審核。

如有任何疑問，歡迎聯繫我們的客服專線。

您也可以在改善相關條件後，再次提出申請。"""
        
        if reason:
            message += f"\n\n原因：{reason}"
        
        self._push_message(user_id, message)
    
    def _push_message(self, user_id: str, message: str):
        """發送推播訊息"""
        if not self.line_api:
            logger.warning("LINE API not available for push message")
            return
        
        try:
            from linebot.v3.messaging import PushMessageRequest, TextMessage
            
            self.line_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
            )
            logger.info(f"Push message sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send push message: {e}")
