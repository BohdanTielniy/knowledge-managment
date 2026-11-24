#!/usr/bin/env python3
"""
ЛР 11, Результат 3: FastAPI REST API для гібридного RAG + Graph чат-бота.

Ендпоінти:
  - GET  /health               — стан сервісу, корпусу та графа знань
  - POST /ask                  — запитання -> відповідь, цитати, джерела, токени, затримка
  - GET  /sources/{source_id}  — отримання повного фрагмента або вузла з перевіркою sensitivity

Безпека:
  - Автентифікація через X-API-Key (2 ролі: public_user та forester_admin)
  - Role-based pre-filter за sensitivity (403 Forbidden при спробі доступу до restricted/internal)
  - Rate limiting per API-key (429 Too Many Requests)
  - Pydantic-валідація входу (422 Unprocessable Entity)

Запуск: uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
import os
import sys
import time
from collections import defaultdict, deque
from typing import List, Optional
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from rag import RAGPipeline, ROLE_SENSITIVITY

API_KEYS = {
    os.environ.get("API_KEY_PUBLIC", "demo-public-key"): "public_user",
    os.environ.get("API_KEY_ADMIN", "demo-admin-key"): "forester_admin",
}
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
_rate_buckets = defaultdict(deque)

app = FastAPI(
    title="Domain Knowledge Hub — Forest Management RAG + Graph API",
    version="1.0.0",
    description="REST API гібридного сховища знань (BM25 + Dense + RRF + Reranker + Neo4j GraphRAG) для ПдО «Управління лісовими продуктами».",
)

pipeline = RAGPipeline()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="Запитання користувача")
    use_graph: bool = Field(True, description="Додавати лінеаризований підграф знань у контекст")
    top_k: int = Field(5, ge=1, le=10, description="Кількість текстових фрагментів контексту")


class SourceItem(BaseModel):
    id: str
    doc_id: str
    sensitivity: str
    score: float


class AskResponse(BaseModel):
    question: str
    role: str
    answer: str
    abstained: bool
    citations: List[str]
    citations_valid: bool
    sources: List[SourceItem]
    graph_entities: List[str]
    total_tokens: int
    latency_ms: float
    cost_usd: float


def authenticate_and_rate_limit(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> str:
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний або відсутній API-ключ (передайте заголовок X-API-Key).",
        )
    now = time.time()
    bucket = _rate_buckets[x_api_key]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Перевищено ліміт запитів ({RATE_LIMIT_PER_MIN} запитів/хв). Спробуйте пізніше.",
        )
    bucket.append(now)
    return API_KEYS[x_api_key]


@app.get("/health", summary="Перевірка стану сервісу")
def health():
    return {
        "status": "ok",
        "corpus_chunks": len(pipeline.corpus),
        "graph_nodes": len(pipeline.kg.nodes),
        "llm_provider": pipeline.llm.provider,
        "rate_limit_per_min": RATE_LIMIT_PER_MIN,
    }


@app.post("/ask", response_model=AskResponse, summary="Поставити запитання гібридному RAG-чат-боту")
def ask_question(req: AskRequest, role: str = Depends(authenticate_and_rate_limit)):
    rec = pipeline.ask(
        query=req.question,
        role=role,
        top_k=req.top_k,
        use_graph=req.use_graph,
    )
    return AskResponse(
        question=rec["query"],
        role=rec["role"],
        answer=rec["answer"],
        abstained=rec["abstained"],
        citations=rec["citations"],
        citations_valid=rec["citations_valid"],
        sources=[SourceItem(**s) for s in rec["sources"]],
        graph_entities=rec["graph_entities"],
        total_tokens=rec["total_tokens"],
        latency_ms=rec["latency_ms"],
        cost_usd=rec["cost_usd"],
    )


@app.get("/sources/{source_id}", summary="Отримати повний текст джерела або вузла графа за ID")
def get_source(source_id: str, role: str = Depends(authenticate_and_rate_limit)):
    allowed = ROLE_SENSITIVITY.get(role, {"public"})
    if source_id in pipeline.corpus_by_id:
        rec = pipeline.corpus_by_id[source_id]
        if rec["sensitivity"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ заборонено: джерело {source_id} має рівень '{rec['sensitivity']}', роль '{role}' не має прав.",
            )
        return rec
    if source_id in pipeline.kg.nodes:
        if role == "public_user" and source_id.startswith(("Forester_", "Quota_2026_V102")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ до вузла {source_id} обмежено для ролі '{role}'.",
            )
        return {"node_id": source_id, "properties": pipeline.kg.nodes[source_id]}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Джерело '{source_id}' не знайдено.")
