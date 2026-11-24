#!/usr/bin/env python3
"""
ЛР 10, Результат 5: оцінювання 4 конфігурацій пошуку (BM25, Dense,
Hybrid RRF k=60, Hybrid + Rerank) на золотому наборі eval/gold.jsonl (45 запитів,
включно з 6 без відповіді), обчислення recall@5, recall@10, MRR, nDCG@10,
затримки та узгодженості двох розмітників (Cohen's kappa).

Запуск: python3 src/eval_metrics.py [--backend local|neural]
Вихід:  outputs/eval_results.json, docs/fig_eval_comparison.png
"""
import argparse
import json
import math
import os
import sys
import time
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from hybrid import HybridRetriever, load_corpus

GOLD_PATH = os.path.join(ROOT, "eval", "gold.jsonl")
AGREE_PATH = os.path.join(ROOT, "eval", "annotator_agreement.jsonl")
OUT_DIR = os.path.join(ROOT, "outputs")
DOCS_DIR = os.path.join(ROOT, "docs")


def compute_cohens_kappa(path: str):
    rows = [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]
    n = len(rows)
    a1 = [r["annotator_1"] for r in rows]
    a2 = [r["annotator_2"] for r in rows]
    qids = sorted({r["qid"] for r in rows})
    po = sum(1 for x, y in zip(a1, a2) if x == y) / n
    p1_yes = sum(a1) / n
    p2_yes = sum(a2) / n
    pe = p1_yes * p2_yes + (1 - p1_yes) * (1 - p2_yes)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return {
        "annotated_queries": len(qids),
        "judged_pairs": n,
        "observed_agreement_po": round(po, 4),
        "expected_agreement_pe": round(pe, 4),
        "cohens_kappa": round(kappa, 4),
    }


def ndcg_at_k(retrieved_docs: list, relevant_set: set, k: int = 10) -> float:
    dcg = 0.0
    seen = set()
    rank = 0
    for d in retrieved_docs:
        if d in seen:
            continue
        seen.add(d)
        rank += 1
        if rank > k:
            break
        if d in relevant_set:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def eval_config(name, fn, gold_queries, no_answer_threshold):
    rec5_list, rec10_list, mrr_list, ndcg10_list, lat_list = [], [], [], [], []
    no_ans_total = 0
    no_ans_rejected = 0

    for g in gold_queries:
        t0 = time.perf_counter()
        hits = fn(g["query"])
        lat_ms = (time.perf_counter() - t0) * 1000.0
        lat_list.append(lat_ms)

        top_score = hits[0][0] if hits else 0.0
        if not g["answerable"]:
            no_ans_total += 1
            if top_score < no_answer_threshold:
                no_ans_rejected += 1
            continue

        rel = set(g["relevant_docs"])
        dedup_docs = []
        for _, _, rec in hits:
            if rec["doc_id"] not in dedup_docs:
                dedup_docs.append(rec["doc_id"])

        r5 = len(set(dedup_docs[:5]) & rel) / len(rel)
        r10 = len(set(dedup_docs[:10]) & rel) / len(rel)
        rr = 0.0
        for rank, d in enumerate(dedup_docs[:10], start=1):
            if d in rel:
                rr = 1.0 / rank
                break
        ndcg = ndcg_at_k(dedup_docs, rel, k=10)

        rec5_list.append(r5)
        rec10_list.append(r10)
        mrr_list.append(rr)
        ndcg10_list.append(ndcg)

    return {
        "config": name,
        "recall@5": round(float(np.mean(rec5_list)), 4),
        "recall@10": round(float(np.mean(rec10_list)), 4),
        "MRR": round(float(np.mean(mrr_list)), 4),
        "nDCG@10": round(float(np.mean(ndcg10_list)), 4),
        "no_answer_rejection": round(no_ans_rejected / max(1, no_ans_total), 4),
        "avg_latency_ms": round(float(np.mean(lat_list)), 3),
        "p95_latency_ms": round(float(np.percentile(lat_list, 95)), 3),
    }


def plot_eval(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configs = [r["config"] for r in results]
    metrics = ["recall@5", "recall@10", "MRR", "nDCG@10"]
    x = np.arange(len(configs))
    width = 0.19
    colors = ["#4C78A8", "#72B7B2", "#2E7D32", "#E67E22"]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for i, m in enumerate(metrics):
        vals = [r[m] for r in results]
        bars = ax.bar(x + (i - 1.5) * width, vals, width, label=m, color=colors[i])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(configs, fontsize=10)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Значення метрики")
    ax.set_title("Порівняння 4 конфігурацій пошуку на золотому наборі (39 відповідаємих + 6 без відповіді)")
    ax.legend(loc="lower right", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    os.makedirs(DOCS_DIR, exist_ok=True)
    fig.savefig(os.path.join(DOCS_DIR, "fig_eval_comparison.png"), dpi=140, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["local", "neural"], default="local")
    args = parser.parse_args()

    corpus = load_corpus()
    gold = [json.loads(ln) for ln in open(GOLD_PATH, encoding="utf-8") if ln.strip()]
    kappa_info = compute_cohens_kappa(AGREE_PATH)

    ret = HybridRetriever(corpus, backend=args.backend, rrf_k=60, seed=42)

    # Пороги відсікання запитів без відповіді (калібруються за шкалою кожної конфігурації)
    configs = [
        ("BM25", lambda q: ret.search_bm25(q, top_k=20), 6.5),
        ("Dense", lambda q: ret.search_dense(q, top_k=20), 0.42),
        ("Hybrid (RRF)", lambda q: ret.search_hybrid(q, top_k=20, rerank=False), 0.030),
        ("Hybrid + Rerank", lambda q: ret.search_hybrid(q, top_k=10, rerank=True), 0.34),
    ]

    results = [eval_config(name, fn, gold, thr) for name, fn, thr in configs]
    plot_eval(results)

    summary = {
        "gold_total_queries": len(gold),
        "gold_answerable": sum(1 for g in gold if g["answerable"]),
        "gold_no_answer": sum(1 for g in gold if not g["answerable"]),
        "annotator_agreement": kappa_info,
        "configurations": results,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "eval_results.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print("Cohen's kappa:", json.dumps(kappa_info, ensure_ascii=False))
    print(f"\n{'Конфігурація':18s} | {'R@5':6s} | {'R@10':6s} | {'MRR':6s} | {'nDCG@10':7s} | {'NoAns':6s} | {'Avg(ms)':7s}")
    print("-" * 74)
    for r in results:
        print(f"{r['config']:18s} | {r['recall@5']:6.4f} | {r['recall@10']:6.4f} | {r['MRR']:6.4f} | "
              f"{r['nDCG@10']:7.4f} | {r['no_answer_rejection']:6.4f} | {r['avg_latency_ms']:7.3f}")


if __name__ == "__main__":
    main()
