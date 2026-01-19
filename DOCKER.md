# 🐳 Docker 部署指南

本指南說明如何在 **WSL2 + NVIDIA GPU** 環境中使用 Docker 部署 Loan-MoE 系統。

---

## 📋 目錄

- [前置需求](#前置需求)
- [WSL2 GPU 設定](#wsl2-gpu-設定)
- [快速開始](#快速開始)
- [Docker Compose 使用](#docker-compose-使用)
- [常用指令](#常用指令)
- [故障排除](#故障排除)

---

## 前置需求

### 1. Windows 系統需求
- Windows 10 版本 21H2 或更新 / Windows 11
- 已啟用 WSL2
- NVIDIA GPU (支援 CUDA)

### 2. 軟體需求
```bash
# 檢查 WSL2 版本
wsl --version

# 檢查 Docker 版本
docker --version
docker compose version
```

需要:
- Docker Desktop 4.x+ (with WSL2 backend)
- NVIDIA Driver 525+ (Windows 端)
- NVIDIA Container Toolkit (WSL2 端)

---

## WSL2 GPU 設定

### Step 1: 安裝 NVIDIA Driver (Windows 端)

下載並安裝最新的 NVIDIA 驅動程式:
https://www.nvidia.com/Download/index.aspx

**重要:** 只需在 Windows 安裝驅動，**不要**在 WSL2 內安裝驅動。

### Step 2: 安裝 NVIDIA Container Toolkit (WSL2 端)

```bash
# 進入 WSL2
wsl

# 添加 NVIDIA 套件庫
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 安裝
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 重新啟動 Docker
sudo systemctl restart docker
```

### Step 3: 驗證 GPU 可用

```bash
# 測試 nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

如果看到 GPU 資訊，表示設定成功！

---

## 快速開始

### 方法 1: 使用 Docker Compose (推薦)

```bash
# 1. 進入專案目錄
cd Loan_Moe_System

# 2. 複製環境變數檔案
cp .env.example .env

# 3. 編輯 .env 填入 API Keys
vim .env

# 4. 建置並啟動
docker compose up -d

# 5. 查看日誌
docker compose logs -f loan-moe

# 6. 進入互動模式
docker compose exec loan-moe python main.py
```

### 方法 2: 直接使用 Docker

```bash
# 建置映像檔
docker build -t loan-moe:latest .

# 執行 (含 GPU)
docker run -it --rm \
    --gpus all \
    -v $(pwd)/models:/app/models:ro \
    -v $(pwd)/.env:/app/.env:ro \
    --network host \
    loan-moe:latest
```

---

## Docker Compose 使用

### 服務說明

| 服務 | 說明 | Port |
|------|------|------|
| `loan-moe` | 主應用程式 | 8000 |
| `redis` | Session 管理 | 6379 |
| `redis-commander` | Redis Web UI (debug) | 8081 |
| `jupyter` | 開發用 Notebook (dev) | 8888 |
| `test` | 測試服務 (test) | - |

### 啟動不同配置

```bash
# 只啟動核心服務 (loan-moe + redis)
docker compose up -d

# 啟動 + Redis Web UI
docker compose --profile debug up -d

# 啟動 + Jupyter Notebook
docker compose --profile dev up -d

# 執行測試
docker compose --profile test up

# 啟動所有服務
docker compose --profile debug --profile dev up -d
```

### 停止服務

```bash
# 停止所有服務
docker compose down

# 停止並刪除 volumes
docker compose down -v

# 停止特定服務
docker compose stop loan-moe
```

---

## 常用指令

### 容器管理

```bash
# 查看執行中的容器
docker compose ps

# 查看日誌
docker compose logs -f loan-moe
docker compose logs -f redis

# 進入容器
docker compose exec loan-moe bash

# 重啟服務
docker compose restart loan-moe
```

### 開發與測試

```bash
# 執行測試
docker compose exec loan-moe python run_tests.py

# 執行特定測試
docker compose exec loan-moe python -m pytest tests/unit/ -v

# 進入 Python 互動模式
docker compose exec loan-moe python

# 檢查 GPU 狀態
docker compose exec loan-moe python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

### 建置與更新

```bash
# 重新建置 (程式碼更新後)
docker compose build --no-cache

# 拉取最新基礎映像
docker compose pull

# 更新並重啟
docker compose up -d --build
```

### 清理

```bash
# 刪除未使用的映像
docker image prune -f

# 刪除未使用的 volumes
docker volume prune -f

# 完全清理
docker system prune -a --volumes
```

---

## 故障排除

### 問題 1: GPU 無法使用

**症狀:**
```
RuntimeError: No CUDA GPUs are available
```

**解決方案:**
```bash
# 1. 確認 Windows NVIDIA 驅動已安裝
nvidia-smi  # 在 PowerShell 執行

# 2. 確認 WSL2 可以看到 GPU
wsl
nvidia-smi  # 在 WSL2 執行

# 3. 確認 Docker 有 GPU 支援
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# 4. 重啟 Docker Desktop
# 在 Windows 系統匣右鍵 Docker → Restart
```

### 問題 2: Redis 連線失敗

**症狀:**
```
redis.exceptions.ConnectionError: Error connecting to redis:6379
```

**解決方案:**
```bash
# 確認 Redis 容器運行中
docker compose ps redis

# 檢查 Redis 健康狀態
docker compose exec redis redis-cli ping

# 重啟 Redis
docker compose restart redis
```

### 問題 3: 記憶體不足 (OOM)

**症狀:**
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**解決方案:**
```bash
# 1. 減少 batch size 或使用 CPU
# 編輯 .env
ENABLE_FINETUNED_MODELS=False

# 2. 或增加 WSL2 記憶體限制
# 編輯 C:\Users\<username>\.wslconfig
[wsl2]
memory=16GB
swap=8GB
```

### 問題 4: 模型載入失敗

**症狀:**
```
FileNotFoundError: models/LDE_adapter not found
```

**解決方案:**
```bash
# 確認模型檔案已放置
ls -la models/

# 確認 volume 掛載正確
docker compose exec loan-moe ls -la /app/models/
```

### 問題 5: Permission Denied

**症狀:**
```
PermissionError: [Errno 13] Permission denied
```

**解決方案:**
```bash
# 修正檔案權限
sudo chown -R 1000:1000 ./models ./logs

# 或在 docker-compose.yml 中使用 root (不建議)
# user: root
```

---

## 📁 檔案結構

```
Loan_Moe_System/
├── Dockerfile              # GPU 版本 (主要)
├── Dockerfile.cpu          # CPU 版本
├── docker-compose.yml      # Docker Compose 配置
├── .dockerignore           # Docker 忽略檔案
├── DOCKER.md               # 本說明文件
├── .env.example            # 環境變數範例
└── ...
```

---

## 🔧 進階配置

### 自訂 GPU 配置

```yaml
# docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1           # GPU 數量
          device_ids: ['0']  # 指定 GPU ID
          capabilities: [gpu]
```

### 自訂資源限制

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 16G
    reservations:
      cpus: '2'
      memory: 8G
```

### 使用外部 MongoDB

```bash
# .env
MONGODB_URI=mongodb+srv://user:pass@your-cluster.mongodb.net/
```

---

## 📚 參考資源

- [Docker Desktop WSL2 Backend](https://docs.docker.com/desktop/wsl/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [Docker Compose GPU Support](https://docs.docker.com/compose/gpu-support/)

---

<div align="center">

**Happy Dockerizing! 🐳**

</div>
