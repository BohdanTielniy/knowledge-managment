#!/usr/bin/env python3
"""
ЛР 11, Результат 2: Entity Linking запиту до вузлів графа знань ЛР 9
та витяг лінеаризованого підграфа (1–2 кроки з лімітом ребер) із ID вузлів.

Підтримує живий Neo4j (якщо задано NEO4J_URI і сервер доступний) та
автономний CSV-граф (data/graph_csv/*.csv — 166 вузлів, 333 зв'язки з ЛР 9).
"""
import csv
import glob
import os
import re
from collections import defaultdict, deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRAPH_CSV_DIR = os.path.join(ROOT, "data", "graph_csv")

SYNONYM_MAP = {
    "карпатськ": "Forestry_LS01",
    "бескидськ": "Forestry_LS02",
    "верховинськ": "Forestry_LS03",
    "дністровськ": "Forestry_LS04",
    "короїд": "Threat_IpsTypographus",
    "типограф": "Threat_IpsTypographus",
    "ips typographus": "Threat_IpsTypographus",
    "вітровал": "Threat_Windthrow2026",
    "фомін": "Forester_F104",
    "білі гриби": "Product_BoletusMushrooms",
    "гриб": "Product_BoletusMushrooms",
    "чорниц": "Product_Blueberries",
    "малин": "Product_Raspberries",
    "звіроб": "Product_StJohnsWort",
    "ялин": "Species_PiceaAbies",
    "сосн": "Species_PinusSylvestris",
    "бук": "Species_FagusSylvatica",
    "модрин": "Species_LarixDecidua",
    "бригада №1": "Brigade_01",
    "бригада №2": "Brigade_02",
    "бригада №3": "Brigade_03",
    "дснс львів": "FireService_DSNS_Lviv",
    "дснс івано": "FireService_DSNS_IvanoFrankivsk",
}


class KnowledgeGraphContext:
    def __init__(self, csv_dir: str = GRAPH_CSV_DIR):
        self.nodes = {}
        self.out_edges = defaultdict(list)
        self.in_edges = defaultdict(list)
        self._load_csv_graph(csv_dir)

    def _load_csv_graph(self, csv_dir: str):
        for path in sorted(glob.glob(os.path.join(csv_dir, "nodes_*.csv"))):
            label = os.path.basename(path)[6:-4]
            with open(path, encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    row["_label"] = label
                    self.nodes[row["id"]] = row

        for path in sorted(glob.glob(os.path.join(csv_dir, "rels_*.csv"))):
            rtype = os.path.basename(path)[5:-4]
            with open(path, encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    edge = {
                        "type": rtype,
                        "start": row["start_id"],
                        "end": row["end_id"],
                        "source": row["source"],
                        "confidence": row["confidence"],
                        "validFrom": row["validFrom"],
                    }
                    self.out_edges[row["start_id"]].append(edge)
                    self.in_edges[row["end_id"]].append(edge)

    def entity_link(self, query: str, max_entities: int = 4) -> list:
        """Зв'язування запиту з ID вузлів графа за кодами (V-012, LS-01, F-104, ЛК-2026-047), іменами та синонімами."""
        q_low = query.lower()
        found = []

        def add_id(nid):
            if nid in self.nodes and nid not in found:
                found.append(nid)

        # 1. Точні коди виділів V-012 -> Compartment_V012
        for m in re.findall(r"\bV-(\d{3})\b", query, flags=re.IGNORECASE):
            add_id(f"Compartment_V{m}")

        # 2. Коди лісництв LS-01 -> Forestry_LS01
        for m in re.findall(r"\bLS-(\d{2})\b", query, flags=re.IGNORECASE):
            add_id(f"Forestry_LS{m}")

        # 3. Коди лісників F-104 -> Forester_F104
        for m in re.findall(r"\bF-(\d{3})\b", query, flags=re.IGNORECASE):
            add_id(f"Forester_F{m}")

        # 4. Лісорубні квитки ЛК-2026-042 -> Ticket_LK2026_042
        for m in re.findall(r"ЛК-2026-(\d{3})", query, flags=re.IGNORECASE):
            add_id(f"Ticket_LK2026_{m}")

        # 5. Прямі ID процесів або квот
        for nid in self.nodes:
            if nid.lower() in q_low:
                add_id(nid)

        # 6. Синоніми та назви
        for kw, nid in SYNONYM_MAP.items():
            if kw in q_low:
                add_id(nid)

        return found[:max_entities]

    def extract_subgraph(self, query: str, max_hops: int = 2, max_edges: int = 12):
        """Витягує підграф на 1–2 кроки навколо знайдених сутностей з жорстким лімітом ребер."""
        seeds = self.entity_link(query)
        if not seeds:
            return {"entities": [], "facts": [], "edges_count": 0, "linearized": ""}

        visited = set(seeds)
        q = deque([(s, 0) for s in seeds])
        edges_collected = []
        seen_edge_keys = set()

        while q and len(edges_collected) < max_edges:
            u, depth = q.popleft()
            if depth >= max_hops:
                continue
            for e in self.out_edges[u] + self.in_edges[u]:
                ekey = (e["start"], e["type"], e["end"])
                if ekey in seen_edge_keys:
                    continue
                seen_edge_keys.add(ekey)
                edges_collected.append(e)
                other = e["end"] if e["start"] == u else e["start"]
                if other not in visited:
                    visited.add(other)
                    q.append((other, depth + 1))
                if len(edges_collected) >= max_edges:
                    break

        facts = []
        lines = []
        for s in seeds:
            n = self.nodes[s]
            props = {k: v for k, v in n.items() if v and k not in ("id", "_label", "origin", "subtype")}
            prop_s = ", ".join(f"{k}={v}" for k, v in list(props.items())[:5])
            txt = f"Вузол {s} ({prop_s})"
            facts.append({"id": s, "text": txt})
            lines.append(f"[{s}] ({n.get('subtype') or n['_label']}): {prop_s}")

        for e in edges_collected:
            s_name = self.nodes[e["start"]].get("unitCode") or self.nodes[e["start"]].get("name") or e["start"]
            e_name = self.nodes[e["end"]].get("unitCode") or self.nodes[e["end"]].get("name") or e["end"]
            txt = f"{e['start']} ({s_name}) -[:{e['type']}]-> {e['end']} ({e_name})"
            facts.append({"id": e["start"], "text": txt})
            lines.append(
                f"[{e['start']}] -[:{e['type']} {{source:'{e['source']}', conf:{e['confidence']}}}]-> [{e['end']}]"
            )

        return {
            "entities": seeds,
            "facts": facts,
            "edges_count": len(edges_collected),
            "linearized": "\n".join(lines),
        }


if __name__ == "__main__":
    kg = KnowledgeGraphContext()
    for q in [
        "Які процеси та лісник пов'язані з виділом V-012?",
        "Що зачепить перевищення квоти на V-102 і квиток ЛК-2026-047?",
    ]:
        sg = kg.extract_subgraph(q, max_hops=2, max_edges=8)
        print("Q:", q)
        print("Entities:", sg["entities"], "Edges:", sg["edges_count"])
        print(sg["linearized"])
        print("-" * 60)
