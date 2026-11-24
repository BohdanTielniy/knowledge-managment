#!/usr/bin/env python3
"""
Результат 5 (Людина в циклі та запис знань: agent/propose_fact.py, docs/hitl.md):
- Інструмент propose_fact: валідація (SHACL-діапазони, source_url) -> оцінка ризику (low/medium/high).
- Для medium/high ризику вимагає схвалення людини; запис лише з provenance.
- Демонстрація 3 сценаріїв: low (авто), medium (схвалення людиною), high (відхилення людиною).
- Журнал аудиту outputs/hitl_audit.jsonl та метрики (частка схвалених, час схвалення).
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "outputs")
DOCS_DIR = os.path.join(BASE_DIR, "docs")


def validate_fact_shacl(proposal: dict):
    """Перевірка SHACL-обмежень та наявності джерела перед класифікацією ризику."""
    if not re.match(r"^https?://", str(proposal.get("source_url", ""))):
        return False, "SHACL-4: відсутній валідний source_url"
    prop = proposal.get("property")
    val = proposal.get("value")
    if prop == "ndvi" and not (isinstance(val, (int, float)) and 0.0 <= val <= 1.0):
        return False, "SHACL-3: ndvi поза межами [0, 1]"
    if prop == "quota_m3" and not (isinstance(val, (int, float)) and val > 0):
        return False, "SHACL-2: квота має бути > 0"
    return True, "SHACL_OK"


def classify_risk(proposal: dict) -> str:
    prop = proposal.get("property")
    if prop in ("skos_altLabel", "description_note"):
        return "low"
    if prop in ("ndvi", "damagedTreesShare"):
        return "medium"
    return "high"  # quota_m3, fsc_certified, delete, тощо


def propose_fact(proposal: dict, human_decision=None, review_time_sec: float = 0.0):
    valid, v_msg = validate_fact_shacl(proposal)
    risk = classify_risk(proposal)

    if not valid:
        status = "rejected_validation"
        approved_by = "shacl_gate"
    elif risk == "low":
        status = "auto_approved"
        approved_by = "auto_policy_low_risk"
    else:
        if human_decision == "approve":
            status = "human_approved"
            approved_by = proposal.get("reviewer", "auditor_LS01")
        else:
            status = "human_rejected"
            approved_by = proposal.get("reviewer", "auditor_LS01")

    audit_rec = {
        "proposal_id": proposal["proposal_id"],
        "entity_id": proposal["entity_id"],
        "property": proposal["property"],
        "value": proposal["value"],
        "source_url": proposal["source_url"],
        "shacl_valid": valid,
        "shacl_msg": v_msg,
        "risk_level": risk,
        "requires_human": risk in ("medium", "high"),
        "status": status,
        "approved_by": approved_by,
        "review_time_sec": review_time_sec,
        "decision_note": proposal.get("decision_note", ""),
        "timestamp": "2026-11-24T22:30:00+02:00",
    }
    return audit_rec


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    demos = [
        (
            {"proposal_id": "HITL-01", "entity_id": "Product_SpruceTimber", "property": "skos_altLabel",
             "value": "Смерекова деревина", "source_url": "https://hub.forest.local/kb/glossary-2026",
             "decision_note": "Безпечний синонім із валідним джерелом — автозапис."},
            None, 0.2,
        ),
        (
            {"proposal_id": "HITL-02", "entity_id": "Compartment_V008", "property": "ndvi",
             "value": 0.81, "source_url": "https://hub.forest.local/kb/sentinel2-2026-10",
             "reviewer": "Лісничий LS-01", "decision_note": "Підтверджено супутниковим знімком Sentinel-2."},
            "approve", 14.2,
        ),
        (
            {"proposal_id": "HITL-03", "entity_id": "Compartment_V102", "property": "quota_m3",
             "value": 780.0, "source_url": "https://import.forest.local/draft-quota",
             "reviewer": "Екоаудитор FSC", "decision_note": "Відхилено: 780 м³ суттєво перевищує річний приріст 555 м³."},
            "reject", 9.5,
        ),
    ]

    logs = [propose_fact(p, dec, rt) for p, dec, rt in demos]
    with open(os.path.join(OUT_DIR, "hitl_audit.jsonl"), "w", encoding="utf-8") as f:
        for r in logs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    approved = sum(1 for r in logs if r["status"] in ("auto_approved", "human_approved"))
    human_times = [r["review_time_sec"] for r in logs if r["requires_human"]]
    summary = {
        "total_proposals": len(logs),
        "approved_count": approved,
        "approval_rate_pct": round(100.0 * approved / len(logs), 1),
        "rejected_count": len(logs) - approved,
        "avg_human_review_sec": round(sum(human_times) / len(human_times), 2),
        "records": logs,
    }
    json.dump(summary, open(os.path.join(OUT_DIR, "hitl_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    md = [
        "# Результат 5. Людина в циклі (HITL) та контрольований запис знань",
        f"- **Усього пропозицій**: {summary['total_proposals']} | **Схвалено**: {approved}/{len(logs)} ({summary['approval_rate_pct']} %) | **Відхилено**: {summary['rejected_count']} | **Середній час рішення людини**: {summary['avg_human_review_sec']} с.",
        "",
        "| ID | Сутність / поле | Значення | Ризик | HITL | Статус | Виконавець | Час (с) |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for r in logs:
        md.append(f"| {r['proposal_id']} | `{r['entity_id']}.{r['property']}` | `{r['value']}` | {r['risk_level']} | {'Так' if r['requires_human'] else 'Ні'} | **{r['status']}** | {r['approved_by']} | {r['review_time_sec']} |")
    open(os.path.join(DOCS_DIR, "hitl.md"), "w", encoding="utf-8").write("\n".join(md))

    print(f"HITL demo done: approved={approved}/{len(logs)} ({summary['approval_rate_pct']}%), avg_human_time={summary['avg_human_review_sec']}s")


if __name__ == "__main__":
    main()
