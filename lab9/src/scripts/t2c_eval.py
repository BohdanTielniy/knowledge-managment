#!/usr/bin/env python3
"""
ЛР 9, Результат 5: оцінювання text-to-Cypher (read-only контроль, перевірка схеми,
примусовий LIMIT, обчислення точності та підтримка live-виконання у Neo4j).

Запуск (автономна перевірка без Neo4j):
    python3 scripts/t2c_eval.py

Запуск із виконанням у Docker Neo4j (read-only сесія):
    python3 scripts/t2c_eval.py --live
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_PATH = os.path.join(ROOT, "tests", "t2c.jsonl")

ALLOWED_LABELS = {
    "Forestry", "Compartment", "TreeSpecies", "ConiferousSpecies", "DeciduousSpecies",
    "ForestProduct", "TimberProduct", "NonTimberProduct",
    "Threat", "InsectPest", "ForestDisease", "Drought", "Windthrow",
    "MeteoObservation", "Process", "TimberHarvesting", "SanitaryFelling", "MainFelling",
    "Reforestation", "FirePreventionMeasure",
    "Permit", "FellingTicket", "Quota", "HarvestQuota", "NonTimberCollectionLimit",
    "Actor", "Forester", "ChiefForester", "HarvestBrigade", "EmergencyService",
}

ALLOWED_RELS = {
    "PART_OF_FORESTRY", "HAS_DOMINANT_SPECIES", "YIELDS_PRODUCT", "AFFECTED_BY",
    "TRIGGERS", "APPLIED_TO", "REQUIRES_PERMIT", "CONSTRAINED_BY", "PERFORMED_BY",
    "SUPERVISES", "NOTIFIES", "FOLLOWED_BY", "MONITORS_UNIT", "LIMITED_BY",
}

FORBIDDEN_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH|CALL\s+dbms|write)\b",
    re.IGNORECASE,
)


def build_schema_prompt(question: str) -> str:
    """Формує schema-aware підказку для text-to-Cypher із обмеженням read-only та LIMIT."""
    return (
        "Ти — експерт із Neo4j Cypher. Згенеруй ТІЛЬКИ один read-only Cypher-запит "
        "(без CREATE/MERGE/DELETE/SET/DROP) і обов'язково додай LIMIT 50.\n"
        f"Дозволені мітки: {', '.join(sorted(ALLOWED_LABELS))}.\n"
        f"Дозволені типи зв'язків: {', '.join(sorted(ALLOWED_RELS))}.\n"
        "Напрямки ключових зв'язків: "
        "(Compartment)-[:PART_OF_FORESTRY]->(Forestry), "
        "(Compartment)-[:HAS_DOMINANT_SPECIES]->(TreeSpecies), "
        "(Compartment)-[:AFFECTED_BY]->(Threat), "
        "(Process)-[:APPLIED_TO]->(Compartment), "
        "(Process)-[:REQUIRES_PERMIT]->(Permit), "
        "(Process)-[:CONSTRAINED_BY]->(Quota), "
        "(Process)-[:FOLLOWED_BY]->(Process), "
        "(Actor)-[:SUPERVISES]->(Compartment|Forestry), "
        "(MeteoObservation)-[:MONITORS_UNIT]->(Forestry).\n"
        "Пороги: ураження damagedTreesShare > 10.0; стиглі хвойні standAgeYears >= 81; "
        "високий пожежний ризик airTemperatureC > 30 AND airHumidityPercent < 30 AND daysWithoutRain >= 7; "
        "низький NDVI ndviValue < 0.65.\n"
        f"Питання користувача: {question}"
    )


def validate_read_only(cypher: str):
    m = FORBIDDEN_WRITE_PATTERN.search(cypher)
    return (m is None), (m.group(0) if m else None)


def validate_schema(cypher: str):
    """Перевіряє, що всі мітки вузлів і типи зв'язків існують у графовій схемі."""
    # Витягуємо типи зв'язків усередині [...]
    rel_matches = re.findall(r"\[\s*[a-zA-Z0-9_]*\s*:([A-Za-z0-9_|]+)", cypher)
    bad_rels = []
    for rm in rel_matches:
        for r in rm.split("|"):
            if r not in ALLOWED_RELS:
                bad_rels.append(r)

    # Витягуємо мітки вузлів усередині (...)
    node_blocks = re.findall(r"\(([^()]*)\)", cypher)
    bad_labels = []
    for blk in node_blocks:
        # ігноруємо ключі словників {key: value}
        blk_clean = re.sub(r"\{[^}]*\}", "", blk)
        for lbl in re.findall(r":([A-Za-z][A-Za-z0-9_]*)", blk_clean):
            if lbl not in ALLOWED_LABELS:
                bad_labels.append(lbl)

    return (len(bad_labels) == 0 and len(bad_rels) == 0), bad_labels, bad_rels


def ensure_limit(cypher: str, default_limit: int = 50):
    has_limit = bool(re.search(r"\bLIMIT\s+\d+\b", cypher, re.IGNORECASE))
    if has_limit:
        return cypher, True
    return f"{cypher.rstrip('; ')} LIMIT {default_limit}", False


def run_live(tests):
    from neo4j import GraphDatabase, RoutingControl

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not pwd:
        raise RuntimeError("Задайте NEO4J_PASSWORD у .env або змінних середовища")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    live_results = {}
    with driver:
        for t in tests:
            q, _ = ensure_limit(t["generated_cypher"])
            ro_ok, _ = validate_read_only(q)
            schema_ok, _, _ = validate_schema(q)
            if not ro_ok or not schema_ok:
                live_results[t["id"]] = ("BLOCKED", 0)
                continue
            try:
                records, _, _ = driver.execute_query(q, routing_=RoutingControl.READ)
                live_results[t["id"]] = ("OK", len(records))
            except Exception as exc:
                live_results[t["id"]] = (f"ERR:{type(exc).__name__}", 0)
    return live_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Виконати запити у Neo4j (RoutingControl.READ)")
    args = parser.parse_args()

    with open(TESTS_PATH, encoding="utf-8") as fh:
        tests = [json.loads(line) for line in fh if line.strip()]

    live_map = run_live(tests) if args.live else {}

    total = len(tests)
    correct = 0
    ro_pass = 0
    schema_pass = 0
    limit_pass = 0

    print(f"Оцінювання text-to-Cypher ({total} питань, файл: tests/t2c.jsonl)\n")
    print(f"{'ID':8s} | {'RO':3s} | {'Sch':3s} | {'Lim':3s} | {'OK':3s} | Коментар / live")
    print("-" * 80)
    for t in tests:
        q = t["generated_cypher"]
        ro_ok, bad_kw = validate_read_only(q)
        sch_ok, bad_lbls, bad_rels = validate_schema(q)
        _, had_lim = ensure_limit(q)

        ro_pass += int(ro_ok)
        schema_pass += int(sch_ok)
        limit_pass += int(had_lim)
        correct += int(t["is_correct"])

        note = t["error_type"] or "pass"
        if not sch_ok:
            note += f" (bad_labels={bad_lbls}, bad_rels={bad_rels})"
        if args.live and t["id"] in live_map:
            st, cnt = live_map[t["id"]]
            note += f" | live={st}(rows={cnt}, exp={t['expected_row_count']})"

        print(f"{t['id']:8s} | {'YES' if ro_ok else 'NO ':3s} | {'YES' if sch_ok else 'NO ':3s} | "
              f"{'YES' if had_lim else 'NO ':3s} | {'YES' if t['is_correct'] else 'NO ':3s} | {note}")

    acc = 100.0 * correct / total if total else 0.0
    print("-" * 80)
    print(f"Частка коректних запитів: {correct}/{total} ({acc:.1f}%)")
    print(f"Read-only перевірка:      {ro_pass}/{total}")
    print(f"Перевірка схеми:          {schema_pass}/{total} (заблоковано галюцинацій: {total - schema_pass})")
    print(f"Наявність LIMIT у виході: {limit_pass}/{total} (решта доповнюється автоматично)")


if __name__ == "__main__":
    main()
