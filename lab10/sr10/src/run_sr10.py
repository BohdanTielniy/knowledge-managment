#!/usr/bin/env python3
"""
СР 10. Експеримент із 3 моделями embeddings на 30 запитах із золотою розміткою:
  1. sentence-transformers/all-MiniLM-L6-v2                     (англомовна, 384d)
  2. sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (мультимовна, 384d)
  3. intfloat/multilingual-e5-small                             (мультимовна асиметрична, 384d)

Обчислює: Recall@5, MRR@5, build_ms, avg_query_ms, p95_query_ms, розмір індексу FAISS (KB)
та автоматично знаходить усі запити, де моделі розходяться (>= 5 розбіжностей).

Запуск у Docker: docker compose run --rm sr10
Вихід: outputs/sr10_results.json, outputs/sr10_summary.txt, outputs/fig_sr10_embeddings.png
"""
import json
import os
import tempfile
import time
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORPUS_PATH = os.path.join(ROOT, "data", "corpus.jsonl")
GOLD_PATH = os.path.join(ROOT, "eval", "gold_30.jsonl")
OUT_DIR = os.path.join(ROOT, "outputs")

MODELS = [
    ("en_MiniLM_L6", "sentence-transformers/all-MiniLM-L6-v2", "English-only", False),
    ("multi_MiniLM_L12", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "Multilingual", False),
    ("multi_e5_small", "intfloat/multilingual-e5-small", "Multilingual (query/passage)", True),
]


def evaluate_model(short_name, model_name, lang_type, is_e5, corpus, queries):
    print(f"\n=== Завантаження та індексація: {model_name} ===")
    model = SentenceTransformer(model_name)
    raw_texts = [f"{r['title']}. {r['section']}. {r['text']}" for r in corpus]
    passages = [f"passage: {t}" for t in raw_texts] if is_e5 else raw_texts

    t0 = time.perf_counter()
    vecs = np.asarray(model.encode(passages, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)
    dim = vecs.shape[1]
    index = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = 64
    index.hnsw.efSearch = 64
    index.add(vecs)
    build_ms = (time.perf_counter() - t0) * 1000.0

    # Точний розмір серіалізованого індексу FAISS на диску (KB)
    with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as tmp:
        tmp_path = tmp.name
    faiss.write_index(index, tmp_path)
    index_size_kb = round(os.path.getsize(tmp_path) / 1024.0, 1)
    os.remove(tmp_path)

    recalls, mrrs, latencies = [], [], []
    by_type = {"keyword": [], "paraphrase": [], "multi_hop": []}
    per_query = {}

    for g in queries:
        q_in = f"query: {g['query']}" if is_e5 else g["query"]
        tq0 = time.perf_counter()
        qvec = np.asarray(model.encode([q_in], normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)
        D, I = index.search(qvec, 15)
        latencies.append((time.perf_counter() - tq0) * 1000.0)

        top_docs = []
        for idx in I[0]:
            if idx == -1:
                continue
            did = corpus[idx]["doc_id"]
            if did not in top_docs:
                top_docs.append(did)
            if len(top_docs) >= 5:
                break

        rel = set(g["relevant_docs"])
        r5 = len(set(top_docs) & rel) / len(rel)
        rr = 0.0
        first_rank = None
        for rank, did in enumerate(top_docs, start=1):
            if did in rel:
                rr = 1.0 / rank
                first_rank = rank
                break

        recalls.append(r5)
        mrrs.append(rr)
        by_type[g["query_type"]].append(r5)
        per_query[g["qid"]] = {
            "recall@5": round(r5, 3),
            "rr": round(rr, 3),
            "first_rank": first_rank,
            "top5_docs": top_docs,
        }

    return {
        "short_name": short_name,
        "model_name": model_name,
        "lang_type": lang_type,
        "dim": int(dim),
        "vectors": len(corpus),
        "index_size_kb": index_size_kb,
        "build_time_ms": round(build_ms, 1),
        "avg_query_ms": round(float(np.mean(latencies)), 2),
        "p95_query_ms": round(float(np.percentile(latencies, 95)), 2),
        "recall@5": round(float(np.mean(recalls)), 4),
        "MRR": round(float(np.mean(mrrs)), 4),
        "recall@5_by_type": {k: round(float(np.mean(v)), 4) for k, v in by_type.items()},
        "per_query": per_query,
    }


def make_chart(models_res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [m["short_name"] for m in models_res]
    r5 = [m["recall@5"] for m in models_res]
    mrr = [m["MRR"] for m in models_res]
    lat = [m["avg_query_ms"] for m in models_res]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
    x = np.arange(len(labels))
    w = 0.34
    b1 = ax1.bar(x - w / 2, r5, w, label="Recall@5", color="#2E7D32")
    b2 = ax1.bar(x + w / 2, mrr, w, label="MRR", color="#4C78A8")
    for bars in (b1, b2):
        for b in bars:
            h = b.get_height()
            ax1.text(b.get_x() + b.get_width() / 2, h + 0.02, f"{h:.3f}", ha="center", fontsize=8.5, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.5)
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Метрика якості")
    ax1.set_title("Якість 3 моделей на 30 українських запитах")
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    b3 = ax2.bar(labels, lat, color=["#E67E22", "#4C78A8", "#2E7D32"], width=0.5)
    for b, v in zip(b3, lat):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f} мс", ha="center", fontsize=9, fontweight="bold")
    ax2.set_ylabel("Середній час запиту (мс)")
    ax2.set_title("Затримка пошуку (CPU, FAISS HNSW)")
    ax2.set_ylim(0, max(lat) * 1.25)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_sr10_embeddings.png"), dpi=160, facecolor="white")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    corpus = [json.loads(l) for l in open(CORPUS_PATH, encoding="utf-8") if l.strip()]
    queries = [json.loads(l) for l in open(GOLD_PATH, encoding="utf-8") if l.strip()]
    assert len(queries) == 30, f"Очікується 30 запитів, отримано {len(queries)}"

    models_res = [
        evaluate_model(sn, mn, lt, is_e5, corpus, queries)
        for sn, mn, lt, is_e5 in MODELS
    ]

    # Пошук запитів із найбільшими розбіжностями між моделями
    disagreements = []
    for g in queries:
        qid = g["qid"]
        r5s = [m["per_query"][qid]["recall@5"] for m in models_res]
        rrs = [m["per_query"][qid]["rr"] for m in models_res]
        spread = (max(r5s) - min(r5s)) + (max(rrs) - min(rrs))
        if spread > 0:
            disagreements.append({
                "qid": qid,
                "query_type": g["query_type"],
                "query": g["query"],
                "relevant_docs": g["relevant_docs"],
                "spread": round(spread, 3),
                "models": {
                    m["short_name"]: m["per_query"][qid] for m in models_res
                },
            })
    disagreements.sort(key=lambda x: -x["spread"])

    out = {
        "num_queries": len(queries),
        "num_chunks": len(corpus),
        "models": [{k: v for k, v in m.items() if k != "per_query"} for m in models_res],
        "disagreements_count": len(disagreements),
        "top_disagreements": disagreements[:10],
    }
    with open(os.path.join(OUT_DIR, "sr10_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    make_chart(models_res)

    lines = [
        f"СР 10: порівняння 3 моделей на {len(queries)} запитах ({len(corpus)} чанків, FAISS HNSW M=32)",
        f"{'Модель':18s} | {'Dim':4s} | {'Size(KB)':8s} | {'Build(ms)':9s} | {'AvgQ(ms)':8s} | {'R@5':6s} | {'MRR':6s}",
        "-" * 75,
    ]
    for m in out["models"]:
        lines.append(
            f"{m['short_name']:18s} | {m['dim']:4d} | {m['index_size_kb']:8.1f} | "
            f"{m['build_time_ms']:9.1f} | {m['avg_query_ms']:8.2f} | {m['recall@5']:6.4f} | {m['MRR']:6.4f}"
        )
    lines.append(f"\nЗнайдено запитів із розбіжностями: {len(disagreements)} (збережено топ-10 у sr10_results.json)")
    summary = "\n".join(lines)
    with open(os.path.join(OUT_DIR, "sr10_summary.txt"), "w", encoding="utf-8") as fh:
        fh.write(summary + "\n")
    print("\n" + summary)


if __name__ == "__main__":
    main()
