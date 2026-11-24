#!/usr/bin/env python3
"""
3 реальні read-only інструменти над гібридним сховищем Domain Knowledge Hub:
  1. search_forest_docs    — гібридний пошук по корпусу ЛР 11 (read-only, RBAC).
  2. query_knowledge_graph — пошук вузлів і альтернатив конфліктів у графі ЛР 14 (read-only).
  3. query_olap_metric     — обчислення затверджених метрик семантичного шару ЛР 12 (read-only, AST).
"""
import json
import os
import re
import sqlite3
import sys
import time

LAB11_DIR = "/working_dir/c_e29ea41a69b8cab6/work_lab11/lab11"
LAB12_DIR = "/working_dir/c_e29ea41a69b8cab6/work_lab12/lab12"
LAB14_DIR = "/working_dir/c_e29ea41a69b8cab6/work_lab14/lab14"

sys.path.insert(0, os.path.join(LAB11_DIR, "src"))
sys.path.insert(0, os.path.join(LAB12_DIR, "src"))

import rag as lab11_rag
import semantic_layer as lab12_sem
import text_to_sql as lab12_t2sql

_RAG_ENGINE = None
_KB_NODES = None
_KB_ALTS = None


def _get_rag():
    global _RAG_ENGINE
    if _RAG_ENGINE is None:
        _RAG_ENGINE = lab11_rag.RAGPipeline()
    return _RAG_ENGINE


def _get_kb():
    global _KB_NODES, _KB_ALTS
    if _KB_NODES is None:
        _KB_NODES = json.load(open(os.path.join(LAB14_DIR, "data", "kb_cleaned.json"), encoding="utf-8"))
        _KB_ALTS = json.load(open(os.path.join(LAB14_DIR, "data", "conflict_alternatives.json"), encoding="utf-8"))
    return _KB_NODES, _KB_ALTS


def search_forest_docs(query: str, top_k: int = 3, role: str = "forester") -> dict:
    """Read-only гібридний пошук по документах корпусу ЛР 11."""
    t0 = time.perf_counter()
    top_k = min(max(1, int(top_k)), 5)
    eng = _get_rag()
    resp = eng.ask(query, top_k=top_k, use_graph=False, use_rerank=True, abstention_threshold=0.34, role=role)
    ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "tool": "search_forest_docs",
        "read_only": True,
        "citations": resp.get("citations", []),
        "abstained": resp.get("abstained", False),
        "top_score": round(float(resp.get("top_score", 0.0)), 4),
        "answer_snippet": resp.get("answer", "")[:320],
        "latency_ms": ms,
    }


def query_knowledge_graph(entity_code: str, include_alternatives: bool = True) -> dict:
    """Read-only пошук сутності в очищеному графі ЛР 14 + збережені альтернативи конфліктів."""
    t0 = time.perf_counter()
    nodes, alts = _get_kb()
    code_up = entity_code.strip().upper()
    matched = [n for n in nodes if n["code"].upper() == code_up or code_up in n["id"].upper()]
    rel_alts = [a for a in alts if code_up.replace("-", "") in a["entity_id"].upper()] if include_alternatives else []
    ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "tool": "query_knowledge_graph",
        "read_only": True,
        "entity_code": code_up,
        "found": len(matched) > 0,
        "nodes": matched[:3],
        "alternatives": rel_alts,
        "citations": [n["source_url"] for n in matched[:3]] + [a["accepted_source"] for a in rel_alts],
        "latency_ms": ms,
    }


def query_olap_metric(metric_name: str, group_by: str = None, year: int = None) -> dict:
    """Read-only обчислення метрики OLAP через семантичний шар ЛР 12 + AST-перевірку."""
    t0 = time.perf_counter()
    dims = [group_by] if group_by else []
    flts = [f"d.year = {int(year)}"] if year else []
    sql = lab12_sem.generate_metric_sql(metric_name, dimensions=dims, filters=flts)
    guard = lab12_t2sql.validate_sql_ast(sql)
    if not guard.safe:
        return {"tool": "query_olap_metric", "read_only": True, "blocked": True, "reason": guard.reason}

    db_uri = f"file:{os.path.join(LAB12_DIR, 'data', 'forest_olap.sqlite')}?mode=ro"
    con = sqlite3.connect(db_uri, uri=True)
    try:
        cur = con.execute(guard.sanitized_sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()[:50]]
    finally:
        con.close()
    ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "tool": "query_olap_metric",
        "read_only": True,
        "metric_name": metric_name,
        "sql": guard.sanitized_sql,
        "rows": rows,
        "citations": [f"semantic/metrics.yml#{metric_name}"],
        "latency_ms": ms,
    }
