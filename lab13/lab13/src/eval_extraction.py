#!/usr/bin/env python3
"""
Результат 4 (Оцінювання та аналіз помилок):
- На замороженій test-вибірці (12 документів, 84 твердження) обчислює Precision / Recall / F1
  загалом і за кожним із 6 типів відношень для Методу А (правила) та Методу Б (LLM).
- Обчислює частку тверджень без підтвердженої цитати та вартість/документ.
- Класифікує >= 10 конкретних помилок обох методів (пропуски, напрямок, заперечення, вигадані).
- Будує графік docs/fig_ie_comparison.png, зберігає docs/extraction_eval.md та outputs/eval_summary.json.
"""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(BASE_DIR, "outputs")

RELATIONS = ["PART_OF", "DOMINATED_BY", "YIELDS", "AFFECTED_BY", "SUPERVISES", "MITIGATES"]


def to_key(c):
    return (c["doc_id"], c["subject"], c["relation"], c["object"])


def prf(gold_set, pred_set):
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def evaluate_method(gold, preds, method_name, cost_per_doc_usd):
    g_all = {to_key(c) for c in gold}
    p_all = {to_key(c) for c in preds}
    overall = prf(g_all, p_all)

    by_rel = {}
    for rel in RELATIONS:
        g_r = {to_key(c) for c in gold if c["relation"] == rel}
        p_r = {to_key(c) for c in preds if c["relation"] == rel}
        by_rel[rel] = prf(g_r, p_r)

    ungrounded = sum(1 for c in preds if not c.get("evidence_grounded", True))
    ungrounded_pct = round(100.0 * ungrounded / len(preds), 2) if preds else 0.0

    # Збираємо помилки
    errors = []
    for k in sorted(g_all - p_all):
        errors.append({"method": method_name, "error_type": "Пропуск (FN)", "triple": f"{k[0]}: ({k[1]}, {k[2]}, {k[3]})"})
    for k in sorted(p_all - g_all):
        # Визначаємо підтип FP
        pred_obj = [c for c in preds if to_key(c) == k][0]
        if not pred_obj.get("evidence_grounded", True):
            etype = "Вигадане твердження (без цитати)"
        elif (k[0], k[3], k[2], k[1]) in g_all:
            etype = "Помилка напрямку (інверсія)"
        else:
            etype = "Хибне спрацювання (заперечення / шум)"
        errors.append({"method": method_name, "error_type": etype, "triple": f"{k[0]}: ({k[1]}, {k[2]}, {k[3]})"})

    return {
        "method": method_name,
        "overall": overall,
        "by_relation": by_rel,
        "total_preds": len(preds),
        "ungrounded_count": ungrounded,
        "ungrounded_pct": ungrounded_pct,
        "cost_per_doc_usd": cost_per_doc_usd,
        "errors": errors,
    }


def plot_comparison(res_a, res_b, out_png):
    labels = RELATIONS + ["ЗАГАЛОМ"]
    f1_a = [res_a["by_relation"][r]["f1"] for r in RELATIONS] + [res_a["overall"]["f1"]]
    f1_b = [res_b["by_relation"][r]["f1"] for r in RELATIONS] + [res_b["overall"]["f1"]]

    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9.5, 4.4), dpi=170)
    b1 = ax.bar(x - w / 2, f1_a, w, label="Метод А (правила/regex)", color="#5DADE2", edgecolor="#111111", lw=0.7)
    b2 = ax.bar(x + w / 2, f1_b, w, label="Метод Б (LLM + схема + retry)", color="#1E8449", edgecolor="#111111", lw=0.7)
    ax.set_ylabel("F1-міра (test, n = 84)")
    ax.set_title("Порівняння F1-міри Метод А (правила) vs Метод Б (LLM) за типами відношень")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right", fontsize=9)
    ax.set_ylim(0, 1.13)
    ax.grid(axis="y", ls="--", alpha=0.4)
    ax.legend(loc="lower right")
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.018, f"{h:.2f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    gold_test = [json.loads(l) for l in open(os.path.join(DATA_DIR, "test.jsonl"), encoding="utf-8")]
    preds_a = [json.loads(l) for l in open(os.path.join(OUT_DIR, "preds_rules_test.jsonl"), encoding="utf-8")]
    preds_b = [json.loads(l) for l in open(os.path.join(OUT_DIR, "preds_llm_test.jsonl"), encoding="utf-8")]

    res_a = evaluate_method(gold_test, preds_a, "Метод А (правила)", 0.0)
    res_b = evaluate_method(gold_test, preds_b, "Метод Б (LLM)", 0.0014)

    all_errors = res_a["errors"] + res_b["errors"]
    summary = {"method_A": res_a, "method_B": res_b, "total_errors_classified": len(all_errors)}
    json.dump(summary, open(os.path.join(OUT_DIR, "eval_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    plot_comparison(res_a, res_b, os.path.join(DOCS_DIR, "fig_ie_comparison.png"))

    md = [
        "# Результат 4. Оцінювання методів витягу на test-вибірці та аналіз помилок",
        f"- **Тестовий набір (`data/test.jsonl`)**: 12 документів, **{len(gold_test)} золотих тверджень**.",
        "",
        "## 1. Порівняння P / R / F1 загалом і за типами (C1–C2)",
        "| Тип відношення | Метод А P | Метод А R | Метод А F1 | Метод Б P | Метод Б R | Метод Б F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rel in RELATIONS:
        a, b = res_a["by_relation"][rel], res_b["by_relation"][rel]
        md.append(f"| `{rel}` | {a['precision']:.3f} | {a['recall']:.3f} | {a['f1']:.3f} | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} |")
    oa, ob = res_a["overall"], res_b["overall"]
    md.append(f"| **ЗАГАЛОМ** | **{oa['precision']:.3f}** | **{oa['recall']:.3f}** | **{oa['f1']:.3f}** | **{ob['precision']:.3f}** | **{ob['recall']:.3f}** | **{ob['f1']:.3f}** |")
    md.extend([
        "",
        f"- **Частка тверджень без підтвердженої цитати**: Метод А = **{res_a['ungrounded_pct']} %** ({res_a['ungrounded_count']}/{res_a['total_preds']}), Метод Б = **{res_b['ungrounded_pct']} %** ({res_b['ungrounded_count']}/{res_b['total_preds']}).",
        f"- **Вартість / документ**: Метод А = **$0.0000**, Метод Б = **${res_b['cost_per_doc_usd']:.4f}** (Gemini 2.5 Flash).",
        "",
        f"## 2. Аналіз помилок (класифіковано {len(all_errors)} помилок, вимога ≥ 10, C3)",
        "| № | Метод | Клас помилки | Твердження |",
        "|---:|---|---|---|",
    ])
    for idx, e in enumerate(all_errors, start=1):
        md.append(f"| {idx} | {e['method']} | {e['error_type']} | `{e['triple']}` |")
    md.extend([
        "",
        "## 3. Рекомендація (C4)",
        "Рекомендується **гібридний конвеєр**: Метод А (правила/regex) для детермінованих кодів (`PART_OF`, `DOMINATED_BY`, F1 = 1.00, вартість $0) + Метод Б (LLM зі схемою + обов’язковий постфільтр `evidence_grounded == True` та перевірка сигнатури типів) для семантично варіативних відношень (`YIELDS`, `AFFECTED_BY`, `SUPERVISES`, `MITIGATES`), де правила втрачають recall на перефразуваннях.",
    ])
    open(os.path.join(DOCS_DIR, "extraction_eval.md"), "w", encoding="utf-8").write("\n".join(md))

    print(f"Eval done: Method A F1={oa['f1']} (P={oa['precision']}, R={oa['recall']}), "
          f"Method B F1={ob['f1']} (P={ob['precision']}, R={ob['recall']}), errors={len(all_errors)}")


if __name__ == "__main__":
    main()
