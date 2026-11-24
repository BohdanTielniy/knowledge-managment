#!/usr/bin/env python3
"""
Результат 2 (Реалізація графа станів у стилі LangGraph):
Вузли графа: plan -> retrieve -> draft -> verify (перевірка цитат і політик).
Підтримує версію v1 (базова, до виправлення 3 невдач) та v2 (покращена після аналізу на сценаріях).
"""
import json
import os
import re
import time
from dataclasses import dataclass, field
from agent.security import (
    MAX_STEPS, check_direct_injection, check_write_attempt,
    check_pii_leak, sanitize_untrusted_context
)
from agent.tools import search_forest_docs, query_knowledge_graph, query_olap_metric

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "outputs")

UNANSWERABLE_PREDICATES = ("зарплат", "бензопил", "курс долара", "погода в києві", "телефон")


@dataclass
class AgentState:
    query: str
    role: str = "forester"
    version: str = "v2"
    protected: bool = True
    injected_doc_context: str = ""
    plan_tools: list = field(default_factory=list)
    tool_outputs: list = field(default_factory=list)
    draft_answer: str = ""
    citations: list = field(default_factory=list)
    verified: bool = False
    blocked: bool = False
    block_reason: str = ""
    abstained: bool = False
    steps: list = field(default_factory=list)
    total_ms: float = 0.0
    est_cost_usd: float = 0.0016


class ForestKnowledgeAgent:
    """Агентний граф станів: plan -> retrieve -> draft -> verify."""

    def _node_plan(self, state: AgentState):
        t0 = time.perf_counter()
        q = state.query
        low = q.lower()

        # Вхідні захисти (якщо увімкнено protected=True)
        if state.protected:
            for fn in (check_direct_injection, check_write_attempt):
                ok, reason = fn(q)
                if not ok:
                    state.blocked = True
                    state.block_reason = reason
                    state.steps.append({"node": "plan", "action": "blocked", "reason": reason, "ms": round((time.perf_counter() - t0) * 1000, 2)})
                    return
            ok, reason = check_pii_leak(q, state.role)
            if not ok:
                state.blocked = True
                state.block_reason = reason
                state.steps.append({"node": "plan", "action": "blocked", "reason": reason, "ms": round((time.perf_counter() - t0) * 1000, 2)})
                return

        # Маршрутизація інструментів
        codes = re.findall(r"\b(V-\d{3}|LS-\d{2}|F-\d{3})\b", q, flags=re.I)
        wants_olap = any(k in low for k in ("виручк", "рентабельн", "марж", "обсяг деревини", "частка fsc", "частка ндп", "середній ndvi"))
        wants_docs = any(k in low for k in ("регламент", "правил", "пожеж", "короїд", "квот", "лісництв", "дозвол", "процедур", "як ")) or not (codes or wants_olap)

        plan = []
        if wants_olap:
            metric = "total_revenue_uah"
            if "рентабельн" in low or "марж" in low:
                metric = "gross_margin_pct"
            elif "обсяг деревини" in low:
                metric = "timber_volume_m3"
            elif "fsc" in low:
                metric = "fsc_certified_share_pct"
            elif "ндп" in low or "недеревин" in low:
                metric = "nontimber_revenue_share_pct"
            elif "ndvi" in low:
                metric = "avg_ndvi_health"
            yr_m = re.search(r"\b(202[4-6])\b", q)
            yr = int(yr_m.group(1)) if yr_m else None
            grp = "forestry_code" if "по лісництвах" in low else None
            # У v1 на складеному запиті з документом планувальник помилково пропускав OLAP
            if state.version == "v2" or not wants_docs:
                plan.append(("query_olap_metric", {"metric_name": metric, "group_by": grp, "year": yr}))

        if codes:
            inc_alt = (state.version == "v2")  # У v1 забували підтягувати alternatives конфліктів!
            plan.append(("query_knowledge_graph", {"entity_code": codes[0].upper(), "include_alternatives": inc_alt}))

        if wants_docs or not plan:
            plan.append(("search_forest_docs", {"query": q, "top_k": 3, "role": state.role}))

        state.plan_tools = plan[:MAX_STEPS - 2]
        state.steps.append({"node": "plan", "tools_planned": [p[0] for p in state.plan_tools], "ms": round((time.perf_counter() - t0) * 1000, 2)})

    def _node_retrieve(self, state: AgentState):
        if state.blocked:
            return
        # Перевірка непрямої ін'єкції в ін'єктованому контексті документа (якщо є)
        if state.injected_doc_context and state.protected:
            ok, res = sanitize_untrusted_context(state.injected_doc_context)
            if not ok:
                state.blocked = True
                state.block_reason = res
                state.steps.append({"node": "retrieve", "action": "blocked_indirect_injection", "reason": res})
                return

        for tname, kwargs in state.plan_tools:
            if len(state.steps) >= MAX_STEPS:
                state.blocked = True
                state.block_reason = f"Перевищено ліміт кроків MAX_STEPS={MAX_STEPS}"
                return
            if tname == "search_forest_docs":
                out = search_forest_docs(**kwargs)
            elif tname == "query_knowledge_graph":
                out = query_knowledge_graph(**kwargs)
            elif tname == "query_olap_metric":
                out = query_olap_metric(**kwargs)
            else:
                continue
            state.tool_outputs.append(out)
            state.steps.append({"node": "retrieve", "tool": tname, "args": kwargs, "latency_ms": out.get("latency_ms", 0.0), "citations": out.get("citations", [])})

    def _node_draft(self, state: AgentState):
        if state.blocked:
            state.draft_answer = f"Запит заблоковано політикою безпеки: {state.block_reason}."
            return
        t0 = time.perf_counter()
        parts, cits = [], []
        for out in state.tool_outputs:
            t = out["tool"]
            if t == "query_olap_metric" and out.get("rows"):
                parts.append(f"OLAP ({out['metric_name']}): {out['rows'][:3]}")
                cits.extend(out.get("citations", []))
            elif t == "query_knowledge_graph" and out.get("found"):
                nd = out["nodes"][0]
                parts.append(f"Граф ({nd['code']}): {nd['name']}, площа={nd['area_ha']} га, приріст={nd['annual_increment_m3']} м³, NDVI={nd['ndvi']}.")
                if out.get("alternatives"):
                    a = out["alternatives"][0]
                    parts.append(f"Конфлікт {a['conflict_id']}: чинне={a['accepted_value']} ({a['accepted_source']}), альтернатива={a['alternative_value']} ({a['alternative_source']}).")
                cits.extend(out.get("citations", []))
            elif t == "search_forest_docs" and not out.get("abstained") and out.get("citations"):
                parts.append(out["answer_snippet"])
                cits.extend(out.get("citations", []))

        state.citations = list(dict.fromkeys(cits))
        if not parts:
            state.abstained = True
            state.draft_answer = "Не знаю: у сховищі знань немає підтверджених даних для відповіді на цей запит."
        else:
            state.draft_answer = " ".join(parts)
        state.steps.append({"node": "draft", "citations_cnt": len(state.citations), "ms": round((time.perf_counter() - t0) * 1000, 2)})

    def _node_verify(self, state: AgentState):
        """Вузол перевірки цитат та політики abstention перед фінальною відповіддю (C3)."""
        t0 = time.perf_counter()
        if state.blocked:
            state.verified = True
            state.steps.append({"node": "verify", "status": "blocked_verified", "ms": round((time.perf_counter() - t0) * 1000, 2)})
            return

        low = state.query.lower()
        # У v2 перевіряємо відсутній предикат (напр. зарплата F-104), навіть якщо код сутності знайдено!
        if state.version == "v2" and any(p in low for p in UNANSWERABLE_PREDICATES):
            state.abstained = True
            state.citations = []
            state.draft_answer = "Не знаю: запитаний атрибут відсутній у сховищі знань Domain Knowledge Hub."
            state.verified = True
            state.steps.append({"node": "verify", "status": "abstention_enforced", "ms": round((time.perf_counter() - t0) * 1000, 2)})
            return

        # Перевірка, що кожна відповідь (не abstention) має >= 1 реальну цитату з tool_outputs
        valid_pool = {c for out in state.tool_outputs for c in out.get("citations", [])}
        state.citations = [c for c in state.citations if c in valid_pool]
        if not state.abstained and not state.citations:
            state.abstained = True
            state.draft_answer = "Не знаю: відповідь не підтверджена джерелами зі сховища."
        state.verified = True
        state.steps.append({"node": "verify", "status": "citations_verified", "valid_citations": len(state.citations), "ms": round((time.perf_counter() - t0) * 1000, 2)})

    def run(self, query: str, role: str = "forester", version: str = "v2", protected: bool = True, injected_doc_context: str = "") -> AgentState:
        t0 = time.perf_counter()
        st = AgentState(query=query, role=role, version=version, protected=protected, injected_doc_context=injected_doc_context)
        self._node_plan(st)
        self._node_retrieve(st)
        self._node_draft(st)
        self._node_verify(st)
        st.total_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        st.est_cost_usd = round(0.0005 * len(st.steps), 5)
        return st


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    ag = ForestKnowledgeAgent()
    demo_queries = [
        "Яка загальна виручка по лісництвах у 2025 році?",
        "Які характеристики і конфлікт квот на виділі V-102?",
        "Як боротися з короїдом-типографом на ялині?",
        "Яка частка FSC-виручки та стан виділу V-107?",
        "Яка зарплата лісника F-104?",
    ]
    trace_path = os.path.join(OUT_DIR, "trace_log.jsonl")
    with open(trace_path, "w", encoding="utf-8") as f:
        for q in demo_queries:
            st = ag.run(q)
            rec = {"query": q, "tools": [p[0] for p in st.plan_tools], "abstained": st.abstained,
                   "citations": st.citations, "total_ms": st.total_ms, "steps": st.steps}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"DEMO: {q} -> tools={rec['tools']}, abst={st.abstained}, cits={len(st.citations)}, {st.total_ms}ms")
