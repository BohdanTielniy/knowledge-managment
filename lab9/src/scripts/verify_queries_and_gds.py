#!/usr/bin/env python3
"""
Автономна верифікація результатів запитів Cypher (Результат 3),
еталонний розрахунок PageRank і Louvain (Результат 4) та звірка
базового підмножинного ABox (SPARQL ЛР 8) із повним графом (Результат 5).

Запуск: python3 scripts/verify_queries_and_gds.py
"""
import csv
import glob
import json
import math
import os
from collections import Counter, defaultdict, deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


LABEL_FILES = {
    "Forestry": "nodes_forestry.csv",
    "Compartment": "nodes_compartment.csv",
    "TreeSpecies": "nodes_treespecies.csv",
    "ForestProduct": "nodes_forestproduct.csv",
    "Threat": "nodes_threat.csv",
    "MeteoObservation": "nodes_meteoobservation.csv",
    "Process": "nodes_process.csv",
    "Permit": "nodes_permit.csv",
    "Quota": "nodes_quota.csv",
    "Actor": "nodes_actor.csv",
}

nodes_by_label = {}
all_nodes = {}
for label, fname in LABEL_FILES.items():
    rows = load_csv(fname)
    nodes_by_label[label] = {}
    for r in rows:
        r["_label"] = label
        nodes_by_label[label][r["id"]] = r
        all_nodes[r["id"]] = r

rels_by_type = defaultdict(list)
all_rels = []
out_adj = defaultdict(list)
in_adj = defaultdict(list)
undir_adj = defaultdict(list)

for path in sorted(glob.glob(os.path.join(DATA, "rels_*.csv"))):
    typ = os.path.basename(path)[5:-4]
    for r in load_csv(os.path.basename(path)):
        r["_type"] = typ
        r["confidence_f"] = float(r["confidence"])
        rels_by_type[typ].append(r)
        all_rels.append(r)
        out_adj[r["start_id"]].append((r["end_id"], typ, r))
        in_adj[r["end_id"]].append((r["start_id"], typ, r))
        undir_adj[r["start_id"]].append((r["end_id"], typ, r))
        undir_adj[r["end_id"]].append((r["start_id"], typ, r))


def fval(x):
    return float(x) if x != "" and x is not None else None


def ival(x):
    return int(x) if x != "" and x is not None else None


print("=== CQ1: Уражені виділи (>10%) ===")
part_of = {r["start_id"]: r["end_id"] for r in rels_by_type["PART_OF_FORESTRY"]}
dom_sp = {r["start_id"]: r["end_id"] for r in rels_by_type["HAS_DOMINANT_SPECIES"]}
cq1 = []
for r in rels_by_type["AFFECTED_BY"]:
    c = nodes_by_label["Compartment"][r["start_id"]]
    if fval(c["damagedTreesShare"]) > 10.0:
        f = nodes_by_label["Forestry"][part_of[c["id"]]]
        s = nodes_by_label["TreeSpecies"][dom_sp[c["id"]]]
        t = nodes_by_label["Threat"][r["end_id"]]
        cq1.append((c["unitCode"], f["unitCode"], s["name"], fval(c["damagedTreesShare"]),
                    t["name"], r["source"], r["confidence_f"]))
cq1.sort(key=lambda x: (-x[3], x[0]))
for row in cq1:
    print(" ", row)

print("\n=== CQ2: Високий пожежний ризик ===")
sup_forestry = defaultdict(list)
for r in rels_by_type["SUPERVISES"]:
    if r["end_label"] == "Forestry":
        a = nodes_by_label["Actor"][r["start_id"]]
        if a["subtype"] == "Forester":
            sup_forestry[r["end_id"]].append(a["name"])
cq2 = []
for r in rels_by_type["MONITORS_UNIT"]:
    o = nodes_by_label["MeteoObservation"][r["start_id"]]
    if fval(o["airTemperatureC"]) > 30 and fval(o["airHumidityPercent"]) < 30 and ival(o["daysWithoutRain"]) >= 7:
        f = nodes_by_label["Forestry"][r["end_id"]]
        foresters = sup_forestry.get(f["id"], [None])
        cq2.append((o["observationDate"], f["unitCode"], f["name"],
                    fval(o["airTemperatureC"]), fval(o["airHumidityPercent"]),
                    ival(o["daysWithoutRain"]), foresters, r["validFrom"]))
cq2.sort()
for row in cq2:
    print(" ", row)

print("\n=== CQ3: Заплановані рубки, обсяги, квитки, квоти, перевищення ===")
applied = {r["start_id"]: r["end_id"] for r in rels_by_type["APPLIED_TO"]}
permit_of = {r["start_id"]: r["end_id"] for r in rels_by_type["REQUIRES_PERMIT"]}
quota_of = {r["start_id"]: r["end_id"] for r in rels_by_type["CONSTRAINED_BY"]}
perf_by = {r["start_id"]: r["end_id"] for r in rels_by_type["PERFORMED_BY"]}
cq3 = []
for pid, p in nodes_by_label["Process"].items():
    if p["subtype"] in ("SanitaryFelling", "MainFelling"):
        c = nodes_by_label["Compartment"][applied[pid]]
        pm = nodes_by_label["Permit"][permit_of[pid]]
        q = nodes_by_label["Quota"][quota_of[pid]]
        a = nodes_by_label["Actor"][perf_by[pid]]
        vol = fval(p["harvestVolumeM3"])
        qlim = fval(q["limitValue"])
        cq3.append((pid, p["subtype"], c["unitCode"], vol, qlim, vol > qlim, pm["number"], a["name"]))
cq3.sort(key=lambda x: (-x[3], x[0]))
for row in cq3:
    print(" ", row)
print(f"  TOTAL fellings={len(cq3)}, sum_vol={sum(x[3] for x in cq3):.1f} m3")

print("\n=== CQ4: Стиглі хвойні виділи (вік >= 81) + агрегація по лісництвах ===")
cq4 = []
cq4_by_f = defaultdict(lambda: [0, 0.0, 0.0])
for cid, c in nodes_by_label["Compartment"].items():
    sp = nodes_by_label["TreeSpecies"][dom_sp[cid]]
    if sp["subtype"] == "ConiferousSpecies" and ival(c["standAgeYears"]) >= 81:
        f = nodes_by_label["Forestry"][part_of[cid]]
        cq4.append((c["unitCode"], f["unitCode"], sp["name"], ival(c["standAgeYears"]),
                    fval(c["timberStockM3"]), fval(c["annualIncrementM3"]), fval(c["ndviValue"])))
        cq4_by_f[f["unitCode"]][0] += 1
        cq4_by_f[f["unitCode"]][1] += fval(c["timberStockM3"])
        cq4_by_f[f["unitCode"]][2] += fval(c["areaHectares"])
cq4.sort(key=lambda x: (-x[3], x[0]))
for row in cq4:
    print(" ", row)
print("  By forestry:", {k: (v[0], round(v[1], 1), round(v[2], 1)) for k, v in sorted(cq4_by_f.items())})

print("\n=== CQ5: Лісовідновлення після рубок (OPTIONAL MATCH) ===")
followed = {r["start_id"]: r["end_id"] for r in rels_by_type["FOLLOWED_BY"]}
cq5 = []
for pid, p in sorted(nodes_by_label["Process"].items()):
    if p["subtype"] in ("SanitaryFelling", "MainFelling"):
        c = nodes_by_label["Compartment"][applied[pid]]
        rid = followed.get(pid)
        rnode = nodes_by_label["Process"][rid] if rid else None
        cq5.append((pid, c["unitCode"], rid, ival(rnode["plantedSeedlingsCount"]) if rnode else None))
for row in cq5:
    print(" ", row)
print("  Without reforestation:", [x[0] for x in cq5 if x[2] is None])

print("\n=== CQ6: Лісники за виділами із загрозами або пожежним патрулюванням ===")
sup_comp = {r["end_id"]: r["start_id"] for r in rels_by_type["SUPERVISES"] if r["end_label"] == "Compartment"}
cq6_threat = []
for r in rels_by_type["AFFECTED_BY"]:
    c = nodes_by_label["Compartment"][r["start_id"]]
    t = nodes_by_label["Threat"][r["end_id"]]
    a = nodes_by_label["Actor"][sup_comp[c["id"]]]
    cq6_threat.append((a["staffCode"], a["name"], c["unitCode"], t["name"], fval(c["damagedTreesShare"])))
cq6_threat.sort()
for row in cq6_threat:
    print("  [THREAT]", row)
cq6_fire = []
for r in rels_by_type["TRIGGERS"]:
    if r["start_label"] == "MeteoObservation":
        p = nodes_by_label["Process"][r["end_id"]]
        a = nodes_by_label["Actor"][perf_by[p["id"]]]
        o = nodes_by_label["MeteoObservation"][r["start_id"]]
        cq6_fire.append((a["staffCode"], a["name"], p["id"], o["observationDate"]))
cq6_fire.sort()
for row in cq6_fire:
    print("  [FIRE]", row)

print("\n=== CQ7: Недеревна продукція та ліміти збору ===")
lim_by = {r["start_id"]: r["end_id"] for r in rels_by_type["LIMITED_BY"]}
cq7_agg = defaultdict(list)
for r in rels_by_type["YIELDS_PRODUCT"]:
    p = nodes_by_label["ForestProduct"][r["end_id"]]
    if p["subtype"] == "NonTimberProduct":
        c = nodes_by_label["Compartment"][r["start_id"]]
        q = nodes_by_label["Quota"][lim_by[p["id"]]]
        cq7_agg[(p["name"], q["limitValue"], q["unit"])].append(c["unitCode"])
for k, v in sorted(cq7_agg.items()):
    print(f"  {k}: count={len(v)}, comps={sorted(v)}")

print("\n=== CQ8: Виділи з NDVI < 0.65 (першочергове обстеження) ===")
threats_of = defaultdict(list)
for r in rels_by_type["AFFECTED_BY"]:
    threats_of[r["start_id"]].append(nodes_by_label["Threat"][r["end_id"]]["name"])
cq8 = []
for cid, c in nodes_by_label["Compartment"].items():
    if fval(c["ndviValue"]) < 0.65:
        f = nodes_by_label["Forestry"][part_of[cid]]
        cq8.append((c["unitCode"], f["unitCode"], fval(c["ndviValue"]),
                    fval(c["damagedTreesShare"]), threats_of.get(cid, [])))
cq8.sort(key=lambda x: (x[2], x[0]))
for row in cq8:
    print(" ", row)

print("\n=== CQ9 (Impact Analysis 1): Ланцюжки впливу від загрози (глибина >= 3) ===")
# Threat -[:TRIGGERS]-> Process -[:FOLLOWED_BY]-> Reforestation -[:APPLIED_TO]-> Compartment -[:PART_OF_FORESTRY]-> Forestry
# Depth 4! Also variable length path Threat -[:TRIGGERS|FOLLOWED_BY|APPLIED_TO|REQUIRES_PERMIT|CONSTRAINED_BY*3..4]-> target
cq9_chains = []
for r1 in rels_by_type["TRIGGERS"]:
    if r1["start_label"] != "Threat":
        continue
    t = nodes_by_label["Threat"][r1["start_id"]]
    p1 = nodes_by_label["Process"][r1["end_id"]]
    # depth 3: Threat -> p1 -> Compartment -> Forestry
    cid = applied[p1["id"]]
    c = nodes_by_label["Compartment"][cid]
    fid = part_of[cid]
    f = nodes_by_label["Forestry"][fid]
    # depth 4: Threat -> p1 -> Reforestation -> Compartment -> Forestry
    rid = followed.get(p1["id"])
    rnode = nodes_by_label["Process"][rid] if rid else None
    # min confidence along Threat->p1->c->f (and rid)
    r_app = [r for r in rels_by_type["APPLIED_TO"] if r["start_id"] == p1["id"]][0]
    r_pf = [r for r in rels_by_type["PART_OF_FORESTRY"] if r["start_id"] == cid][0]
    confs = [r1["confidence_f"], r_app["confidence_f"], r_pf["confidence_f"]]
    if rid:
        r_fb = [r for r in rels_by_type["FOLLOWED_BY"] if r["start_id"] == p1["id"]][0]
        confs.append(r_fb["confidence_f"])
    cq9_chains.append((t["id"], p1["id"], rid, c["unitCode"], f["unitCode"], min(confs)))
cq9_chains.sort()
for row in cq9_chains:
    print(" ", row)
print(f"  Total impact chains (depth 3-4): {len(cq9_chains)}")

print("\n=== CQ10 (Impact Analysis 2): Вплив аномальної/загальних квот + shortestPath(Forester, Threat) ===")
# Impact of Quota on Process -> Compartment -> Forestry (depth 3) + Forester
cq10_over = []
for pid, p in nodes_by_label["Process"].items():
    if p["subtype"] in ("SanitaryFelling", "MainFelling"):
        q = nodes_by_label["Quota"][quota_of[pid]]
        c = nodes_by_label["Compartment"][applied[pid]]
        f = nodes_by_label["Forestry"][part_of[c["id"]]]
        pm = nodes_by_label["Permit"][permit_of[pid]]
        fo = nodes_by_label["Actor"][sup_comp[c["id"]]]
        vol = fval(p["harvestVolumeM3"])
        lim = fval(q["limitValue"])
        if vol > lim:
            cq10_over.append((q["id"], lim, pid, vol, pm["number"], c["unitCode"], f["unitCode"], fo["staffCode"]))
print("  Over-quota impact:", cq10_over)


# shortestPath between Forester_F104 and all Threats (undirected hops)
def bfs_shortest(src, dst):
    q = deque([(src, [(src, None)])])
    vis = {src}
    while q:
        u, path = q.popleft()
        if u == dst:
            return path
        for v, typ, _ in undir_adj[u]:
            if v not in vis:
                vis.add(v)
                q.append((v, path + [(v, typ)]))
    return None


for tid in sorted(nodes_by_label["Threat"].keys()):
    p = bfs_shortest("Forester_F104", tid)
    if p:
        hops = len(p) - 1
        desc = " -> ".join(f"{nid}" + (f" ({t})" if t else "") for nid, t in p)
        print(f"  shortestPath(Forester_F104, {tid}): hops={hops} | {desc}")

# === RESULT 4: PageRank (d=0.85, maxIter=20, Neo4j GDS formula) ===
print("\n=== GDS Reference: PageRank (directed, d=0.85, 20 iters, GDS unnormalized) ===")
node_ids = sorted(all_nodes.keys())
N_nodes = len(node_ids)
d = 0.85
# Neo4j GDS PageRank initializes PR(v) = 1 - d = 0.15, and iterates PR(v) = (1-d) + d * sum(PR(u)/outdeg(u))
pr = {u: 1.0 - d for u in node_ids}
out_deg = {u: len(out_adj[u]) for u in node_ids}
for _ in range(20):
    new_pr = {u: 1.0 - d for u in node_ids}
    for u in node_ids:
        if out_deg[u] > 0:
            share = d * pr[u] / out_deg[u]
            for v, _, _ in out_adj[u]:
                new_pr[v] += share
    pr = new_pr

top10_pr = sorted(pr.items(), key=lambda x: (-x[1], x[0]))[:10]
for rank, (nid, score) in enumerate(top10_pr, 1):
    n = all_nodes[nid]
    print(f"  {rank:2d}. {nid:30s} | {n['_label']:16s} | PR={score:.4f} | in={len(in_adj[nid]):2d} out={len(out_adj[nid]):2d} | {n.get('name', n.get('number', ''))}")

# === GDS Reference: Louvain (undirected modularity optimization, seed=42) ===
print("\n=== GDS Reference: Louvain (undirected modularity) ===")
# Build undirected weighted adjacency (weight=1 per edge)
adj_w = defaultdict(lambda: defaultdict(float))
m2 = 0.0
for r in all_rels:
    u, v = r["start_id"], r["end_id"]
    adj_w[u][v] += 1.0
    adj_w[v][u] += 1.0
    m2 += 2.0


def louvain(nodes_list, adj):
    comm = {u: i for i, u in enumerate(nodes_list)}
    k = {u: sum(adj[u].values()) for u in nodes_list}
    tot = {comm[u]: k[u] for u in nodes_list}
    m = sum(k.values()) / 2.0
    improved = True
    while improved:
        improved = False
        for u in nodes_list:
            cu = comm[u]
            ku = k[u]
            # weights to neighbor communities
            neigh_c = defaultdict(float)
            for v, w in adj[u].items():
                if v != u:
                    neigh_c[comm[v]] += w
            # remove u from cu
            tot[cu] -= ku
            best_c = cu
            best_gain = 0.0
            ki_in_cu = neigh_c.get(cu, 0.0)
            base_loss = ki_in_cu - (tot[cu] * ku) / (2.0 * m)
            for c, ki_in in neigh_c.items():
                gain = (ki_in - (tot[c] * ku) / (2.0 * m)) - base_loss
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_c = c
            comm[u] = best_c
            tot[best_c] += ku
            if best_c != cu:
                improved = True
    # Phase 2: aggregate super-nodes once to merge small communities
    comms_map = defaultdict(list)
    for u, c in comm.items():
        comms_map[c].append(u)
    super_nodes = sorted(comms_map.keys())
    s_adj = defaultdict(lambda: defaultdict(float))
    for u in nodes_list:
        cu = comm[u]
        for v, w in adj[u].items():
            cv = comm[v]
            s_adj[cu][cv] += w
    s_comm = {c: c for c in super_nodes}
    s_k = {c: sum(s_adj[c].values()) for c in super_nodes}
    s_tot = {c: s_k[c] for c in super_nodes}
    improved = True
    while improved:
        improved = False
        for u in super_nodes:
            cu = s_comm[u]
            ku = s_k[u]
            neigh_c = defaultdict(float)
            for v, w in s_adj[u].items():
                if v != u:
                    neigh_c[s_comm[v]] += w
            s_tot[cu] -= ku
            best_c = cu
            best_gain = 0.0
            ki_in_cu = neigh_c.get(cu, 0.0)
            base_loss = ki_in_cu - (s_tot[cu] * ku) / (2.0 * m)
            for c, ki_in in neigh_c.items():
                gain = (ki_in - (s_tot[c] * ku) / (2.0 * m)) - base_loss
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_c = c
            s_comm[u] = best_c
            s_tot[best_c] += ku
            if best_c != cu:
                improved = True
    final_comm = {u: s_comm[comm[u]] for u in nodes_list}
    # Compute modularity Q
    Q = 0.0
    for u in nodes_list:
        for v, w in adj[u].items():
            if final_comm[u] == final_comm[v]:
                Q += w - (k[u] * k[v]) / (2.0 * m)
    Q /= (2.0 * m)
    return final_comm, Q


comm_map, Q = louvain(node_ids, adj_w)
groups = defaultdict(list)
for u, c in comm_map.items():
    groups[c].append(u)
sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
print(f"  Modularity Q = {Q:.4f}, Communities = {len(sorted_groups)}")
for idx, (cid, members) in enumerate(sorted_groups, 1):
    lbl_cnt = Counter(all_nodes[u]["_label"] for u in members)
    forestries = [u for u in members if all_nodes[u]["_label"] == "Forestry"]
    top_pr_in_c = sorted(members, key=lambda u: -pr[u])[:4]
    print(f"  Community {idx} (size={len(members):2d}): forestries={forestries}, labels={dict(lbl_cnt)}, top={top_pr_in_c}")

# === RESULT 5: Base ABox (origin == 'lab7-8') vs Full Graph counts for 5 CQ ===
print("\n=== SPARQL (base ABox lab7-8) vs Cypher (full graph) ===")
base_cq1 = [x for x in cq1 if nodes_by_label["Compartment"]["Compartment_" + x[0].replace("-", "")]["origin"] == "lab7-8"]
base_cq2 = [x for x in cq2 if x[1] == "LS-01" and x[0] == "2026-09-05"]
base_cq3 = [x for x in cq3 if nodes_by_label["Process"][x[0]]["origin"] == "lab7-8"]
base_cq4 = [x for x in cq4 if nodes_by_label["Compartment"]["Compartment_" + x[0].replace("-", "")]["origin"] == "lab7-8"]
base_cq5_missing = [x for x in cq5 if nodes_by_label["Process"][x[0]]["origin"] == "lab7-8" and x[2] is None]
print(f"  CQ1: base={len(base_cq1)} ({[x[0] for x in base_cq1]}) | full={len(cq1)} ({[x[0] for x in cq1]})")
print(f"  CQ2: base={len(base_cq2)} ({[x[0] for x in base_cq2]}) | full={len(cq2)} ({[(x[0], x[1]) for x in cq2]})")
print(f"  CQ3: base={len(base_cq3)} ({[x[0] for x in base_cq3]}) | full={len(cq3)}")
print(f"  CQ4: base={len(base_cq4)} ({[x[0] for x in base_cq4]}) | full={len(cq4)}")
print(f"  CQ5 (no reforest): base={len(base_cq5_missing)} ({[x[0] for x in base_cq5_missing]}) | full={len([x for x in cq5 if x[2] is None])}")
