import torch
import redis
import sys
import os

# 確保能讀到 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_infra():
    print("=== 1. Checking GPU (CUDA) ===")
    if torch.cuda.is_available():
        print(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
        print(f"✅ CUDA Version: {torch.version.cuda}")
    else:
        print("❌ GPU Not Found! 模型將無法使用加速功能。")

    print("\n=== 2. Checking Redis Connection ===")
    try:
        r = redis.Redis(host='localhost', port=6379, socket_timeout=3)
        if r.ping():
            print("✅ Redis is ALIVE (PONG)")
        else:
            print("❌ Redis ping failed.")
    except Exception as e:
        print(f"❌ Redis Connection Error: {e}")
        print("提示: 請嘗試執行 'sudo service redis-server start'")

if __name__ == "__main__":
    test_infra()