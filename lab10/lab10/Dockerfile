FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    PIP_NO_CACHE_DIR=1

# libgomp1 потрібен для faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Встановлюємо CPU-версію PyTorch окремо, щоб образ не завантажував CUDA-залежності (~2+ ГБ)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install -r requirements.txt

COPY . .
RUN chmod +x scripts/run_all.sh

CMD ["bash", "scripts/run_all.sh"]
