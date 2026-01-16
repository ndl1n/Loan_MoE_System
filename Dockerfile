# ============================================================
# Loan-MoE System Dockerfile
# Optimized for WSL2 + NVIDIA GPU
# ============================================================

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set timezone
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    python3.10-dev \
    git \
    curl \
    wget \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ============================================================
# Stage 2: Dependencies installation
# ============================================================
FROM base AS dependencies

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install PyTorch with CUDA 11.8 support
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages for development
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    ipython \
    jupyter

# ============================================================
# Stage 3: Production image
# ============================================================
FROM dependencies AS production

WORKDIR /app

# Create non-root user for security
RUN groupadd -r loanmoe && useradd -r -g loanmoe loanmoe

# Copy application code
COPY --chown=loanmoe:loanmoe . .

# Create necessary directories
RUN mkdir -p /app/models/LDE_adapter \
             /app/models/DVE_adapter \
             /app/models/FRE_adapter \
             /app/moe/models \
             /app/logs \
    && chown -R loanmoe:loanmoe /app

# Set environment variables
ENV PYTHONPATH=/app
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers

# Expose port (if using Flask/FastAPI later)
EXPOSE 8000

# Switch to non-root user
USER loanmoe

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; print(torch.cuda.is_available())" || exit 1

# Default command
CMD ["python", "main.py"]

# ============================================================
# Stage 4: Development image (optional)
# ============================================================
FROM production AS development

USER root

# Install development tools
RUN pip install --no-cache-dir \
    black \
    flake8 \
    mypy \
    pre-commit

# Switch back to non-root user
USER loanmoe

# Override command for development
CMD ["bash"]
