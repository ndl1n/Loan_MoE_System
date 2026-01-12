"""
測試 Conversation Manager 的範例腳本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversation.user_session_manager import UserSessionManager
from conversation.field_schema import FieldSchema
from conversation.gemini_client import GeminiClient
from conversation.conversation_manager import ConversationManager

import logging

# 設定詳細的 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_conversation_flow():
    """
    模擬完整對話流程
    """
    print("=" * 60)
    print("🧪 開始測試對話流程")
    print("=" * 60)
    
    # 初始化組件
    user_id = "test_user_001"
    session_mgr = UserSessionManager(user_id)
    field_schema = FieldSchema()
    gemini_client = GeminiClient()
    conv_mgr = ConversationManager(session_mgr, field_schema, gemini_client)
    
    # 清空舊資料
    session_mgr.clear_session()
    
    # === 情境 1: 標準流程 ===
    print("\n📋 情境 1: 標準問答流程")
    print("-" * 60)
    
    conversations = [
        ("王小明", "應該要抓到 name"),
        ("A123456789", "應該要抓到 id"),
        ("0912345678", "應該要抓到 phone"),
        ("軟體工程師", "應該要抓到 job"),
        ("月薪大概7萬", "應該要抓到 income=70000"),
        ("我想買車", "應該要抓到 loan_purpose"),
        ("想借50萬", "應該要抓到 amount=500000")
    ]
    
    for i, (user_input, expected) in enumerate(conversations, 1):
        print(f"\n{'='*60}")
        print(f"第 {i} 輪對話 - 期望: {expected}")
        print(f"{'='*60}")
        print(f"👤 使用者: {user_input}")
        
        # 處理對話
        result = conv_mgr.handle_turn(user_id, user_input)
        
        print(f"🤖 系統狀態: {result['status']}")
        print(f"🤖 系統回應: {result['response']}")
        
        # 顯示當前 profile
        profile = result['profile']
        print(f"\n📊 當前收集到的資料:")
        for key, value in profile.items():
            if value is not None and key not in ['last_asked_field', 'retry_count', 'created_at', 'updated_at']:
                print(f"   ✓ {key}: {value}")
        
        if result.get('missing_fields'):
            print(f"\n❌ 尚缺欄位: {result['missing_fields']}")
        
        # 如果完成收集,顯示摘要
        if result['status'] == 'READY_FOR_MOE':
            print(f"\n✅ 資料收集完成!")
            print(f"📋 完整資料:")
            for key, value in result['summary'].items():
                print(f"   - {key}: {value}")
            break
    
    # 顯示對話歷史
    print(f"\n{'='*60}")
    print("📜 完整對話歷史")
    print(f"{'='*60}")
    history = session_mgr.get_history(limit=20)
    for msg in history:
        role_symbol = "👤" if msg["role"] == "user" else "🤖"
        print(f"{role_symbol} {msg['role']}: {msg['content']}")
    
    # 顯示 Session 資訊
    print(f"\n{'='*60}")
    print("ℹ️  Session 資訊")
    print(f"{'='*60}")
    session_info = session_mgr.get_session_info()
    for key, value in session_info.items():
        print(f"   - {key}: {value}")
    
    return session_mgr


def test_edge_cases():
    """
    測試邊緣案例
    """
    print("\n" + "=" * 60)
    print("🧪 測試邊緣案例")
    print("=" * 60)
    
    user_id = "test_user_002"
    session_mgr = UserSessionManager(user_id)
    field_schema = FieldSchema()
    gemini_client = GeminiClient()
    conv_mgr = ConversationManager(session_mgr, field_schema, gemini_client)
    
    session_mgr.clear_session()
    
    # 測試案例
    test_cases = [
        {
            "input": "我叫王大明,身分證 A123456789",
            "description": "一次提供多個欄位",
            "expected": "name + id"
        },
        {
            "input": "0912-345-678",
            "description": "回答電話 (帶破折號)",
            "expected": "phone"
        },
        {
            "input": "工程師",
            "description": "回答職業",
            "expected": "job"
        },
        {
            "input": "月薪 5 萬多",
            "description": "模糊金額表達",
            "expected": "income=50000"
        },
        {
            "input": "買車用",
            "description": "回答貸款用途",
            "expected": "loan_purpose"
        },
        {
            "input": "50萬左右",
            "description": "模糊貸款金額",
            "expected": "amount=500000"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 測試案例 {i}: {case['description']} ---")
        print(f"👤 輸入: {case['input']}")
        print(f"📝 期望: {case['expected']}")
        
        result = conv_mgr.handle_turn(user_id, case['input'])
        
        print(f"🤖 狀態: {result['status']}")
        print(f"🤖 回應: {result['response']}")
        
        # 顯示目前抓到的資料
        profile = result['profile']
        collected = {k: v for k, v in profile.items() 
                    if v is not None and k not in ['last_asked_field', 'retry_count', 'created_at', 'updated_at']}
        if collected:
            print(f"✓ 已收集: {collected}")
    
    print(f"\n✅ 邊緣案例測試完成")
    print(f"📊 最終 Profile: {session_mgr.get_profile()}")


def test_validation():
    """
    測試欄位驗證功能
    """
    print("\n" + "=" * 60)
    print("🧪 測試欄位驗證")
    print("=" * 60)
    
    schema = FieldSchema()
    
    test_data = {
        "name": "王小明",
        "id": "A123456789",
        "phone": "0912345678",
        "job": "工程師",
        "income": 70000,
        "loan_purpose": "購車",
        "amount": 500000
    }
    
    print("\n✅ 正確資料驗證:")
    results = schema.validate_all(test_data)
    for field, info in results.items():
        status = "✓" if info["valid"] else "✗"
        print(f"   {status} {field}: {info}")
    
    # 測試錯誤資料
    print("\n❌ 錯誤資料驗證:")
    error_data = {
        "name": "王小明",
        "id": "123",  # 格式錯誤
        "phone": "123456",  # 格式錯誤
        "income": -1000,  # 負數
    }
    
    errors = schema.get_validation_errors(error_data)
    for field, error_msg in errors.items():
        print(f"   ✗ {field}: {error_msg}")


if __name__ == "__main__":
    try:
        # 執行測試
        test_conversation_flow()
        test_edge_cases()
        test_validation()
        
        print("\n" + "=" * 60)
        print("✅ 所有測試完成!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"測試失敗: {e}", exc_info=True)