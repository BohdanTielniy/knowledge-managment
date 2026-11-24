#!/usr/bin/env python3
"""
Результат 1 (Рекомендаційний модуль: reco/recommender.py):
- Каталог із 28 реальних об'єктів знань Domain Knowledge Hub (документи, виділи, регламенти, OLAP-звіти).
- 4 конфігурації ранжування:
  1. Popularity (baseline)
  2. Graph Paths (2-hop шляхи по графу: User -> Forestry/Species/Topic -> Item)
  3. Embeddings kNN (косинусна схожість TF-IDF / векторних профілів)
  4. Hybrid RRF (Reciprocal Rank Fusion + зважене поєднання w_graph=0.55, w_emb=0.45, k=60)
- Фільтри якості та прав доступу: verified == True, свіжість (updated_at >= 2025-11-24), RBAC sensitivity.
"""
import math
import os
from collections import Counter
import numpy as np

SEED = 42

TOPICS = ["spruce_beetle", "fire_safety", "beech_fsc", "oak_quota", "nontimber_eco", "olap_finance"]
FORESTRIES = ["LS-01", "LS-02", "LS-03", "LS-04"]


def build_catalog():
    """28 об'єктів рекомендацій (24 валідні + 4 тестові для демонстрації фільтрів якості/прав)."""
    items = []
    topic_meta = {
        "spruce_beetle": ("Захист ялини від короїда-типографа", "Species_PiceaAbies", "Threat_BarkBeetle"),
        "fire_safety": ("Протипожежний моніторинг та протоколи ДСНС", "Species_PinusSylvestris", "Threat_CrownFire"),
        "beech_fsc": ("Сертифікація FSC та букові деревостани", "Species_FagusSylvatica", "Threat_RootRot"),
        "oak_quota": ("Контроль квот дубової деревини та приросту", "Species_QuercusRobur", "Threat_Drought"),
        "nontimber_eco": ("Збір недеревинних продуктів (гриби, ягоди)", "Species_AbiesAlba", "Product_Boletus"),
        "olap_finance": ("OLAP-аналітика виручки та маржинальності", "Metric_Revenue", "Metric_Margin"),
    }
    iid = 1
    for t_idx, topic in enumerate(TOPICS):
        title_base, sp_node, th_node = topic_meta[topic]
        for f_idx, fcode in enumerate(FORESTRIES):
            # Детермінований 6-вимірний embedding-профіль теми + легкий шум по лісництву
            vec = [0.1] * len(TOPICS)
            vec[t_idx] = 1.0
            vec[(t_idx + 1) % len(TOPICS)] = 0.25 if f_idx % 2 == 0 else 0.12
            norm = math.sqrt(sum(v * v for v in vec))
            vec = [round(v / norm, 4) for v in vec]
            items.append({
                "item_id": f"ITEM-{iid:02d}",
                "title": f"{title_base} ({fcode})",
                "topic": topic,
                "forestry": fcode,
                "graph_nodes": [fcode, sp_node, th_node],
                "embedding": vec,
                "verified": True,
                "updated_at": "2026-09-15",
                "sensitivity": "internal" if f_idx == 3 else "public",
            })
            iid += 1

    # 4 проблемні об'єкти для демонстрації фільтрів якості й прав (C2)
    items.extend([
        {"item_id": "ITEM-25", "title": "Неперевірена чернетка квот LS-01", "topic": "oak_quota",
         "forestry": "LS-01", "graph_nodes": ["LS-01", "Species_QuercusRobur"], "embedding": [0.1, 0.1, 0.1, 0.9, 0.1, 0.1],
         "verified": False, "updated_at": "2026-10-01", "sensitivity": "public"},
        {"item_id": "ITEM-26", "title": "Застарілий регламент 2022 р.", "topic": "fire_safety",
         "forestry": "LS-02", "graph_nodes": ["LS-02", "Threat_CrownFire"], "embedding": [0.1, 0.9, 0.1, 0.1, 0.1, 0.1],
         "verified": True, "updated_at": "2022-06-01", "sensitivity": "public"},
        {"item_id": "ITEM-27", "title": "Конфіденційний реєстр штрафів (restricted)", "topic": "olap_finance",
         "forestry": "LS-03", "graph_nodes": ["LS-03", "Metric_Revenue"], "embedding": [0.1, 0.1, 0.1, 0.1, 0.1, 0.9],
         "verified": True, "updated_at": "2026-10-10", "sensitivity": "restricted"},
        {"item_id": "ITEM-28", "title": "Новий звіт FSC-2026 (cold-start item)", "topic": "beech_fsc",
         "forestry": "LS-02", "graph_nodes": ["LS-02", "Species_FagusSylvatica", "Threat_RootRot"],
         "embedding": [0.1, 0.1, 0.95, 0.1, 0.1, 0.1],
         "verified": True, "updated_at": "2026-11-20", "sensitivity": "public"},
    ])
    return items


def filter_catalog(items, role="forester", min_date="2025-11-24"):
    """Фільтри якості та прав доступу (verified, свіжість, RBAC sensitivity)."""
    allowed_sens = {"public"} if role == "public_user" else ({"public", "internal"} if role == "forester" else {"public", "internal", "restricted"})
    passed, filtered_out = [], []
    for it in items:
        reasons = []
        if not it["verified"]:
            reasons.append("not_verified")
        if it["updated_at"] < min_date:
            reasons.append("stale_date")
        if it["sensitivity"] not in allowed_sens:
            reasons.append(f"sensitivity:{it['sensitivity']}")
        if reasons:
            filtered_out.append({"item_id": it["item_id"], "reasons": reasons})
        else:
            passed.append(it)
    return passed, filtered_out


def cos_sim(a, b):
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if (da and db) else 0.0


class ForestRecommender:
    def __init__(self, items, train_interactions):
        self.all_items = items
        self.item_map = {it["item_id"]: it for it in items}
        # Популярність лише за train-взаємодіями (без витоку з майбутнього!)
        self.pop_counts = Counter(x["item_id"] for x in train_interactions)
        self.total_train = max(1, len(train_interactions))
        self.user_hist = {}
        for x in train_interactions:
            self.user_hist.setdefault(x["user_id"], []).append(x["item_id"])

    def _user_profile(self, user_id, fallback_forestry=None, fallback_topic=None):
        hist = self.user_hist.get(user_id, [])
        if not hist:
            # Cold-start профіль користувача
            vec = [0.1] * len(TOPICS)
            if fallback_topic in TOPICS:
                vec[TOPICS.index(fallback_topic)] = 1.0
            nodes = Counter({fallback_forestry: 3}) if fallback_forestry else Counter()
            return vec, nodes, set()
        vecs = [self.item_map[iid]["embedding"] for iid in hist if iid in self.item_map]
        avg_vec = [sum(v[i] for v in vecs) / len(vecs) for i in range(len(TOPICS))]
        nodes = Counter()
        for iid in hist:
            if iid in self.item_map:
                for nd in self.item_map[iid]["graph_nodes"]:
                    nodes[nd] += 1
        return avg_vec, nodes, set(hist)

    def recommend(self, user_id, method="hybrid_rrf", k=10, role="forester",
                  fallback_forestry=None, fallback_topic=None, w_graph=0.55, w_emb=0.45, rrf_k=60):
        candidates, _ = filter_catalog(self.all_items, role=role)
        u_vec, u_nodes, seen = self._user_profile(user_id, fallback_forestry, fallback_topic)
        pool = [it for it in candidates if it["item_id"] not in seen]

        # 1. Popularity scores
        pop_rank = sorted(pool, key=lambda it: (self.pop_counts.get(it["item_id"], 0), it["item_id"]), reverse=True)
        if method == "popularity":
            return [{"item_id": it["item_id"], "score": self.pop_counts.get(it["item_id"], 0) / self.total_train, "path": ["Popularity"]} for it in pop_rank[:k]]

        # 2. Graph Paths scores (кількість спільних вузлів у 2-hop шляху User -> Node -> Item)
        g_scored = []
        for it in pool:
            shared = sorted(set(u_nodes.keys()) & set(it["graph_nodes"]))
            g_score = sum(u_nodes[nd] for nd in shared) / max(1, sum(u_nodes.values()))
            g_scored.append((g_score, shared, it))
        g_scored.sort(key=lambda x: (x[0], self.pop_counts.get(x[2]["item_id"], 0)), reverse=True)
        if method == "graph":
            return [{"item_id": it["item_id"], "score": round(sc, 4), "path": [user_id] + shared + [it["item_id"]]} for sc, shared, it in g_scored[:k]]

        # 3. Embeddings kNN scores
        e_scored = []
        for it in pool:
            e_sc = cos_sim(u_vec, it["embedding"])
            e_scored.append((e_sc, it))
        e_scored.sort(key=lambda x: (x[0], self.pop_counts.get(x[1]["item_id"], 0)), reverse=True)
        if method == "embeddings":
            return [{"item_id": it["item_id"], "score": round(sc, 4), "path": [user_id, "kNN_cosine", it["item_id"]]} for sc, it in e_scored[:k]]

        # 4. Hybrid RRF + weighted boost
        g_pos = {it["item_id"]: (idx + 1, shared) for idx, (_, shared, it) in enumerate(g_scored)}
        e_pos = {it["item_id"]: idx + 1 for idx, (_, it) in enumerate(e_scored)}
        hyb = []
        for it in pool:
            iid = it["item_id"]
            rg, shared = g_pos[iid]
            re_ = e_pos[iid]
            rrf = w_graph / (rrf_k + rg) + w_emb / (rrf_k + re_)
            hyb.append((rrf, shared, it))
        hyb.sort(key=lambda x: x[0], reverse=True)
        return [{"item_id": it["item_id"], "score": round(sc, 5), "path": [user_id] + (shared if shared else [it["forestry"]]) + [it["item_id"]]} for sc, shared, it in hyb[:k]]
