#!/bin/bash
# ============================================================
# Loan-MoE Docker 啟動腳本
# 適用於 WSL2 + NVIDIA GPU 環境
# ============================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輔助函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 顯示 Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║     🏦 Loan-MoE System - Docker Launcher                  ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 檢查前置需求
check_prerequisites() {
    log_info "檢查前置需求..."
    
    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝！請先安裝 Docker Desktop。"
        exit 1
    fi
    
    # 檢查 Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安裝！"
        exit 1
    fi
    
    # 檢查 .env 檔案
    if [ ! -f ".env" ]; then
        log_warning ".env 檔案不存在，正在從範例建立..."
        cp .env.example .env
        log_warning "請編輯 .env 檔案填入必要的 API Keys！"
        echo ""
        read -p "是否現在編輯 .env? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vim} .env
        fi
    fi
    
    log_success "前置需求檢查通過！"
}

# 檢查 GPU
check_gpu() {
    log_info "檢查 GPU 支援..."
    
    if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        log_success "NVIDIA GPU 可用！"
        GPU_AVAILABLE=true
    else
        log_warning "無法使用 GPU，將以 CPU 模式運行。"
        GPU_AVAILABLE=false
    fi
}

# 建置映像
build_image() {
    log_info "建置 Docker 映像..."
    
    if [ "$GPU_AVAILABLE" = true ]; then
        docker compose build
    else
        docker build -f Dockerfile.cpu -t loan-moe:cpu .
    fi
    
    log_success "映像建置完成！"
}

# 啟動服務
start_services() {
    log_info "啟動服務..."
    
    docker compose up -d
    
    # 等待服務就緒
    log_info "等待服務就緒..."
    sleep 5
    
    # 檢查服務狀態
    docker compose ps
    
    log_success "服務已啟動！"
}

# 顯示使用說明
show_usage() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}服務已就緒！以下是常用操作：${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "📌 進入互動模式："
    echo "   docker compose exec loan-moe python main.py"
    echo ""
    echo "📌 查看日誌："
    echo "   docker compose logs -f loan-moe"
    echo ""
    echo "📌 執行測試："
    echo "   docker compose exec loan-moe python run_tests.py"
    echo ""
    echo "📌 停止服務："
    echo "   docker compose down"
    echo ""
    echo "📌 Redis Web UI (需啟用 debug profile)："
    echo "   http://localhost:8081"
    echo ""
}

# 互動式選單
show_menu() {
    echo ""
    echo -e "${BLUE}請選擇操作：${NC}"
    echo "1) 啟動所有服務"
    echo "2) 啟動服務 + 進入互動模式"
    echo "3) 只建置映像"
    echo "4) 執行測試"
    echo "5) 停止所有服務"
    echo "6) 查看服務狀態"
    echo "7) 清理 Docker 資源"
    echo "0) 退出"
    echo ""
    read -p "請輸入選項 [0-7]: " choice
    
    case $choice in
        1)
            start_services
            show_usage
            ;;
        2)
            start_services
            log_info "進入互動模式..."
            docker compose exec loan-moe python main.py
            ;;
        3)
            build_image
            ;;
        4)
            log_info "執行測試..."
            docker compose --profile test up --abort-on-container-exit
            ;;
        5)
            log_info "停止服務..."
            docker compose down
            log_success "服務已停止！"
            ;;
        6)
            docker compose ps
            ;;
        7)
            log_warning "這將刪除未使用的 Docker 資源！"
            read -p "確定要繼續嗎? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker system prune -f
                log_success "清理完成！"
            fi
            ;;
        0)
            log_info "再見！"
            exit 0
            ;;
        *)
            log_error "無效的選項！"
            ;;
    esac
}

# 主程式
main() {
    show_banner
    
    # 切換到腳本所在目錄
    cd "$(dirname "$0")"
    
    check_prerequisites
    check_gpu
    
    # 如果有參數，直接執行對應操作
    case "${1:-}" in
        start)
            build_image
            start_services
            show_usage
            ;;
        stop)
            docker compose down
            log_success "服務已停止！"
            ;;
        build)
            build_image
            ;;
        test)
            docker compose --profile test up --abort-on-container-exit
            ;;
        logs)
            docker compose logs -f
            ;;
        shell)
            docker compose exec loan-moe bash
            ;;
        interactive)
            start_services
            docker compose exec loan-moe python main.py
            ;;
        *)
            # 無參數時顯示互動選單
            while true; do
                show_menu
            done
            ;;
    esac
}

# 執行主程式
main "$@"
