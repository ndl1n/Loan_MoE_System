"""
Loan MoE System - FastAPI 應用程式
提供 REST API 和 LINE Bot Webhook

API 端點:
- POST /api/v1/chat - 對話 API
- POST /api/v1/webhook/line - LINE Bot Webhook
- GET /api/v1/health - 健康檢查
- GET /api/v1/session/{user_id} - 取得 session 資訊
- DELETE /api/v1/session/{user_id} - 重置 session
"""

import os
import logging
import hashlib
import hmac
import base64
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# LINE Bot SDK
try:
    from linebot.v3 import WebhookHandler
    from linebot.v3.messaging import (
        Configuration,
        ApiClient,
        MessagingApi,
        ReplyMessageRequest,
        PushMessageRequest,
        TextMessage,
        FlexMessage,
        FlexContainer
    )
    from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, UnfollowEvent
    from linebot.v3.exceptions import InvalidSignatureError
    LINEBOT_AVAILABLE = True
except ImportError:
    LINEBOT_AVAILABLE = False
    WebhookHandler = None

from main import LoanMoESystem
from config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    API_HOST,
    API_PORT,
    DEBUG_MODE
)

# ==========================================
# Logging Setup
# ==========================================
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# Global Instances
# ==========================================
loan_system: Optional[LoanMoESystem] = None
line_handler: Optional[WebhookHandler] = None
line_api: Optional['MessagingApi'] = None


# ==========================================
# Lifespan Management
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global loan_system, line_handler, line_api
    
    # Startup
    logger.info("🚀 啟動 Loan MoE API Server...")
    
    # 初始化 Loan System
    loan_system = LoanMoESystem()
    logger.info("✅ Loan MoE System 初始化完成")
    
    # 初始化 LINE Bot (如果有設定)
    if LINEBOT_AVAILABLE and LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN:
        try:
            line_handler = WebhookHandler(LINE_CHANNEL_SECRET)
            
            configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
            api_client = ApiClient(configuration)
            line_api = MessagingApi(api_client)
            
            logger.info("✅ LINE Bot 初始化完成")
            
            # 註冊 LINE 事件處理器
            register_line_handlers()
            
        except Exception as e:
            logger.warning(f"⚠️ LINE Bot 初始化失敗: {e}")
            line_handler = None
            line_api = None
    else:
        logger.warning("⚠️ LINE Bot 未設定或 SDK 未安裝")
    
    yield
    
    # Shutdown
    logger.info("👋 關閉 Loan MoE API Server...")


# ==========================================
# FastAPI App
# ==========================================
app = FastAPI(
    title="Loan MoE System API",
    description="貸款審核 Mixture of Experts 系統 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG_MODE else None,
    redoc_url="/redoc" if DEBUG_MODE else None
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境請限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Models
# ==========================================
class ChatRequest(BaseModel):
    """對話請求"""
    user_id: str = Field(..., description="使用者 ID", min_length=1)
    message: str = Field(..., description="使用者訊息", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "U1234567890",
                "message": "我想申請貸款"
            }
        }


class ChatResponse(BaseModel):
    """對話回應"""
    success: bool
    stage: str
    expert: Optional[str]
    response: str
    profile: dict
    missing_fields: list = []
    next_step: str
    routing_info: Optional[dict] = None


class SessionInfo(BaseModel):
    """Session 資訊"""
    user_id: str
    profile: dict
    history_length: int
    verification_status: Optional[str]
    created_at: Optional[float]


class HealthResponse(BaseModel):
    """健康檢查回應"""
    status: str
    version: str
    services: dict


# ==========================================
# API Endpoints
# ==========================================
@app.get("/", tags=["Root"])
async def root():
    """根路徑"""
    return {
        "name": "Loan MoE System API",
        "version": "1.0.0",
        "docs": "/docs" if DEBUG_MODE else "disabled"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """健康檢查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "loan_system": loan_system is not None,
            "line_bot": line_handler is not None,
            "redis": check_redis_connection(),
            "mongodb": check_mongodb_connection()
        }
    )


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    對話 API - 處理使用者訊息
    
    這是主要的對話入口，適用於:
    - 自建前端整合
    - 其他聊天平台整合
    - 測試和開發
    """
    if not loan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        result = loan_system.process_message(request.user_id, request.message)
        
        return ChatResponse(
            success=True,
            stage=result.get("stage", "UNKNOWN"),
            expert=result.get("expert"),
            response=result.get("response", ""),
            profile=result.get("profile", {}),
            missing_fields=result.get("missing_fields", []),
            next_step=result.get("next_step", ""),
            routing_info=result.get("routing_info")
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/session/{user_id}", response_model=SessionInfo, tags=["Session"])
async def get_session(user_id: str):
    """取得使用者 Session 資訊"""
    if not loan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        conv_mgr = loan_system._get_conversation_manager(user_id)
        profile = conv_mgr.session_mgr.get_profile()
        session_info = conv_mgr.session_mgr.get_session_info()
        
        return SessionInfo(
            user_id=user_id,
            profile=profile,
            history_length=session_info.get("history_length", 0),
            verification_status=profile.get("verification_status"),
            created_at=profile.get("created_at")
        )
    
    except Exception as e:
        logger.error(f"Get session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/session/{user_id}", tags=["Session"])
async def reset_session(user_id: str):
    """重置使用者 Session"""
    if not loan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        loan_system.reset_user_session(user_id)
        return {"success": True, "message": f"Session for {user_id} has been reset"}
    
    except Exception as e:
        logger.error(f"Reset session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# LINE Bot Webhook
# ==========================================
@app.post("/api/v1/webhook/line", tags=["LINE Bot"])
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None)
):
    """
    LINE Bot Webhook 端點
    
    接收 LINE Platform 的事件並處理
    """
    if not LINEBOT_AVAILABLE:
        raise HTTPException(status_code=501, detail="LINE Bot SDK not installed")
    
    if not line_handler:
        raise HTTPException(status_code=503, detail="LINE Bot not configured")
    
    body = await request.body()
    body_str = body.decode('utf-8')
    
    logger.debug(f"LINE Webhook received: {body_str[:200]}...")
    
    # 驗證簽名
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")
    
    try:
        line_handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.error("Invalid LINE signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"LINE webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"status": "ok"}


def register_line_handlers():
    """註冊 LINE 事件處理器"""
    if not line_handler:
        return
    
    @line_handler.add(MessageEvent, message=TextMessageContent)
    def handle_text_message(event: MessageEvent):
        """處理文字訊息"""
        user_id = event.source.user_id
        message_text = event.message.text
        reply_token = event.reply_token
        
        logger.info(f"LINE Message from {user_id}: {message_text[:50]}...")
        
        try:
            # 處理特殊指令
            if message_text.lower() in ['重新開始', 'reset', '重設']:
                loan_system.reset_user_session(user_id)
                reply_text = "🔄 對話已重置！\n\n請問有什麼可以幫您的呢？"
            
            elif message_text.lower() in ['說明', 'help', '幫助']:
                reply_text = get_help_message()
            
            else:
                # 正常對話處理
                result = loan_system.process_message(user_id, message_text)
                reply_text = format_line_response(result)
            
            # 回覆訊息
            line_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        
        except Exception as e:
            logger.error(f"LINE message handling error: {e}", exc_info=True)
            
            # 錯誤回覆
            line_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text="抱歉，系統發生錯誤，請稍後再試。")]
                )
            )
    
    @line_handler.add(FollowEvent)
    def handle_follow(event: FollowEvent):
        """處理加好友事件"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        logger.info(f"New follower: {user_id}")
        
        welcome_message = """👋 歡迎使用貸款智能助理！

我可以幫您：
📋 申請貸款
💰 試算額度與利率
❓ 回答貸款相關問題

請直接輸入您的需求，例如：
「我想申請貸款」
「利率多少？」
「我的條件可以貸多少？」

輸入「說明」查看更多資訊"""
        
        line_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=welcome_message)]
            )
        )
    
    @line_handler.add(UnfollowEvent)
    def handle_unfollow(event: UnfollowEvent):
        """處理取消好友事件"""
        user_id = event.source.user_id
        logger.info(f"User unfollowed: {user_id}")
        
        # 清除使用者資料
        try:
            loan_system.reset_user_session(user_id)
        except:
            pass


def format_line_response(result: dict) -> str:
    """格式化 LINE 回應訊息"""
    response = result.get("response", "")
    stage = result.get("stage", "")
    expert = result.get("expert", "")
    next_step = result.get("next_step", "")
    
    # 添加狀態標記
    if stage == "CONVERSATION":
        prefix = "📝 "
    elif expert == "LDE":
        prefix = "💬 "
    elif expert == "DVE":
        prefix = "🔍 "
    elif expert == "FRE":
        prefix = "💰 "
    else:
        prefix = ""
    
    formatted = f"{prefix}{response}"
    
    # 添加案件結束提示
    if next_step == "CASE_CLOSED_SUCCESS":
        formatted += "\n\n✅ 恭喜！您的申請已初步核准。"
        formatted += "\n\n輸入「重新開始」可以開始新的申請。"
    elif next_step == "CASE_CLOSED_REJECT":
        formatted += "\n\n❌ 很抱歉，本次申請未能通過。"
        formatted += "\n\n輸入「重新開始」可以開始新的申請。"
    elif next_step == "HUMAN_HANDOVER":
        formatted += "\n\n📞 您的申請需要專人服務，我們會盡快與您聯繫。"
    
    return formatted


def get_help_message() -> str:
    """取得說明訊息"""
    return """📖 使用說明

🔹 申請貸款
直接告訴我您的需求，我會引導您完成申請流程。

🔹 所需資料
- 姓名
- 身分證字號
- 手機號碼
- 職業
- 月收入
- 貸款用途
- 申請金額

🔹 常用指令
• 「重新開始」- 重置對話
• 「說明」- 顯示此說明

🔹 注意事項
• 所有資料僅供審核使用
• 本系統為初步審核，最終結果以專人審核為準

有任何問題歡迎直接詢問！"""


# ==========================================
# Helper Functions
# ==========================================
def check_redis_connection() -> bool:
    """檢查 Redis 連線"""
    try:
        from conversation.user_session_manager import redis_client
        if redis_client:
            redis_client.ping()
            return True
    except:
        pass
    return False


def check_mongodb_connection() -> bool:
    """檢查 MongoDB 連線"""
    try:
        from services.database import MongoManager
        mongo = MongoManager()
        if mongo._client:
            mongo._client.admin.command('ping')
            return True
    except:
        pass
    return False


# ==========================================
# Error Handlers
# ==========================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 例外處理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般例外處理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )


# ==========================================
# Run Server
# ==========================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG_MODE,
        log_level="debug" if DEBUG_MODE else "info"
    )
