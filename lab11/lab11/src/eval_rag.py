#!/usr/bin/env python3
"""
ЛР 11, Результати 2, 4 і 5:
  - Результат 2: порівняння «лише текст» vs «текст + підграф» на 12 питаннях (outputs/graph_vs_text.json)
  - Результат 4: оцінювання на 32 тестах (faithfulness, context_recall, citation_accuracy, abstention_rate),
                 узгодженість суддя–людина (12 оцінок) та аналіз провалів (outputs/rag_eval_results.json)
  - Результат 5: контрольований експеримент оптимізації «до/після» (Baseline vs Optimized),
                 p50/p95 затримка, токени, вартість і графік docs/fig_rag_optimization.png

Запуск: python3 src/eval_rag.py
"""
import json
import os
import sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from rag import RAGPipeline

GRAPH_Q_PATH = os.path.join(ROOT, "eval", "graph_questions.jsonl")
RAG_EVAL_PATH = os.path.join(ROOT, "eval", "rag_eval.jsonl")
AGREE_PATH = os.path.join(ROOT, "eval", "judge_human_agreement.jsonl")
OUT_DIR = os.path.join(ROOT, "outputs")
DOCS_DIR = os.path.join(ROOT, "docs")


def eval_graph_vs_text(rag: RAGPipeline):
    qs = [json.loads(l) for l in open(GRAPH_Q_PATH, encoding="utf-8") if l.strip()]
    rows = []
    for item in qs:
        r_txt = rag.ask(item["query"], role="forester_admin", top_k=5, use_graph=False, log_path=None)
        r_grp = rag.ask(item["query"], role="forester_admin", top_k=5, use_graph=True, log_path=None)

        exp = item["expected_entities"]
        # Перевіряємо, скільки цільових ID/сутностей згадано у відповіді або цитатах (пояснюваність + повнота зв'язків)
        def entity_cov(rec):
            blob = (rec["answer"] + " " + " ".join(rec["citations"]) + " " + " ".join(rec["graph_entities"])).lower()
            hits = 0
            for e in exp:
                short = e.split("_")[-1].lower()
                if e.lower() in blob or (len(short) >= 4 and short in blob):
                    hits += 1
            return round(hits / len(exp), 3)

        rows.append({
            "id": item["id"],
            "query": item["query"],
            "text_only_cov": entity_cov(r_txt),
            "text_graph_cov": entity_cov(r_grp),
            "text_only_tokens": r_txt["total_tokens"],
            "text_graph_tokens": r_grp["total_tokens"],
            "graph_edges_added": r_grp["graph_edges"],
        })

    summary = {
        "num_questions": len(rows),
        "text_only_avg_cov": round(float(np.mean([r["text_only_cov"] for r in rows])), 4),
        "text_graph_avg_cov": round(float(np.mean([r["text_graph_cov"] for r in rows])), 4),
        "text_only_avg_tokens": round(float(np.mean([r["text_only_tokens"] for r in rows])), 1),
        "text_graph_avg_tokens": round(float(np.mean([r["text_graph_tokens"] for r in rows])), 1),
        "token_overhead_pct": round(
            100.0 * (np.mean([r["text_graph_tokens"] for r in rows]) - np.mean([r["text_only_tokens"] for r in rows]))
            / max(1.0, np.mean([r["text_only_tokens"] for r in rows])),
            1,
        ),
        "per_question": rows,
    }
    with open(os.path.join(OUT_DIR, "graph_vs_text.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return summary


def run_eval_suite(rag: RAGPipeline, tests: list, cfg_name: str,
                   top_k: int, use_graph: bool, use_rerank: bool,
                   abst_thr: float, strict_inj: bool):
    faith_list, ctx_rec_list, cit_acc_list = [], [], []
    abst_total, abst_ok = 0, 0
    inj_total, inj_ok = 0, 0
    conf_total, conf_ok = 0, 0
    latencies, tokens_list = [], []
    failures = []

    for t in tests:
        rec = rag.ask(
            t["query"],
            role="forester_admin",
            top_k=top_k,
            use_graph=use_graph,
            use_rerank=use_rerank,
            abstention_threshold=abst_thr,
            strict_injection=strict_inj,
            log_path=None,
        )
        latencies.append(rec["latency_ms"])
        tokens_list.append(rec["total_tokens"])
        cat = t["category"]
        got_docs = {s["doc_id"] for s in rec["sources"]}
        exp_docs = set(t["expected_docs"])

        if cat == "answerable":
            cr = len(got_docs & exp_docs) / len(exp_docs)
            ctx_rec_list.append(cr)
            # Faithfulness (автоматичний суддя): не відмовився хибно + цитати валідні + покриття контексту > 0
            f_ok = (not rec["abstained"]) and rec["citations_valid"] and len(rec["citations"]) > 0 and cr > 0
            faith_list.append(1.0 if f_ok else 0.0)
            cit_acc_list.append(1.0 if (rec["citations_valid"] and len(rec["citations"]) > 0) else 0.0)
            if not f_ok or cr < 1.0:
                reason = "пошук" if cr < 1.0 else ("політика" if rec["abstained"] else "генерація")
                failures.append({"id": t["id"], "category": cat, "reason": reason,
                                 "detail": f"context_recall={cr:.2f}, abstained={rec['abstained']}, cits={rec['citations'][:2]}"})

        elif cat == "no_answer":
            abst_total += 1
            if rec["abstained"]:
                abst_ok += 1
                faith_list.append(1.0)
            else:
                faith_list.append(0.0)
                failures.append({"id": t["id"], "category": cat, "reason": "політика",
                                 "detail": f"Хибна відповідь замість 'не знаю' (top_score={rec['sources'][0]['score'] if rec['sources'] else 0})"})

        elif cat == "conflict":
            conf_total += 1
            cr = len(got_docs & exp_docs) / len(exp_docs)
            ctx_rec_list.append(cr)
            if rec["conflict_detected"] and rec["citations_valid"]:
                conf_ok += 1
                faith_list.append(1.0)
                cit_acc_list.append(1.0)
            else:
                faith_list.append(0.0)
                cit_acc_list.append(1.0 if rec["citations_valid"] else 0.0)
                failures.append({"id": t["id"], "category": cat, "reason": "контекст" if cr < 1.0 else "генерація",
                                 "detail": f"conflict_detected={rec['conflict_detected']}, context_recall={cr:.2f}"})

        elif cat == "injection":
            inj_total += 1
            if rec["injection_blocked"]:
                inj_ok += 1
                faith_list.append(1.0)
            else:
                faith_list.append(0.0)
                failures.append({"id": t["id"], "category": cat, "reason": "політика",
                                 "detail": "Prompt injection не заблоковано на етапі політики"})

    avg_tok = float(np.mean(tokens_list))
    # Орієнтовна вартість у хмарному тарифі gpt-4o-mini ($0.15/1M in, $0.60/1M out) для порівняння бюджету
    est_cloud_cost_1k = round((avg_tok * 0.82 * 0.15 + avg_tok * 0.18 * 0.60) / 1000.0, 4)

    return {
        "config": cfg_name,
        "params": {"top_k": top_k, "use_graph": use_graph, "use_rerank": use_rerank,
                   "abstention_threshold": abst_thr, "strict_injection": strict_inj},
        "faithfulness": round(float(np.mean(faith_list)), 4),
        "context_recall": round(float(np.mean(ctx_rec_list)), 4),
        "citation_accuracy": round(float(np.mean(cit_acc_list)), 4),
        "abstention_rate": round(abst_ok / max(1, abst_total), 4),
        "conflict_handling_rate": round(conf_ok / max(1, conf_total), 4),
        "injection_defense_rate": round(inj_ok / max(1, inj_total), 4),
        "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        "avg_tokens": round(avg_tok, 1),
        "local_cost_usd_per_query": 0.0,
        "est_gpt4o_mini_usd_per_1k": est_cloud_cost_1k,
        "failures_count": len(failures),
        "failures": failures,
    }


def compute_judge_agreement():
    rows = [json.loads(l) for l in open(AGREE_PATH, encoding="utf-8") if l.strip()]
    n = len(rows)
    agree = sum(1 for r in rows if r["judge_faithful"] == r["human_faithful"])
    po = agree / n
    return {
        "manual_samples": n,
        "exact_agreement": round(po, 4),
        "disagreements": [r for r in rows if r["judge_faithful"] != r["human_faithful"]],
    }


def plot_optimization(before, after):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = ["faithfulness", "context_recall", "citation_accuracy", "abstention_rate", "injection_defense_rate"]
    labels = ["Faithfulness", "Context\nRecall", "Citation\nAccuracy", "Abstention\nRate", "Injection\nDefense"]
    v_b = [before[m] for m in metrics]
    v_a = [after[m] for m in metrics]

    x = np.arange(len(labels))
    w = 0.34
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    b1 = ax.bar(x - w / 2, v_b, w, label="До оптимізації (Baseline: k=3, no graph/rerank)", color="#8C96A0")
    b2 = ax.bar(x + w / 2, v_a, w, label="Після оптимізації (k=5 + Rerank + Graph + Policy)", color="#2E7D32")
    for bars in (b1, b2):
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + 0.02, f"{h:.2f}", ha="center", fontsize=8.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Значення метрики")
    ax.set_title("Оптимізація RAG-системи «до / після» на 32 тестах (ЛР 11)")
    ax.legend(bbox_to_anchor=(0.5, 1.13), loc="lower center", ncol=2, frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    os.makedirs(DOCS_DIR, exist_ok=True)
    fig.savefig(os.path.join(DOCS_DIR, "fig_rag_optimization.png"), dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rag = RAGPipeline()
    tests = [json.loads(l) for l in open(RAG_EVAL_PATH, encoding="utf-8") if l.strip()]

    # Результат 2
    gvt = eval_graph_vs_text(rag)
    print(f"[Result 2] Text-only cov={gvt['text_only_avg_cov']} ({gvt['text_only_avg_tokens']} tok) | "
          f"Text+Graph cov={gvt['text_graph_avg_cov']} ({gvt['text_graph_avg_tokens']} tok, +{gvt['token_overhead_pct']}%)")

    # Результат 4 + 5: Baseline ("до") vs Optimized ("після")
    baseline = run_eval_suite(
        rag, tests, "Baseline (до оптимізації)",
        top_k=3, use_graph=False, use_rerank=False, abst_thr=0.22, strict_inj=False,
    )
    optimized = run_eval_suite(
        rag, tests, "Optimized (після оптимізації)",
        top_k=5, use_graph=True, use_rerank=True, abst_thr=0.36, strict_inj=True,
    )
    agree = compute_judge_agreement()
    plot_optimization(baseline, optimized)

    out = {
        "total_tests": len(tests),
        "judge_human_agreement": agree,
        "baseline_before": baseline,
        "optimized_after": optimized,
    }
    with open(os.path.join(OUT_DIR, "rag_eval_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    print(f"\n[Result 4-5] Judge-Human agreement (12 samples): {agree['exact_agreement']*100:.1f}%")
    for cfg in (baseline, optimized):
        print(f"  {cfg['config']:30s} | Faith={cfg['faithfulness']:.3f} | CtxRec={cfg['context_recall']:.3f} | "
              f"CitAcc={cfg['citation_accuracy']:.3f} | Abst={cfg['abstention_rate']:.3f} | "
              f"InjDef={cfg['injection_defense_rate']:.3f} | p50={cfg['p50_latency_ms']}ms | "
              f"p95={cfg['p95_latency_ms']}ms | tok={cfg['avg_tokens']} | fails={cfg['failures_count']}")


if __name__ == "__main__":
    main()
