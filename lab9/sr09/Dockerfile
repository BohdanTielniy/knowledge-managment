FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install --upgrade pip && pip install "neo4j>=5.20,<6.0" "requests>=2.31"
COPY . .

CMD ["python3", "src/bench.py"]
