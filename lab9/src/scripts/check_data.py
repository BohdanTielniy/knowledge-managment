#!/usr/bin/env python3
"""
Автономна перевірка CSV (без Neo4j): цілісність, пороги ЛР 1–8 та «еталонні»
значення, з якими студент порівнює результати запитів у Neo4j.

Запуск:  python3 -I scripts/check_data.py
"""
import csv
import glob
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


LABEL_FILES = {
    "Forestry": "nodes_forestry.csv", "Compartment": "nodes_compartment.csv",
    "TreeSpecies": "nodes_treespecies.csv", "ForestProduct": "nodes_forestproduct.csv",
    "Threat": "nodes_threat.csv", "MeteoObservation": "nodes_meteoobservation.csv",
    "Process": "nodes_process.csv", "Permit": "nodes_permit.csv",
    "Quota": "nodes_quota.csv", "Actor": "nodes_actor.csv",
}
errors = []
nodes = {}
for label, f in LABEL_FILES.items():
    rows = load(f)
    nodes[label] = {r["id"]: r for r in rows}
    if len(nodes[label]) != len(rows):
        errors.append(f"{label}: дублікати id")
all_ids = [i for d in nodes.values() for i in d]
if len(all_ids) != len(set(all_ids)):
    errors.append("id вузлів не унікальні між мітками")
codes = [r["unitCode"] for r in nodes["Compartment"].values()]
if len(codes) != len(set(codes)):
    errors.append("Compartment.unitCode не унікальний")

rels = defaultdict(list)
for path in sorted(glob.glob(os.path.join(DATA, "rels_*.csv"))):
    typ = os.path.basename(path)[5:-4]
    for r in load(os.path.basename(path)):
        rels[typ].append(r)
        if r["start_id"] not in nodes.get(r["start_label"], {}):
            errors.append(f"{typ}: немає початкового вузла {r['start_label']}:{r['start_id']}")
        if r["end_id"] not in nodes.get(r["end_label"], {}):
            errors.append(f"{typ}: немає кінцевого вузла {r['end_label']}:{r['end_id']}")
        for k in ("source", "confidence", "validFrom"):
            if not r[k]:
                errors.append(f"{typ}: порожнє {k}")

n_nodes = sum(len(d) for d in nodes.values())
n_rels = sum(len(v) for v in rels.values())
print(f"Вузлів: {n_nodes} (вимога >=100) | Зв'язків: {n_rels} (вимога >=200) | "
      f"міток: {len(nodes)} (>=6) | типів зв'язків: {len(rels)} (>=8)")
if n_nodes < 100 or n_rels < 200 or len(nodes) < 6 or len(rels) < 8:
    errors.append("не виконано кількісні вимоги C1")

# --- Еталонні значення (рахуються незалежно від Cypher) ---------------------
comp = nodes["Compartment"]
species_of = {r["start_id"]: r["end_id"] for r in rels["HAS_DOMINANT_SPECIES"]}
conif = {i for i, r in nodes["TreeSpecies"].items() if r["subtype"] == "ConiferousSpecies"}

damaged = sorted(i for i, r in comp.items() if float(r["damagedTreesShare"]) > 10.0)
low_ndvi = sorted(i for i, r in comp.items() if float(r["ndviValue"]) < 0.65)
mature = sorted(i for i, r in comp.items()
                if int(r["standAgeYears"]) >= 81 and species_of[i] in conif)
fire = sorted(i for i, r in nodes["MeteoObservation"].items()
              if float(r["airTemperatureC"]) > 30.0 and float(r["airHumidityPercent"]) < 30.0
              and int(r["daysWithoutRain"]) >= 7)

fellings = {i: r for i, r in nodes["Process"].items() if r["subtype"] in ("SanitaryFelling", "MainFelling")}
applied = {r["start_id"]: r["end_id"] for r in rels["APPLIED_TO"]}
quota_of = {r["start_id"]: r["end_id"] for r in rels["CONSTRAINED_BY"]}
permit_of = {r["start_id"] for r in rels["REQUIRES_PERMIT"]}
followed = {r["start_id"] for r in rels["FOLLOWED_BY"]}

over_quota, over_incr = [], []
for pid, p in fellings.items():
    vol = float(p["harvestVolumeM3"])
    q = float(nodes["Quota"][quota_of[pid]]["limitValue"])
    c = comp[applied[pid]]
    if vol > q:
        over_quota.append(pid)
    if c["annualIncrementM3"] and vol > float(c["annualIncrementM3"]):
        over_incr.append(pid)
no_permit = sorted(p for p in fellings if p not in permit_of)
no_reforest = sorted(p for p in fellings if p not in followed)
total_volume = sum(float(p["harvestVolumeM3"]) for p in fellings.values())

by_forestry = Counter()
forestry_of = {r["start_id"]: r["end_id"] for r in rels["PART_OF_FORESTRY"]}
for pid in fellings:
    by_forestry[forestry_of[applied[pid]]] += 1
if no_permit:
    errors.append(f"рубки без квитка: {no_permit}")

print("\nЕталонні значення для звірки з Neo4j:")
print(f"  DamagedCompartment (damagedTreesShare > 10): {len(damaged)}  {[comp[i]['unitCode'] for i in damaged]}")
print(f"  NDVI < 0.65: {len(low_ndvi)}  {[comp[i]['unitCode'] for i in low_ndvi]}")
print(f"  Стиглі хвойні (вік >= 81): {len(mature)}  {[comp[i]['unitCode'] for i in mature]}")
print(f"  HighFireRiskObservation: {len(fire)}  {fire}")
print(f"  Рубок (санітарних + головних): {len(fellings)}; сумарний обсяг {total_volume:.1f} м³")
print(f"  Рубки по лісництвах: {dict(by_forestry)}")
print(f"  Рубки без лісовідновлення: {len(no_reforest)}  {no_reforest}")
print(f"  Обсяг > квоти: {over_quota} | обсяг > річного приросту: {over_incr}")

print("\nПорушення:" if errors else "\nПомилок цілісності не знайдено.")
for e in errors:
    print("  -", e)
sys.exit(1 if errors else 0)
