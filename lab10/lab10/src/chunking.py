#!/usr/bin/env python3
"""
ЛР 10, Результат 2: реалізація та порівняння >=3 стратегій chunking
(fixed_overlap, by_headers, hierarchical) на однаковій моделі embeddings
і 10 тестових запитах (recall@5 та середній розмір контексту).

Запуск: python3 src/chunking.py [--backend local|neural]
Вихід:  outputs/chunking_results.json, docs/fig_chunking_cmp.png
"""
import argparse
import glob
import json
import os
import re
import sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from embeddings import get_embedder

KB_DIR = os.path.join(ROOT, "kb")
OUT_DIR = os.path.join(ROOT, "outputs")
DOCS_DIR = os.path.join(ROOT, "docs")

# 10 тестових запитів для порівняння стратегій chunking (з еталонними doc_id)
CHUNKING_TEST_QUERIES = [
    ("CQ-01", "Яка частка ураження короїдом-типографом на виділі V-012?", ["DOC-01"]),
    ("CQ-02", "Умови високого класу пожежної небезпеки за правилом R8", ["DOC-07", "DOC-08"]),
    ("CQ-03", "Яке перевищення квоти виявлено на виділі V-102?", ["DOC-11", "DOC-02"]),
    ("CQ-04", "Який поріг індексу NDVI для першочергового обстеження лісів?", ["DOC-09"]),
    ("CQ-05", "Які рубки головного користування не мають плану лісовідновлення?", ["DOC-12", "DOC-03"]),
    ("CQ-06", "Які сезонні ліміти діють на збір білих грибів, чорниці та звіробою?", ["DOC-13"]),
    ("CQ-07", "Як біопрепарат Phlebiopsis gigantea захищає пні від кореневого гниття?", ["DOC-06"]),
    ("CQ-08", "Який мінімальний вік стиглості хвойних деревостанів для рубок?", ["DOC-10"]),
    ("CQ-09", "Коли діє сезон тиші в охоронних зонах гніздування чорного лелеки?", ["DOC-20"]),
    ("CQ-10", "Яка точність визначення запасу деревини за допомогою LiDAR?", ["DOC-17"]),
]


def load_clean_docs():
    docs = []
    for path in sorted(glob.glob(os.path.join(KB_DIR, "DOC-*.md"))):
        doc_id = os.path.basename(path).replace(".md", "")
        with open(path, encoding="utf-8") as fh:
            text = fh.read().strip()
        lines = text.splitlines()
        title = lines[0].lstrip("# ").strip() if lines else doc_id
        docs.append({"doc_id": doc_id, "title": title, "text": text})
    return docs


def chunk_fixed_overlap(docs, chunk_words=60, overlap_words=15):
    """Стратегія 1: фіксоване ковзне вікно слів із перекриттям (overlap = 25%)."""
    chunks = []
    step = max(1, chunk_words - overlap_words)
    for d in docs:
        body = re.sub(r"^#+\s*", "", d["text"], flags=re.M)
        words = body.split()
        idx = 0
        cnum = 1
        while idx < len(words):
            piece = " ".join(words[idx:idx + chunk_words])
            chunks.append({
                "chunk_id": f"{d['doc_id']}_FX{cnum:02d}",
                "doc_id": d["doc_id"],
                "section": f"window_{cnum}",
                "text": piece,
                "context_text": piece,
            })
            cnum += 1
            if idx + chunk_words >= len(words):
                break
            idx += step
    return chunks


def chunk_by_headers(docs):
    """Стратегія 2: розбиття за Markdown-заголовками секцій (##)."""
    chunks = []
    for d in docs:
        sec_title = "Загальне"
        buf = []
        cnum = 1
        for ln in d["text"].splitlines():
            s = ln.strip()
            if s.startswith("# "):
                continue
            if s.startswith("Дата публікації:"):
                continue
            if s.startswith("## "):
                if buf:
                    txt = f"{d['title']} — {sec_title}. " + " ".join(buf)
                    chunks.append({
                        "chunk_id": f"{d['doc_id']}_HD{cnum:02d}",
                        "doc_id": d["doc_id"],
                        "section": sec_title,
                        "text": txt,
                        "context_text": txt,
                    })
                    cnum += 1
                    buf = []
                sec_title = s[3:].strip()
            elif s:
                buf.append(s)
        if buf:
            txt = f"{d['title']} — {sec_title}. " + " ".join(buf)
            chunks.append({
                "chunk_id": f"{d['doc_id']}_HD{cnum:02d}",
                "doc_id": d["doc_id"],
                "section": sec_title,
                "text": txt,
                "context_text": txt,
            })
    return chunks


def chunk_hierarchical(docs, child_words=32, child_overlap=8):
    """
    Стратегія 3: ієрархічне розбиття (Parent-Child).
    Пошук виконується за компактними дочірніми чанками з префіксом [Документ > Секція],
    а в контекст повертається повна батьківська секція.
    """
    parents = chunk_by_headers(docs)
    chunks = []
    step = max(1, child_words - child_overlap)
    for p in parents:
        words = p["text"].split()
        idx = 0
        cnum = 1
        while idx < len(words):
            child_txt = " ".join(words[idx:idx + child_words])
            if idx > 0:
                child_txt = f"[{p['section']}] " + child_txt
            chunks.append({
                "chunk_id": f"{p['chunk_id']}_CH{cnum:02d}",
                "parent_id": p["chunk_id"],
                "doc_id": p["doc_id"],
                "section": p["section"],
                "text": child_txt,
                "context_text": p["text"],  # батьківський контекст при видачі
            })
            cnum += 1
            if idx + child_words >= len(words):
                break
            idx += step
    return chunks


def evaluate_strategy(name, chunks, backend="local"):
    embedder = get_embedder("model_b", backend=backend, seed=42)
    texts = [c["text"] for c in chunks]
    embedder.fit(texts)
    mat = embedder.encode(texts, is_query=False)

    recalls, mrrs = [], []
    per_query = []
    for qid, qtext, rel_docs in CHUNKING_TEST_QUERIES:
        qvec = embedder.encode([qtext], is_query=True)[0]
        scores = mat @ qvec
        top_idx = np.argsort(-scores)[:5]
        retrieved_docs = []
        for i in top_idx:
            did = chunks[i]["doc_id"]
            if did not in retrieved_docs:
                retrieved_docs.append(did)
        hits = len(set(retrieved_docs) & set(rel_docs))
        rec = hits / len(rel_docs)
        rr = 0.0
        for rank, i in enumerate(top_idx, start=1):
            if chunks[i]["doc_id"] in rel_docs:
                rr = 1.0 / rank
                break
        recalls.append(rec)
        mrrs.append(rr)
        per_query.append({"qid": qid, "recall@5": round(rec, 3), "rr": round(rr, 3),
                          "top_docs": [chunks[i]["doc_id"] for i in top_idx]})

    avg_search_words = round(sum(len(c["text"].split()) for c in chunks) / len(chunks), 1)
    avg_ctx_words = round(sum(len(c["context_text"].split()) for c in chunks) / len(chunks), 1)
    avg_ctx_chars = round(sum(len(c["context_text"]) for c in chunks) / len(chunks), 1)
    return {
        "strategy": name,
        "embedder": embedder.name,
        "num_chunks": len(chunks),
        "avg_search_chunk_words": avg_search_words,
        "avg_context_words": avg_ctx_words,
        "avg_context_chars": avg_ctx_chars,
        "recall@5": round(float(np.mean(recalls)), 4),
        "mrr@5": round(float(np.mean(mrrs)), 4),
        "per_query": per_query,
    }


def plot_comparison(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [r["strategy"] for r in results]
    recalls = [r["recall@5"] for r in results]
    ctx_words = [r["avg_context_words"] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    colors = ["#4C78A8", "#2E7D32", "#E67E22"]

    bars1 = ax1.bar(names, recalls, color=colors, width=0.55)
    ax1.set_ylim(0, 1.12)
    ax1.set_ylabel("Recall@5")
    ax1.set_title("Якість пошуку (Recall@5 на 10 запитах)")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    for b, v in zip(bars1, recalls):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.03, f"{v:.3f}", ha="center", fontweight="bold")

    bars2 = ax2.bar(names, ctx_words, color=colors, width=0.55)
    ax2.set_ylabel("Середній розмір контексту (слів)")
    ax2.set_title("Середній розмір контексту фрагмента")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    for b, v in zip(bars2, ctx_words):
        ax2.text(b.get_x() + b.get_width() / 2, v + 2.0, f"{v:.1f}", ha="center", fontweight="bold")

    plt.tight_layout()
    os.makedirs(DOCS_DIR, exist_ok=True)
    out_png = os.path.join(DOCS_DIR, "fig_chunking_cmp.png")
    fig.savefig(out_png, dpi=140, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["local", "neural"], default="local")
    args = parser.parse_args()

    docs = load_clean_docs()
    strategies = [
        ("fixed_overlap", chunk_fixed_overlap(docs, chunk_words=60, overlap_words=15)),
        ("by_headers", chunk_by_headers(docs)),
        ("hierarchical", chunk_hierarchical(docs, child_words=32, child_overlap=8)),
    ]

    results = [evaluate_strategy(name, ch, backend=args.backend) for name, ch in strategies]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "chunking_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    plot_comparison(results)

    print(f"{'Стратегія':16s} | {'Чанків':6s} | {'Пошук(сл)':9s} | {'Контекст(сл)':12s} | {'Recall@5':8s} | {'MRR@5':6s}")
    print("-" * 72)
    for r in results:
        print(f"{r['strategy']:16s} | {r['num_chunks']:6d} | {r['avg_search_chunk_words']:9.1f} | "
              f"{r['avg_context_words']:12.1f} | {r['recall@5']:8.4f} | {r['mrr@5']:6.4f}")


if __name__ == "__main__":
    main()
