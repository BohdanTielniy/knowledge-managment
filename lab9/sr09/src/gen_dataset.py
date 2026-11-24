#!/usr/bin/env python3
"""
СР 9, Крок 2: генератор детермінованого датасету (>= 500 вузлів) для ПдО
«Управління лісовими продуктами» (seed = 42) у двох еквівалентних форматах:
  - data/dataset.json    (для Neo4j та Memgraph)
  - data/forest_sr09.ttl (Turtle RDF для GraphDB Free)

Запуск: python3 src/gen_dataset.py
"""
import json
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
SEED = 42


def generate():
    rnd = random.Random(SEED)
    os.makedirs(DATA_DIR, exist_ok=True)

    # 10 лісництв
    forestries = [
        {"id": f"Forestry_LS{i:02d}", "unitCode": f"LS-{i:02d}", "name": f"Лісництво №{i:02d}"}
        for i in range(1, 11)
    ]

    # 6 деревних порід
    species = [
        {"id": "Species_PiceaAbies", "name": "Ялина європейська", "coniferous": True},
        {"id": "Species_PinusSylvestris", "name": "Сосна звичайна", "coniferous": True},
        {"id": "Species_AbiesAlba", "name": "Ялиця біла", "coniferous": True},
        {"id": "Species_LarixDecidua", "name": "Модрина європейська", "coniferous": True},
        {"id": "Species_FagusSylvatica", "name": "Бук лісовий", "coniferous": False},
        {"id": "Species_QuercusRobur", "name": "Дуб звичайний", "coniferous": False},
    ]
    sp_weights = [32, 18, 12, 8, 20, 10]

    # 12 загроз
    threats = [
        {"id": f"Threat_Ips_{i:02d}", "name": "Короїд-типограф", "kind": "Biotic"} for i in range(1, 5)
    ] + [
        {"id": f"Threat_Rot_{i:02d}", "name": "Кореневе гниття", "kind": "Biotic"} for i in range(1, 5)
    ] + [
        {"id": f"Threat_Wind_{i:02d}", "name": "Вітровал", "kind": "Abiotic"} for i in range(1, 5)
    ]

    # 30 лісників
    foresters = [
        {"id": f"Forester_F{i:03d}", "staffCode": f"F-{i:03d}", "name": f"Лісник F-{i:03d}"}
        for i in range(101, 131)
    ]

    # 400 лісових виділів
    compartments = []
    rels_part_of = []
    rels_species = []
    rels_supervises = []
    rels_affected = []

    for i in range(1, 401):
        cid = f"Compartment_V{i:03d}"
        f = forestries[(i - 1) // 40]
        sp = rnd.choices(species, sp_weights)[0]
        fo = foresters[(i - 1) % len(foresters)]
        age = rnd.randint(25, 135)
        area = round(rnd.uniform(4.0, 18.0), 1)
        stock = round(area * rnd.uniform(240.0, 340.0), 1)
        is_damaged = (i % 7 == 0)  # ~57 уражених виділів
        dmg = round(rnd.uniform(11.0, 32.0), 1) if is_damaged else round(rnd.uniform(0.5, 9.0), 1)
        ndvi = round(rnd.uniform(0.48, 0.63), 2) if is_damaged else round(rnd.uniform(0.67, 0.88), 2)
        if not is_damaged and i % 29 == 0:
            ndvi = round(rnd.uniform(0.60, 0.64), 2)  # раннє попередження

        compartments.append({
            "id": cid, "unitCode": f"V-{i:03d}", "areaHectares": area,
            "standAgeYears": age, "timberStockM3": stock,
            "damagedTreesShare": dmg, "ndviValue": ndvi,
        })
        rels_part_of.append({"start": cid, "end": f["id"]})
        rels_species.append({"start": cid, "end": sp["id"]})
        rels_supervises.append({"start": fo["id"], "end": cid})
        if is_damaged:
            th = threats[(i // 7) % 8]  # біотичні загрози
            rels_affected.append({"start": cid, "end": th["id"]})
        elif i % 23 == 0:
            th = threats[8 + (i % 4)]   # абіотичний вітровал
            rels_affected.append({"start": cid, "end": th["id"]})

    # 120 процесів рубок + 90 процесів лісовідновлення (разом > 650 вузлів!)
    harvests = []
    reforestations = []
    rels_applied = []
    rels_followed = []

    h_idx = 0
    for c in compartments:
        if c["damagedTreesShare"] > 10.0 or (c["standAgeYears"] >= 81 and h_idx < 120):
            if h_idx >= 120:
                break
            h_idx += 1
            hid = f"Harvest_{h_idx:03d}"
            kind = "SanitaryFelling" if c["damagedTreesShare"] > 10.0 else "MainFelling"
            vol = round(rnd.uniform(90.0, 420.0), 1)
            harvests.append({"id": hid, "kind": kind, "harvestVolumeM3": vol})
            rels_applied.append({"start": hid, "end": c["id"]})
            if h_idx <= 90:
                rid = f"Reforest_{h_idx:03d}"
                reforestations.append({"id": rid, "seedlings": rnd.randint(3500, 9500)})
                rels_followed.append({"start": hid, "end": rid})

    total_nodes = (len(forestries) + len(species) + len(threats) + len(foresters)
                   + len(compartments) + len(harvests) + len(reforestations))
    total_rels = (len(rels_part_of) + len(rels_species) + len(rels_supervises)
                  + len(rels_affected) + len(rels_applied) + len(rels_followed))

    # Еталонні відповіді на 5 запитів бенчмарку
    conif_ids = {s["id"] for s in species if s["coniferous"]}
    sp_of = {r["start"]: r["end"] for r in rels_species}
    f_of = {r["start"]: r["end"] for r in rels_part_of}
    app_of = {r["start"]: r["end"] for r in rels_applied}
    fol_set = {r["start"] for r in rels_followed}
    aff_set = {r["start"] for r in rels_affected}

    q1_cnt = sum(1 for c in compartments if c["damagedTreesShare"] > 10.0 and c["id"] in aff_set)
    q2_cnt = sum(1 for c in compartments if c["standAgeYears"] >= 81 and sp_of[c["id"]] in conif_ids)
    q3_cnt = sum(1 for h in harvests if h["id"] not in fol_set)
    q4_total_vol = round(sum(h["harvestVolumeM3"] for h in harvests), 1)
    q5_cnt = sum(1 for r in rels_affected if any(
        h["id"] in fol_set and app_of[h["id"]] == r["start"] for h in harvests
    ))

    dataset = {
        "seed": SEED,
        "summary": {
            "total_nodes": total_nodes,
            "total_rels": total_rels,
            "expected": {
                "Q1_damaged_with_threat": q1_cnt,
                "Q2_mature_coniferous": q2_cnt,
                "Q3_harvests_without_reforest": q3_cnt,
                "Q4_total_harvest_volume_m3": q4_total_vol,
                "Q5_threat_harvest_reforest_chains": q5_cnt,
            },
        },
        "nodes": {
            "forestries": forestries,
            "species": species,
            "threats": threats,
            "foresters": foresters,
            "compartments": compartments,
            "harvests": harvests,
            "reforestations": reforestations,
        },
        "rels": {
            "PART_OF_FORESTRY": rels_part_of,
            "HAS_DOMINANT_SPECIES": rels_species,
            "SUPERVISES": rels_supervises,
            "AFFECTED_BY": rels_affected,
            "APPLIED_TO": rels_applied,
            "FOLLOWED_BY": rels_followed,
        },
    }

    with open(os.path.join(DATA_DIR, "dataset.json"), "w", encoding="utf-8") as fh:
        json.dump(dataset, fh, ensure_ascii=False, indent=2)

    # Генерація еквівалентного Turtle (.ttl) для GraphDB Free
    ttl = [
        "@prefix fm: <http://lnu.edu.ua/ontologies/2026/forest-sr09#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]
    for f in forestries:
        ttl.append(f'fm:{f["id"]} a fm:Forestry ; fm:unitCode "{f["unitCode"]}" ; fm:name "{f["name"]}" .')
    for s in species:
        sub = "fm:ConiferousSpecies" if s["coniferous"] else "fm:DeciduousSpecies"
        ttl.append(f'fm:{s["id"]} a fm:TreeSpecies, {sub} ; fm:name "{s["name"]}" .')
    for t in threats:
        ttl.append(f'fm:{t["id"]} a fm:Threat ; fm:name "{t["name"]}" ; fm:kind "{t["kind"]}" .')
    for fo in foresters:
        ttl.append(f'fm:{fo["id"]} a fm:Forester ; fm:staffCode "{fo["staffCode"]}" ; fm:name "{fo["name"]}" .')
    for c in compartments:
        ttl.append(
            f'fm:{c["id"]} a fm:Compartment ; fm:unitCode "{c["unitCode"]}" ; '
            f'fm:areaHectares {c["areaHectares"]} ; fm:standAgeYears {c["standAgeYears"]} ; '
            f'fm:timberStockM3 {c["timberStockM3"]} ; fm:damagedTreesShare {c["damagedTreesShare"]} ; '
            f'fm:ndviValue {c["ndviValue"]} .'
        )
    for h in harvests:
        ttl.append(
            f'fm:{h["id"]} a fm:TimberHarvesting ; fm:kind "{h["kind"]}" ; '
            f'fm:harvestVolumeM3 {h["harvestVolumeM3"]} .'
        )
    for rf in reforestations:
        ttl.append(f'fm:{rf["id"]} a fm:Reforestation ; fm:seedlings {rf["seedlings"]} .')

    pred_map = {
        "PART_OF_FORESTRY": "fm:partOfForestry",
        "HAS_DOMINANT_SPECIES": "fm:hasDominantSpecies",
        "SUPERVISES": "fm:supervises",
        "AFFECTED_BY": "fm:affectedBy",
        "APPLIED_TO": "fm:appliedTo",
        "FOLLOWED_BY": "fm:followedBy",
    }
    for rtype, rlist in dataset["rels"].items():
        pred = pred_map[rtype]
        for r in rlist:
            ttl.append(f'fm:{r["start"]} {pred} fm:{r["end"]} .')

    with open(os.path.join(DATA_DIR, "forest_sr09.ttl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ttl) + "\n")

    print(json.dumps(dataset["summary"], ensure_ascii=False, indent=2))
    assert total_nodes >= 500, f"Потрібно >= 500 вузлів, отримано {total_nodes}"


if __name__ == "__main__":
    generate()
