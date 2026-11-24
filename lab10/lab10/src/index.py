#!/usr/bin/env python3
"""
ЛР 10, Результат 3: побудова векторного індексу (HNSW: FAISS у --backend neural
або детермінований HNSW-індекс у --backend local) для 2 моделей embeddings,
замір часу побудови/пошуку, порівняння на 20 запитах (recall@5, затримка)
та верифікація процедури оновлення (upsert/delete) на 5 документах.

Запуск: python3 src/index.py [--backend local|neural]
Вихід:  outputs/embeddings_results.json
"""
import argparse
import heapq
import json
import os
import random
import sys
import time
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from embeddings import get_embedder

CORPUS_PATH = os.path.join(ROOT, "data", "corpus.jsonl")
OUT_DIR = os.path.join(ROOT, "outputs")

# 20 тестових запитів (українська морфологія + латинські терміни + точні коди)
INDEX_TEST_QUERIES = [
    ("Q01", "Яке ураження короїдом на виділі V-012?", ["DOC-01"]),
    ("Q02", "Скільки гектарів займає лісництво Бескидське LS-02?", ["DOC-02"]),
    ("Q03", "Де зафіксовано найвищий відсоток пошкодження дерев 28.7%?", ["DOC-03"]),
    ("Q04", "Чому виділ V-301 потребує першочергового наземного обстеження?", ["DOC-04", "DOC-09"]),
    ("Q05", "Поріг правила R5 для класифікації ураженого виділу Ips typographus", ["DOC-05"]),
    ("Q06", "Гриб-антагоніст Phlebiopsis gigantea проти кореневої губки Heterobasidion", ["DOC-06"]),
    ("Q07", "Три метеорологічні умови оголошення високого пожежного ризику R8", ["DOC-07"]),
    ("Q08", "Які дати вересня 2026 перевищили поріг пожежної небезпеки?", ["DOC-08"]),
    ("Q09", "Формула розрахунку NDVI за каналами супутника Sentinel-2", ["DOC-09"]),
    ("Q10", "З якого віку хвойні насадження вважаються стиглими?", ["DOC-10"]),
    ("Q11", "На скільки кубічних метрів MainFelling_2026_V102 перевищує квоту?", ["DOC-11"]),
    ("Q12", "Скільки саджанців заплановано у програмі весняного садіння 2027?", ["DOC-12"]),
    ("Q13", "Який сезонний ліміт діє на збір білих грибів і чорниці?", ["DOC-13"]),
    ("Q14", "Чому монокультури ялини європейської Picea abies вразливі до вітровалів?", ["DOC-14"]),
    ("Q15", "Які лісники мають найбільше навантаження за проблемними виділами?", ["DOC-15"]),
    ("Q16", "Які вимоги сертифікації FSC щодо буферних зон і мертвої деревини?", ["DOC-16"]),
    ("Q17", "Похибка оцінки запасу деревини за допомогою LiDAR", ["DOC-17"]),
    ("Q18", "Чому заборонено гусеничне трелювання на схилах крутіше 20 градусів?", ["DOC-18"]),
    ("Q19", "Скільки тонн CO2 поглинає один кубічний метр приросту деревини?", ["DOC-19"]),
    ("Q20", "Коли діє сезон тиші біля гніздувань чорного лелеки Ciconia nigra?", ["DOC-20"]),
]


class LocalHNSWIndex:
    """
    Компактний навігаційний графовий індекс HNSW (ієрархічний малий світ)
    із параметрами M, efConstruction, efSearch та підтримкою upsert/delete (tombstones).
    """

    def __init__(self, dim: int, M: int = 16, ef_construction: int = 64, ef_search: int = 48, seed: int = 42):
        self.dim = dim
        self.M = M
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.rng = random.Random(seed)
        self.vectors = {}      # int_id -> np.ndarray (L2-normalized)
        self.metadata = {}     # int_id -> dict
        self.chunk_to_id = {}  # chunk_id -> int_id
        self.deleted = set()
        self.neighbors = {}    # int_id -> list[int_id] (базовий шар)
        self.next_id = 0

    def _sim(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))

    def _search_layer(self, qvec: np.ndarray, ef: int):
        active_ids = [i for i in self.vectors if i not in self.deleted]
        if not active_ids:
            return []
        # Старт із 3 випадкових детермінованих точок входу + жадібний обхід графа
        entry_points = active_ids[:min(3, len(active_ids))]
        visited = set(entry_points)
        cand = []  # max-heap by sim -> store (-sim, nid)
        best = []  # min-heap by sim -> store (sim, nid)
        for ep in entry_points:
            s = self._sim(qvec, self.vectors[ep])
            heapq.heappush(cand, (-s, ep))
            heapq.heappush(best, (s, ep))

        while cand:
            neg_s, curr = heapq.heappop(cand)
            curr_s = -neg_s
            worst_best = best[0][0] if len(best) >= ef else -1e9
            if curr_s < worst_best:
                break
            for nb in self.neighbors.get(curr, ()):
                if nb in visited or nb in self.deleted:
                    continue
                visited.add(nb)
                s = self._sim(qvec, self.vectors[nb])
                if len(best) < ef or s > best[0][0]:
                    heapq.heappush(cand, (-s, nb))
                    heapq.heappush(best, (s, nb))
                    if len(best) > ef:
                        heapq.heappop(best)

        best.sort(key=lambda x: -x[0])
        return best

    def add(self, vectors: np.ndarray, records: list):
        for vec, rec in zip(vectors, records):
            cid = rec["chunk_id"]
            if cid in self.chunk_to_id:
                old_id = self.chunk_to_id[cid]
                self.deleted.add(old_id)
            nid = self.next_id
            self.next_id += 1
            self.vectors[nid] = vec
            self.metadata[nid] = rec
            self.chunk_to_id[cid] = nid
            self.neighbors[nid] = []

            if len(self.vectors) - len(self.deleted) > 1:
                cands = self._search_layer(vec, self.ef_construction)
                chosen = [cid_nb for _, cid_nb in cands if cid_nb != nid][:self.M]
                self.neighbors[nid] = chosen
                for nb in chosen:
                    self.neighbors[nb].append(nid)
                    if len(self.neighbors[nb]) > self.M * 2:
                        nb_vec = self.vectors[nb]
                        self.neighbors[nb].sort(key=lambda x: -self._sim(nb_vec, self.vectors[x]))
                        self.neighbors[nb] = self.neighbors[nb][:self.M]

    def delete_by_doc_id(self, doc_id: str) -> int:
        removed = 0
        for nid, rec in list(self.metadata.items()):
            if nid not in self.deleted and rec["doc_id"] == doc_id:
                self.deleted.add(nid)
                self.chunk_to_id.pop(rec["chunk_id"], None)
                removed += 1
        return removed

    def upsert_document(self, doc_id: str, new_vectors: np.ndarray, new_records: list):
        deleted_old = self.delete_by_doc_id(doc_id)
        self.add(new_vectors, new_records)
        return deleted_old, len(new_records)

    def active_count(self) -> int:
        return len(self.vectors) - len(self.deleted)

    def search(self, qvec: np.ndarray, top_k: int = 5):
        res = self._search_layer(qvec, max(self.ef_search, top_k))
        return [(score, self.metadata[nid]) for score, nid in res[:top_k]]


class FaissHNSWWrapper:
    """Обгортка над faiss.IndexHNSWFlat (використовується у --backend neural)."""

    def __init__(self, dim: int, M: int = 32, ef_construction: int = 64, ef_search: int = 64):
        import faiss

        self.dim = dim
        self.M = M
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.index = faiss.IndexHNSWFlat(dim, M, faiss.METRIC_INNER_PRODUCT)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        self.records = []
        self.deleted = set()

    def add(self, vectors: np.ndarray, records: list):
        self.index.add(vectors)
        self.records.extend(records)

    def delete_by_doc_id(self, doc_id: str) -> int:
        removed = 0
        for idx, rec in enumerate(self.records):
            if idx not in self.deleted and rec["doc_id"] == doc_id:
                self.deleted.add(idx)
                removed += 1
        return removed

    def upsert_document(self, doc_id: str, new_vectors: np.ndarray, new_records: list):
        old = self.delete_by_doc_id(doc_id)
        self.add(new_vectors, new_records)
        return old, len(new_records)

    def active_count(self) -> int:
        return len(self.records) - len(self.deleted)

    def search(self, qvec: np.ndarray, top_k: int = 5):
        k_fetch = min(len(self.records), top_k + len(self.deleted) + 10)
        D, I = self.index.search(qvec.reshape(1, -1), k_fetch)
        out = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1 or idx in self.deleted:
                continue
            out.append((float(score), self.records[idx]))
            if len(out) >= top_k:
                break
        return out


def load_corpus():
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def benchmark_model(model_key: str, corpus: list, backend: str = "local"):
    embedder = get_embedder(model_key, backend=backend, seed=42)
    texts = [f"{r['title']}. {r['section']}. {r['text']}" for r in corpus]

    t0 = time.perf_counter()
    embedder.fit(texts)
    vecs = embedder.encode(texts, is_query=False)
    dim = vecs.shape[1]

    M, ef_c, ef_s = (32, 64, 64) if backend == "neural" else (16, 64, 48)
    idx = FaissHNSWWrapper(dim, M, ef_c, ef_s) if backend == "neural" else LocalHNSWIndex(dim, M, ef_c, ef_s, seed=42)
    idx.add(vecs, corpus)
    build_ms = (time.perf_counter() - t0) * 1000.0

    recalls, mrrs, latencies = [], [], []
    for qid, qtext, rel_docs in INDEX_TEST_QUERIES:
        tq0 = time.perf_counter()
        qvec = embedder.encode([qtext], is_query=True)[0]
        hits = idx.search(qvec, top_k=5)
        lat_ms = (time.perf_counter() - tq0) * 1000.0
        latencies.append(lat_ms)

        got_docs = []
        for _, rec in hits:
            if rec["doc_id"] not in got_docs:
                got_docs.append(rec["doc_id"])
        recalls.append(len(set(got_docs) & set(rel_docs)) / len(rel_docs))
        rr = 0.0
        for rank, (_, rec) in enumerate(hits, start=1):
            if rec["doc_id"] in rel_docs:
                rr = 1.0 / rank
                break
        mrrs.append(rr)

    return {
        "model_key": model_key,
        "model_name": embedder.name,
        "dim": int(dim),
        "index_type": "FAISS IndexHNSWFlat" if backend == "neural" else "LocalHNSWIndex (Cosine)",
        "M": M,
        "efConstruction": ef_c,
        "efSearch": ef_s,
        "vectors_indexed": idx.active_count(),
        "build_time_ms": round(build_ms, 2),
        "avg_query_ms": round(float(np.mean(latencies)), 3),
        "p95_query_ms": round(float(np.percentile(latencies, 95)), 3),
        "recall@5_20q": round(float(np.mean(recalls)), 4),
        "mrr@5_20q": round(float(np.mean(mrrs)), 4),
    }, embedder, idx


def verify_upsert_delete(embedder, idx):
    """Крок 4 (C4): перевірка upsert/delete на 5 документах."""
    before_cnt = idx.active_count()
    ops_log = []

    # 1-2: Оновлення (upsert) двох існуючих документів (DOC-01 та DOC-11)
    upd_docs = [
        ("DOC-01", "Оновлена таксація LS-01", "Переоцінка V-012",
         "Оновлення листопада 2026: на виділі V-012 завершено санітарну рубку 120 м3, частка ураження знизилася до 2.1 відсотка."),
        ("DOC-11", "Оновлений акт аудиту V-102", "Коригування квоти",
         "Аудит V-102 закрито: обсяг рубки MainFelling_2026_V102 зменшено з 694 м3 до 540 м3 у межах квоти 620 м3."),
    ]
    for did, title, sec, txt in upd_docs:
        rec = {"chunk_id": f"{did}_UPD01", "doc_id": did, "title": title, "section": sec,
               "type": "audit", "date": "2026-11-20", "sensitivity": "internal",
               "source_url": f"https://hub.forest.local/kb/{did.lower()}-upd", "text": txt}
        vec = embedder.encode([f"{title}. {sec}. {txt}"], is_query=False)
        old_n, new_n = idx.upsert_document(did, vec, [rec])
        ops_log.append({"op": "upsert_update", "doc_id": did, "removed_chunks": old_n, "added_chunks": new_n})

    # 3-4: Додавання (upsert) двох нових документів (DOC-29 та DOC-30)
    new_docs = [
        ("DOC-29", "Дроновий моніторинг термальними камерами", "Виявлення тління",
         "Тепловізійні БПЛА дозволяють виявляти підземне тління торфовищ і лісової підстилки за 4 години до відкритого полум'я."),
        ("DOC-30", "Облік біомаси для котелень на деревній трісці", "Енергетична тріска",
         "Порубкові рештки після санітарних рубок переробляються на паливну тріску вологістю до 30 відсотків для комунальних котелень."),
    ]
    for did, title, sec, txt in new_docs:
        rec = {"chunk_id": f"{did}_C01", "doc_id": did, "title": title, "section": sec,
               "type": "technology", "date": "2026-11-22", "sensitivity": "public",
               "source_url": f"https://hub.forest.local/kb/{did.lower()}", "text": txt}
        vec = embedder.encode([f"{title}. {sec}. {txt}"], is_query=False)
        old_n, new_n = idx.upsert_document(did, vec, [rec])
        ops_log.append({"op": "upsert_insert", "doc_id": did, "removed_chunks": old_n, "added_chunks": new_n})

    # 5: Видалення (delete) документа DOC-24
    del_n = idx.delete_by_doc_id("DOC-24")
    ops_log.append({"op": "delete", "doc_id": "DOC-24", "removed_chunks": del_n, "added_chunks": 0})

    # Перевірка пошуком: новий DOC-29 знаходиться, видалений DOC-24 не з'являється
    q_new = embedder.encode(["тепловізійні БПЛА тління підстилки"], is_query=True)[0]
    top_new = [r["doc_id"] for _, r in idx.search(q_new, top_k=5)]
    q_del = embedder.encode(["несанкціонований збір чорниці металеві гребінки LS-03 65 кг"], is_query=True)[0]
    top_del = [r["doc_id"] for _, r in idx.search(q_del, top_k=5)]

    return {
        "vectors_before": before_cnt,
        "vectors_after": idx.active_count(),
        "operations_5_docs": ops_log,
        "new_doc_DOC29_found_in_top5": "DOC-29" in top_new,
        "deleted_doc_DOC24_absent_from_top5": "DOC-24" not in top_del,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["local", "neural"], default="local")
    args = parser.parse_args()

    corpus = load_corpus()
    res_a, _, _ = benchmark_model("model_a", corpus, backend=args.backend)
    res_b, emb_b, idx_b = benchmark_model("model_b", corpus, backend=args.backend)
    upsert_report = verify_upsert_delete(emb_b, idx_b)

    out = {"models": [res_a, res_b], "upsert_delete_check": upsert_report}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "embeddings_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    print(f"{'Модель':22s} | {'Dim':4s} | {'M':3s} | {'efS':4s} | {'Build(ms)':9s} | {'AvgQ(ms)':8s} | {'Recall@5':8s} | {'MRR@5':6s}")
    print("-" * 82)
    for r in out["models"]:
        print(f"{r['model_name']:22s} | {r['dim']:4d} | {r['M']:3d} | {r['efSearch']:4d} | "
              f"{r['build_time_ms']:9.2f} | {r['avg_query_ms']:8.3f} | {r['recall@5_20q']:8.4f} | {r['mrr@5_20q']:6.4f}")
    print("\nПеревірка upsert/delete на 5 документах:")
    print(json.dumps(upsert_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
