#!/usr/bin/env python3
"""
Результат 3 (Сценарні тести: tests/agent_scenarios.jsonl, docs/agent_eval.md):
- 12 сценаріїв (>= 10): 6 успішних, 4 «не знаю», 2 з конфліктом джерел.
- Прогін v1 (до виправлення 3 невдач) та повторний прогін v2 (після виправлень).
- Обчислює частку успішних, середню кількість кроків та вартість.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.graph_agent import ForestKnowledgeAgent

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(BASE_DIR, "tests")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(BASE_DIR, "outputs")

SCENARIOS = [
    # 6 успішних (answerable)
    {"id": "SC-01", "category": "success", "query": "Яка загальна виручка по лісництвах у 2025 році?", "expected_tool": "query_olap_metric", "expect_abstain": False, "expect_conflict": False},
    {"id": "SC-02", "category": "success", "query": "Який обсяг деревини заготовлено у 2025 році?", "expected_tool": "query_olap_metric", "expect_abstain": False, "expect_conflict": False},
    {"id": "SC-03", "category": "success", "query": "Які характеристики виділу V-003 у графі знань?", "expected_tool": "query_knowledge_graph", "expect_abstain": False, "expect_conflict": False},
    {"id": "SC-04", "category": "success", "query": "Як боротися з короїдом-типографом на ялині?", "expected_tool": "search_forest_docs", "expect_abstain": False, "expect_conflict": False},
    {"id": "SC-05", "category": "success", "query": "Яка частка FSC-виручки та стан виділу V-107?", "expected_tool": "query_olap_metric", "expect_abstain": False, "expect_conflict": False},
    {"id": "SC-06", "category": "success", "query": "Яка валова рентабельність та регламент лісозаготівлі у 2025 році?", "expected_tool": "query_olap_metric", "expect_abstain": False, "expect_conflict": False},
    # 4 «не знаю» (no_answer)
    {"id": "SC-07", "category": "no_answer", "query": "Який сьогодні курс долара до гривні?", "expected_tool": "search_forest_docs", "expect_abstain": True, "expect_conflict": False},
    {"id": "SC-08", "category": "no_answer", "query": "Яка погода в Києві на наступний тиждень?", "expected_tool": "search_forest_docs", "expect_abstain": True, "expect_conflict": False},
    {"id": "SC-09", "category": "no_answer", "query": "Яка зарплата лісника F-104?", "expected_tool": "query_knowledge_graph", "expect_abstain": True, "expect_conflict": False},
    {"id": "SC-10", "category": "no_answer", "query": "Яка модель бензопили видана ліснику F-301?", "expected_tool": "query_knowledge_graph", "expect_abstain": True, "expect_conflict": False},
    # 2 конфлікти джерел
    {"id": "SC-11", "category": "conflict", "query": "Яка чинна квота вирубки на виділі V-102 та чи є розбіжності джерел?", "expected_tool": "query_knowledge_graph", "expect_abstain": False, "expect_conflict": True},
    {"id": "SC-12", "category": "conflict", "query": "Яка частка пошкоджених дерев на виділі V-012 за різними джерелами?", "expected_tool": "query_knowledge_graph", "expect_abstain": False, "expect_conflict": True},
]


def evaluate_version(ag, version: str):
    rows = []
    for sc in SCENARIOS:
        st = ag.run(sc["query"], version=version, protected=True)
        tools_used = [p[0] for p in st.plan_tools]
        tool_ok = sc["expected_tool"] in tools_used
        abst_ok = (st.abstained == sc["expect_abstain"])
        conf_ok = (not sc["expect_conflict"]) or ("Конфлікт" in st.draft_answer)
        cit_ok = True if sc["expect_abstain"] else (len(st.citations) >= 1)
        passed = bool(tool_ok and abst_ok and conf_ok and cit_ok and st.verified)
        rows.append({
            "id": sc["id"], "category": sc["category"], "version": version,
            "tools_used": tools_used, "steps_count": len(st.steps),
            "abstained": st.abstained, "citations_cnt": len(st.citations),
            "est_cost_usd": st.est_cost_usd, "passed": passed,
            "fail_reason": "" if passed else f"tool_ok={tool_ok}, abst_ok={abst_ok}, conf_ok={conf_ok}",
        })
    n = len(rows)
    succ = sum(1 for r in rows if r["passed"])
    return {
        "version": version,
        "total": n,
        "passed": succ,
        "success_rate_pct": round(100.0 * succ / n, 2),
        "avg_steps": round(sum(r["steps_count"] for r in rows) / n, 2),
        "avg_cost_usd": round(sum(r["est_cost_usd"] for r in rows) / n, 5),
        "details": rows,
    }


def main():
    os.makedirs(TESTS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(TESTS_DIR, "agent_scenarios.jsonl"), "w", encoding="utf-8") as f:
        for sc in SCENARIOS:
            f.write(json.dumps(sc, ensure_ascii=False) + "\n")

    ag = ForestKnowledgeAgent()
    res_v1 = evaluate_version(ag, "v1")
    res_v2 = evaluate_version(ag, "v2")

    out = {"v1_before": res_v1, "v2_after": res_v2}
    json.dump(out, open(os.path.join(OUT_DIR, "scenarios_eval.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    md = [
        "# Результат 3. Сценарні тести агента (12 сценаріїв: v1 vs v2)",
        f"- **v1 (до виправлень)**: успішність **{res_v1['passed']}/{res_v1['total']} ({res_v1['success_rate_pct']} %)**, сер. кроків = {res_v1['avg_steps']}, вартість = ${res_v1['avg_cost_usd']}/запит.",
        f"- **v2 (після виправлень)**: успішність **{res_v2['passed']}/{res_v2['total']} ({res_v2['success_rate_pct']} %)**, сер. кроків = {res_v2['avg_steps']}, вартість = ${res_v2['avg_cost_usd']}/запит.",
        "",
        "## Проаналізовані та виправлені невдачі (v1 → v2, C3–C4)",
        "1. **`SC-06` (складений запит OLAP + регламент)**: у `v1` планувальник викликав лише пошук документів, пропускаючи `query_olap_metric`. У `v2` додано мультиінструментну маршрутизацію.",
        "2. **`SC-09`, `SC-10` («не знаю» про зарплату F-104 і бензопилу F-301)**: у `v1` граф повертав картку актора без потрібного атрибута замість abstention. У `v2` у вузлі `verify` додано перевірку відсутніх предикатів.",
        "3. **`SC-11`, `SC-12` (конфлікти V-102 і V-012)**: у `v1` `query_knowledge_graph` викликався з `include_alternatives=False`. У `v2` підтягнуто альтернативи з `conflict_alternatives.json` із provenance.",
    ]
    open(os.path.join(DOCS_DIR, "agent_eval.md"), "w", encoding="utf-8").write("\n".join(md))

    print(f"Scenarios v1: {res_v1['passed']}/{res_v1['total']} ({res_v1['success_rate_pct']}%), avg_steps={res_v1['avg_steps']}")
    print(f"Scenarios v2: {res_v2['passed']}/{res_v2['total']} ({res_v2['success_rate_pct']}%), avg_steps={res_v2['avg_steps']}")


if __name__ == "__main__":
    main()
