#!/usr/bin/env python3
"""
ЛР 9. Генератор CSV та Cypher-імпорту для графової бази знань
«Управління лісовими продуктами».

Джерела даних:
  * lab7-8-abox          — екземпляри (ABox), явно описані у звітах ЛР 6–8
                           (лісництво «Карпатське», виділи V-012/V-003/V-008,
                           метеозаміри, рубки, квитки тощо);
  * synthetic-gen-seed42 — синтетичне розширення, згенероване цим скриптом
                           (детермінований seed), щоб досягти >=100 вузлів
                           і >=200 зв'язків. Усі такі записи мають
                           origin=synthetic, а їхні зв'язки — confidence=0.8.

Запуск:  python3 scripts/gen_data.py
Вихід:   data/*.csv, import/01_import_nodes.cypher, import/02_import_rels.cypher
"""
import csv
import math
import os
import random
from collections import defaultdict
from datetime import date, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
IMPORT = os.path.join(ROOT, "import")
SEED = 42
rnd = random.Random(SEED)

SRC_BASE = "lab7-8-abox"
SRC_SYN = "synthetic-gen-seed42"
CONF_BASE = 1.0
CONF_SYN = 0.8
D0 = date(2026, 9, 1)  # початок змодельованого сценарію (вересень 2026)

nodes = defaultdict(list)
rels = defaultdict(list)


def N(label, id_, base, **props):
    row = {"id": id_, "origin": "lab7-8" if base else "synthetic"}
    row.update(props)
    nodes[label].append(row)
    return row


def R(typ, sl, sid, el, eid, base, valid=None):
    rels[typ].append(dict(
        start_label=sl, start_id=sid, end_label=el, end_id=eid,
        source=SRC_BASE if base else SRC_SYN,
        confidence=CONF_BASE if base else CONF_SYN,
        validFrom=(valid or D0).isoformat()))


def rdate(a, b):
    return a + timedelta(days=rnd.randint(0, (b - a).days))


# --------------------------------------------------------------------------
# Специфікація вузлів: label -> (файл, [(колонка, тип)], [підтипи-мітки])
# типи: s=string, f=float, i=integer, d=date
# --------------------------------------------------------------------------
NODE_SPECS = {
    "Forestry": ("nodes_forestry.csv",
                 [("origin", "s"), ("unitCode", "s"), ("name", "s"), ("areaHectares", "f")], []),
    "Compartment": ("nodes_compartment.csv",
                    [("origin", "s"), ("unitCode", "s"), ("name", "s"), ("areaHectares", "f"),
                     ("standAgeYears", "i"), ("dbhCm", "f"), ("heightMeters", "f"),
                     ("timberStockM3", "f"), ("annualIncrementM3", "f"),
                     ("damagedTreesShare", "f"), ("ndviValue", "f")], []),
    "TreeSpecies": ("nodes_treespecies.csv",
                    [("origin", "s"), ("name", "s"), ("latinName", "s")],
                    ["ConiferousSpecies", "DeciduousSpecies"]),
    "ForestProduct": ("nodes_forestproduct.csv",
                      [("origin", "s"), ("name", "s"), ("category", "s")],
                      ["TimberProduct", "NonTimberProduct"]),
    "Threat": ("nodes_threat.csv",
               [("origin", "s"), ("name", "s"), ("kind", "s"), ("detectedOn", "d")],
               ["InsectPest", "ForestDisease", "Drought", "Windthrow"]),
    "MeteoObservation": ("nodes_meteoobservation.csv",
                         [("origin", "s"), ("observationDate", "d"), ("airTemperatureC", "f"),
                          ("airHumidityPercent", "f"), ("daysWithoutRain", "i"),
                          ("soilMoisturePercent", "f")], []),
    "Process": ("nodes_process.csv",
                [("origin", "s"), ("name", "s"), ("plannedDate", "d"),
                 ("harvestVolumeM3", "f"), ("plantedSeedlingsCount", "i")],
                ["SanitaryFelling", "MainFelling", "Reforestation", "FirePreventionMeasure"]),
    "Permit": ("nodes_permit.csv",
               [("origin", "s"), ("number", "s"), ("issuedOn", "d")], ["FellingTicket"]),
    "Quota": ("nodes_quota.csv",
              [("origin", "s"), ("name", "s"), ("limitValue", "f"), ("unit", "s"), ("period", "s")],
              ["HarvestQuota", "NonTimberCollectionLimit"]),
    "Actor": ("nodes_actor.csv",
              [("origin", "s"), ("name", "s"), ("staffCode", "s")],
              ["Forester", "ChiefForester", "HarvestBrigade", "EmergencyService"]),
}

REL_ORDER = ["PART_OF_FORESTRY", "HAS_DOMINANT_SPECIES", "YIELDS_PRODUCT", "AFFECTED_BY",
             "TRIGGERS", "APPLIED_TO", "REQUIRES_PERMIT", "CONSTRAINED_BY", "PERFORMED_BY",
             "SUPERVISES", "NOTIFIES", "FOLLOWED_BY", "MONITORS_UNIT", "LIMITED_BY"]

# --------------------------------------------------------------------------
# 1. Довідники
# --------------------------------------------------------------------------
FORESTRIES = [  # id, код, назва, площа, base
    ("Forestry_LS01", "LS-01", "Карпатське", 4200.0, True),
    ("Forestry_LS02", "LS-02", "Бескидське", 3100.0, False),
    ("Forestry_LS03", "LS-03", "Верховинське", 3650.0, False),
    ("Forestry_LS04", "LS-04", "Дністровське", 2800.0, False),
]
for fid, code, name, area, base in FORESTRIES:
    N("Forestry", fid, base, unitCode=code, name=f"Лісництво «{name}»", areaHectares=area)

SPECIES = [  # id, укр, лат, підтип, base, вага
    ("Species_PiceaAbies", "Ялина європейська", "Picea abies", "ConiferousSpecies", True, 35),
    ("Species_PinusSylvestris", "Сосна звичайна", "Pinus sylvestris", "ConiferousSpecies", True, 12),
    ("Species_FagusSylvatica", "Бук лісовий", "Fagus sylvatica", "DeciduousSpecies", True, 25),
    ("Species_AbiesAlba", "Ялиця біла", "Abies alba", "ConiferousSpecies", False, 10),
    ("Species_LarixDecidua", "Модрина європейська", "Larix decidua", "ConiferousSpecies", False, 4),
    ("Species_QuercusRobur", "Дуб звичайний", "Quercus robur", "DeciduousSpecies", False, 5),
    ("Species_CarpinusBetulus", "Граб звичайний", "Carpinus betulus", "DeciduousSpecies", False, 5),
    ("Species_BetulaPendula", "Береза повисла", "Betula pendula", "DeciduousSpecies", False, 4),
]
CONIFER = {s[0] for s in SPECIES if s[3] == "ConiferousSpecies"}
for sid, uk, lat, st, base, _ in SPECIES:
    N("TreeSpecies", sid, base, subtype=st, name=uk, latinName=lat)

TIMBER_BY_SPECIES = {
    "Species_PiceaAbies": "Product_SpruceTimber",
    "Species_AbiesAlba": "Product_FirTimber",
    "Species_PinusSylvestris": "Product_PineTimber",
    "Species_LarixDecidua": "Product_LarchTimber",
    "Species_FagusSylvatica": "Product_BeechTimber",
    "Species_QuercusRobur": "Product_OakTimber",
    "Species_CarpinusBetulus": "Product_HardwoodFirewood",
    "Species_BetulaPendula": "Product_HardwoodFirewood",
}
PRODUCTS = [  # id, назва, підтип, категорія, base
    ("Product_SpruceTimber", "Деревина ялини", "TimberProduct", "Timber", True),
    ("Product_FirTimber", "Деревина ялиці", "TimberProduct", "Timber", False),
    ("Product_PineTimber", "Деревина сосни", "TimberProduct", "Timber", False),
    ("Product_LarchTimber", "Деревина модрини", "TimberProduct", "Timber", False),
    ("Product_BeechTimber", "Деревина бука", "TimberProduct", "Timber", False),
    ("Product_OakTimber", "Деревина дуба", "TimberProduct", "Timber", False),
    ("Product_HardwoodFirewood", "Дрова твердолистяних", "TimberProduct", "Timber", False),
    ("Product_BoletusMushrooms", "Білі гриби", "NonTimberProduct", "Mushrooms", True),
    ("Product_Blueberries", "Чорниця", "NonTimberProduct", "Berries", True),
    ("Product_Raspberries", "Малина лісова", "NonTimberProduct", "Berries", False),
    ("Product_StJohnsWort", "Звіробій", "NonTimberProduct", "MedicinalHerbs", False),
]
for pid, uk, st, cat, base in PRODUCTS:
    N("ForestProduct", pid, base, subtype=st, name=uk, category=cat)

# Квоти на недеревні продукти (ліміт 800 кг/сезон — з ЛР 6–7)
N("Quota", "Quota_2026_NonTimber_800kg", True, subtype="NonTimberCollectionLimit",
  name="Ліміт збору грибів і чорниці", limitValue=800.0, unit="кг/сезон", period="2026")
N("Quota", "Quota_2026_Raspberries_500kg", False, subtype="NonTimberCollectionLimit",
  name="Ліміт збору малини", limitValue=500.0, unit="кг/сезон", period="2026")
N("Quota", "Quota_2026_Herbs_150kg", False, subtype="NonTimberCollectionLimit",
  name="Ліміт збору лікарських трав", limitValue=150.0, unit="кг/сезон", period="2026")
R("LIMITED_BY", "ForestProduct", "Product_BoletusMushrooms", "Quota", "Quota_2026_NonTimber_800kg", True)
R("LIMITED_BY", "ForestProduct", "Product_Blueberries", "Quota", "Quota_2026_NonTimber_800kg", True)
R("LIMITED_BY", "ForestProduct", "Product_Raspberries", "Quota", "Quota_2026_Raspberries_500kg", False)
R("LIMITED_BY", "ForestProduct", "Product_StJohnsWort", "Quota", "Quota_2026_Herbs_150kg", False)

# --------------------------------------------------------------------------
# 2. Суб'єкти (Actor)
# --------------------------------------------------------------------------
FORESTERS = {
    "Forestry_LS01": ["Forester_F104", "Forester_F101", "Forester_F102"],
    "Forestry_LS02": ["Forester_F201", "Forester_F202", "Forester_F203"],
    "Forestry_LS03": ["Forester_F301", "Forester_F302"],
    "Forestry_LS04": ["Forester_F401", "Forester_F402"],
}
for fid, ids in FORESTERS.items():
    for aid in ids:
        code = "F-" + aid.split("_F")[1]
        if aid == "Forester_F104":
            N("Actor", aid, True, subtype="Forester", name="Фомін О.В.", staffCode=code)
        else:
            N("Actor", aid, False, subtype="Forester", name=f"Лісник {code}", staffCode=code)
CHIEF = {}
for fid, code, *_ in FORESTRIES:
    cid = "Chief_" + code.replace("-", "")
    CHIEF[fid] = cid
    N("Actor", cid, False, subtype="ChiefForester", name=f"Лісничий {code}", staffCode=None)
BRIGADES = ["Brigade_01", "Brigade_02", "Brigade_03"]
N("Actor", "Brigade_01", True, subtype="HarvestBrigade", name="Бригада лісозаготівлі №1", staffCode=None)
N("Actor", "Brigade_02", False, subtype="HarvestBrigade", name="Бригада лісозаготівлі №2", staffCode=None)
N("Actor", "Brigade_03", False, subtype="HarvestBrigade", name="Бригада лісозаготівлі №3", staffCode=None)
N("Actor", "FireService_DSNS_Lviv", True, subtype="EmergencyService",
  name="Пожежна служба ДСНС (Львів)", staffCode=None)
N("Actor", "FireService_DSNS_IvanoFrankivsk", False, subtype="EmergencyService",
  name="Пожежна служба ДСНС (Івано-Франківськ)", staffCode=None)
FIRE_SERVICE = {"Forestry_LS01": "FireService_DSNS_Lviv", "Forestry_LS02": "FireService_DSNS_Lviv",
                "Forestry_LS03": "FireService_DSNS_IvanoFrankivsk",
                "Forestry_LS04": "FireService_DSNS_IvanoFrankivsk"}

# --------------------------------------------------------------------------
# 3. Виділи
# --------------------------------------------------------------------------
BASE_COMP = {
    "V-012": dict(f="Forestry_LS01", sp="Species_PiceaAbies", area=8.4, age=78, dbh=38.0, h=29.0,
                  stock=2690.0, inc=320.0, dmg=12.0, ndvi=0.60),
    "V-003": dict(f="Forestry_LS01", sp="Species_PinusSylvestris", area=12.0, age=105, dbh=44.0, h=31.0,
                  stock=3150.0, inc=280.0, dmg=3.5, ndvi=0.79),
    "V-008": dict(f="Forestry_LS01", sp="Species_FagusSylvatica", area=6.5, age=55, dbh=32.0, h=25.0,
                  stock=2100.0, inc=None, dmg=1.8, ndvi=0.82),
}
SYN_NUMS = {
    "Forestry_LS01": [1, 2, 4, 5, 6, 7, 9, 10, 11, 13, 14],
    "Forestry_LS02": list(range(101, 110)),
    "Forestry_LS03": list(range(201, 210)),
    "Forestry_LS04": list(range(301, 309)),
}
comps = []  # словники з усіма атрибутами
for code, b in BASE_COMP.items():
    comps.append(dict(code=code, base=True, **b))
sp_ids = [s[0] for s in SPECIES]
sp_w = [s[5] for s in SPECIES]
for fid, nums in SYN_NUMS.items():
    for n in nums:
        comps.append(dict(code=f"V-{n:03d}", base=False, f=fid,
                          sp=rnd.choices(sp_ids, sp_w)[0],
                          age=int(round(rnd.triangular(25, 140, 70))),
                          area=round(rnd.uniform(4.0, 16.0), 1),
                          dmg=None, ndvi=None, dbh=None, h=None, stock=None, inc=None))
syn = [c for c in comps if not c["base"]]
syn_conif = [c for c in syn if c["sp"] in CONIFER]
assert len(syn_conif) >= 14, len(syn_conif)

damaged_syn = rnd.sample([c for c in syn_conif if c["sp"] in
                          ("Species_PiceaAbies", "Species_AbiesAlba", "Species_PinusSylvestris")], 6)
rest = [c for c in syn_conif if c not in damaged_syn]
mature_syn = rnd.sample(rest, 5)
for c in mature_syn:
    c["age"] = rnd.randint(85, 130)
healthy = [c for c in syn if c not in damaged_syn]
early_warn = rnd.sample([c for c in healthy if c not in mature_syn], 2)  # NDVI<0.65, ураження<10

for c in syn:
    c["id"] = "Compartment_V" + c["code"][2:]
    c["stock"] = float(round(c["area"] * rnd.uniform(250, 340)))
    c["inc"] = float(round(c["stock"] * rnd.uniform(0.085, 0.12)))
    c["dbh"] = round(c["age"] * rnd.uniform(0.40, 0.55), 1)
    c["h"] = round(11 + c["age"] * 0.22 + rnd.uniform(-1.5, 1.5), 1)
    if c in damaged_syn:
        c["dmg"] = round(rnd.uniform(10.5, 32.0), 1)
        c["ndvi"] = round(rnd.uniform(0.50, 0.66), 2)
    else:
        c["dmg"] = round(rnd.uniform(0.5, 8.0), 1)
        c["ndvi"] = round(rnd.uniform(0.70, 0.88), 2)
    if c in early_warn:
        c["ndvi"] = round(rnd.uniform(0.62, 0.64), 2)
for c in comps:
    if c["base"]:
        c["id"] = "Compartment_V" + c["code"][2:]
comps.sort(key=lambda c: (c["f"], c["code"]))
by_code = {c["code"]: c for c in comps}

for c in comps:
    N("Compartment", c["id"], c["base"], unitCode=c["code"], name=f"Лісовий виділ {c['code']}",
      areaHectares=c["area"], standAgeYears=c["age"], dbhCm=c["dbh"], heightMeters=c["h"],
      timberStockM3=c["stock"], annualIncrementM3=c["inc"], damagedTreesShare=c["dmg"],
      ndviValue=c["ndvi"])
    R("PART_OF_FORESTRY", "Compartment", c["id"], "Forestry", c["f"], c["base"])
    R("HAS_DOMINANT_SPECIES", "Compartment", c["id"], "TreeSpecies", c["sp"], c["base"])

# Продукція виділів
for c in comps:
    timber = TIMBER_BY_SPECIES[c["sp"]]
    explicit_base = c["code"] in ("V-012", "V-008")
    if c["code"] != "V-008":
        R("YIELDS_PRODUCT", "Compartment", c["id"], "ForestProduct", timber, c["code"] == "V-012")
    if c["code"] == "V-008":
        R("YIELDS_PRODUCT", "Compartment", c["id"], "ForestProduct", "Product_BoletusMushrooms", True)
        R("YIELDS_PRODUCT", "Compartment", c["id"], "ForestProduct", "Product_Blueberries", True)
        R("YIELDS_PRODUCT", "Compartment", c["id"], "ForestProduct", timber, False)
        continue
    if c["base"]:
        continue
    extra = []
    if c["sp"] in CONIFER:
        if rnd.random() < 0.5: extra.append("Product_Blueberries")
        if rnd.random() < 0.4: extra.append("Product_BoletusMushrooms")
        if rnd.random() < 0.2: extra.append("Product_StJohnsWort")
    else:
        if rnd.random() < 0.6: extra.append("Product_BoletusMushrooms")
        if rnd.random() < 0.4: extra.append("Product_Raspberries")
    for p in extra:
        R("YIELDS_PRODUCT", "Compartment", c["id"], "ForestProduct", p, False)

# Нагляд (SUPERVISES): один лісник на виділ, лісничий на лісництво
for c in comps:
    if c["code"] == "V-012":
        fo, base = "Forester_F104", True
    else:
        fo, base = rnd.choice(FORESTERS[c["f"]]), False
    c["forester"] = fo
    R("SUPERVISES", "Actor", fo, "Compartment", c["id"], base)
R("SUPERVISES", "Actor", "Forester_F104", "Forestry", "Forestry_LS01", True)  # ЛР7, запит 2
for fid, cid in CHIEF.items():
    R("SUPERVISES", "Actor", cid, "Forestry", fid, False)

# --------------------------------------------------------------------------
# 4. Загрози
# --------------------------------------------------------------------------
threat_by_key = {}


def threat(forestry, kind_key):
    key = (forestry, kind_key)
    if key in threat_by_key:
        return threat_by_key[key]
    ls = forestry[-4:]
    if kind_key == "ips":
        tid = "Threat_IpsTypographus" if forestry == "Forestry_LS01" else f"Threat_IpsTypographus_{ls}"
        N("Threat", tid, False, subtype="InsectPest",
          name="Короїд-типограф (Ips typographus)", kind="Biotic",
          detectedOn=rdate(date(2026, 8, 1), date(2026, 10, 15)))
    elif kind_key == "rot":
        tid = f"Threat_RootRot_{ls}"
        N("Threat", tid, False, subtype="ForestDisease",
          name="Кореневе гниття (Heterobasidion annosum)", kind="Biotic",
          detectedOn=rdate(date(2026, 8, 1), date(2026, 10, 15)))
    elif kind_key == "drought":
        tid = f"Threat_Drought_{ls}"
        N("Threat", tid, False, subtype="Drought", name="Посуха вересня 2026", kind="Abiotic",
          detectedOn=rdate(date(2026, 9, 1), date(2026, 9, 25)))
    else:
        tid = f"Threat_Windthrow_{ls}"
        N("Threat", tid, False, subtype="Windthrow", name="Вітровал 2026", kind="Abiotic",
          detectedOn=rdate(date(2026, 9, 1), date(2026, 10, 25)))
    threat_by_key[key] = tid
    return tid


# Базова загроза з ЛР 6–8: короїд-типограф на V-012 (дата виявлення в звітах не вказана)
N("Threat", "Threat_IpsTypographus", True, subtype="InsectPest",
  name="Короїд-типограф (Ips typographus)", kind="Biotic", detectedOn=None)
threat_by_key[("Forestry_LS01", "ips")] = "Threat_IpsTypographus"
N("Threat", "Threat_Windthrow2026", True, subtype="Windthrow", name="Вітровал 2026",
  kind="Abiotic", detectedOn=None)  # ЛР 6, рис. 2: V-008 affectedByThreat Threat_Windthrow2026
R("AFFECTED_BY", "Compartment", "Compartment_V012", "Threat", "Threat_IpsTypographus", True)
R("AFFECTED_BY", "Compartment", "Compartment_V008", "Threat", "Threat_Windthrow2026", True)
# прибираємо дублікат-вузол, який міг створити threat() (тут не створюється: ключ уже заданий)

comp_threat = {"V-012": "Threat_IpsTypographus"}
for c in damaged_syn:
    if c["sp"] in ("Species_PiceaAbies", "Species_AbiesAlba"):
        kind = "ips" if rnd.random() < 0.7 else "rot"
    else:
        kind = "rot"
    tid = threat(c["f"], kind)
    comp_threat[c["code"]] = tid
    R("AFFECTED_BY", "Compartment", c["id"], "Threat", tid, False,
      D0)
# абіотичні загрози на «здорових» виділах
ok_by_f = defaultdict(list)
for c in comps:
    if c not in damaged_syn and c["code"] != "V-012":
        ok_by_f[c["f"]].append(c)
for c in rnd.sample([x for x in ok_by_f["Forestry_LS03"] if not x["base"]], 2):
    R("AFFECTED_BY", "Compartment", c["id"], "Threat", threat("Forestry_LS03", "drought"), False)
for c in rnd.sample([x for x in ok_by_f["Forestry_LS04"] if not x["base"]], 1):
    R("AFFECTED_BY", "Compartment", c["id"], "Threat", threat("Forestry_LS04", "windthrow"), False)

# --------------------------------------------------------------------------
# 5. Дозволи, квоти, рубки, лісовідновлення
# --------------------------------------------------------------------------
permit_seq = [39]


def next_permit():
    permit_seq[0] += 1
    if permit_seq[0] in (42,):
        permit_seq[0] += 1
    return permit_seq[0]


N("Permit", "Ticket_LK2026_042", True, subtype="FellingTicket", number="ЛК-2026-042", issuedOn=None)
N("Permit", "Ticket_LK2026_039", True, subtype="FellingTicket", number="ЛК-2026-039", issuedOn=None)
N("Quota", "Quota_2026_V012_450m3", True, subtype="HarvestQuota",
  name="Квота заготівлі деревини, виділ V-012", limitValue=450.0, unit="м³/рік", period="2026")
N("Quota", "Quota_2026_V003_300m3", True, subtype="HarvestQuota",
  name="Квота заготівлі деревини, виділ V-003", limitValue=300.0, unit="м³/рік", period="2026")

# Базові процеси
N("Process", "SanitaryFelling_2026_V012", True, subtype="SanitaryFelling",
  name="Вибіркова санітарна рубка V-012", plannedDate=None, harvestVolumeM3=120.0,
  plantedSeedlingsCount=None)
N("Process", "MainFelling_2026_V003", True, subtype="MainFelling",
  name="Рубка головного користування V-003", plannedDate=None, harvestVolumeM3=260.0,
  plantedSeedlingsCount=None)
N("Process", "Planting_Spring2027_V012", True, subtype="Reforestation",
  name="Весняне садіння ялини 2027, V-012", plannedDate=None, harvestVolumeM3=None,
  plantedSeedlingsCount=5000)
R("APPLIED_TO", "Process", "SanitaryFelling_2026_V012", "Compartment", "Compartment_V012", True)
R("APPLIED_TO", "Process", "MainFelling_2026_V003", "Compartment", "Compartment_V003", True)
R("APPLIED_TO", "Process", "Planting_Spring2027_V012", "Compartment", "Compartment_V012", True)
R("REQUIRES_PERMIT", "Process", "SanitaryFelling_2026_V012", "Permit", "Ticket_LK2026_042", True)
R("REQUIRES_PERMIT", "Process", "MainFelling_2026_V003", "Permit", "Ticket_LK2026_039", True)
R("CONSTRAINED_BY", "Process", "SanitaryFelling_2026_V012", "Quota", "Quota_2026_V012_450m3", True)
R("CONSTRAINED_BY", "Process", "MainFelling_2026_V003", "Quota", "Quota_2026_V003_300m3", True)
R("PERFORMED_BY", "Process", "SanitaryFelling_2026_V012", "Actor", "Forester_F104", True)
R("PERFORMED_BY", "Process", "MainFelling_2026_V003", "Actor", "Brigade_01", True)
R("FOLLOWED_BY", "Process", "SanitaryFelling_2026_V012", "Process", "Planting_Spring2027_V012", True)
R("TRIGGERS", "Threat", "Threat_IpsTypographus", "Process", "SanitaryFelling_2026_V012", True)

# Синтетичні санітарні рубки (для уражених виділів)
for c in damaged_syn:
    n = c["code"].replace("-", "")
    when = rdate(date(2026, 10, 1), date(2026, 12, 15))
    vol = float(round(c["stock"] * rnd.uniform(0.03, 0.06)))
    qv = float(math.ceil(vol * rnd.uniform(1.15, 1.6) / 10) * 10)
    pid, qid, tid = f"SanitaryFelling_2026_{n}", f"Quota_2026_{n}_{int(qv)}m3", f"Ticket_LK2026_{next_permit():03d}"
    N("Process", pid, False, subtype="SanitaryFelling", name=f"Вибіркова санітарна рубка {c['code']}",
      plannedDate=when, harvestVolumeM3=vol, plantedSeedlingsCount=None)
    N("Quota", qid, False, subtype="HarvestQuota", name=f"Квота заготівлі деревини, виділ {c['code']}",
      limitValue=qv, unit="м³/рік", period="2026")
    num = tid.split("_LK2026_")[1]
    N("Permit", tid, False, subtype="FellingTicket", number=f"ЛК-2026-{num}",
      issuedOn=when - timedelta(days=rnd.randint(10, 30)))
    R("APPLIED_TO", "Process", pid, "Compartment", c["id"], False, when)
    R("REQUIRES_PERMIT", "Process", pid, "Permit", tid, False, when)
    R("CONSTRAINED_BY", "Process", pid, "Quota", qid, False, when)
    R("PERFORMED_BY", "Process", pid, "Actor", c["forester"], False, when)
    R("TRIGGERS", "Threat", comp_threat[c["code"]], "Process", pid, False, when)
    # лісовідновлення
    rid = f"Planting_Spring2027_{n}"
    rwhen = rdate(date(2027, 4, 5), date(2027, 5, 20))
    N("Process", rid, False, subtype="Reforestation", name=f"Весняне садіння культур 2027, {c['code']}",
      plannedDate=rwhen, harvestVolumeM3=None,
      plantedSeedlingsCount=int(round(c["area"] * rnd.uniform(550, 650), -2)))
    R("APPLIED_TO", "Process", rid, "Compartment", c["id"], False, rwhen)
    R("FOLLOWED_BY", "Process", pid, "Process", rid, False, rwhen)

# Синтетичні рубки головного користування (стиглі хвойні)
ANOMALY = mature_syn[0]  # навмисний тестовий випадок: обсяг > квоти і > приросту
for c in mature_syn:
    n = c["code"].replace("-", "")
    when = rdate(date(2026, 11, 1), date(2027, 2, 28))
    if c is ANOMALY:
        vol = float(round(c["inc"] * 1.25))
        qv = float(math.floor(vol * 0.9 / 10) * 10)
    else:
        vol = float(round(c["inc"] * rnd.uniform(0.55, 0.92)))
        qv = float(math.ceil(vol * rnd.uniform(1.15, 1.6) / 10) * 10)
    pid, qid, tid = f"MainFelling_2026_{n}", f"Quota_2026_{n}_{int(qv)}m3", f"Ticket_LK2026_{next_permit():03d}"
    N("Process", pid, False, subtype="MainFelling", name=f"Рубка головного користування {c['code']}",
      plannedDate=when, harvestVolumeM3=vol, plantedSeedlingsCount=None)
    N("Quota", qid, False, subtype="HarvestQuota", name=f"Квота заготівлі деревини, виділ {c['code']}",
      limitValue=qv, unit="м³/рік", period="2026")
    num = tid.split("_LK2026_")[1]
    N("Permit", tid, False, subtype="FellingTicket", number=f"ЛК-2026-{num}",
      issuedOn=when - timedelta(days=rnd.randint(10, 30)))
    R("APPLIED_TO", "Process", pid, "Compartment", c["id"], False, when)
    R("REQUIRES_PERMIT", "Process", pid, "Permit", tid, False, when)
    R("CONSTRAINED_BY", "Process", pid, "Quota", qid, False, when)
    R("PERFORMED_BY", "Process", pid, "Actor", rnd.choice(BRIGADES), False, when)
# лісовідновлення лише для 3 із 5 синтетичних рубок головного користування
for c in rnd.sample(mature_syn, 3):
    n = c["code"].replace("-", "")
    rid = f"Planting_Spring2027_{n}"
    rwhen = rdate(date(2027, 4, 5), date(2027, 5, 20))
    N("Process", rid, False, subtype="Reforestation", name=f"Весняне садіння культур 2027, {c['code']}",
      plannedDate=rwhen, harvestVolumeM3=None,
      plantedSeedlingsCount=int(round(c["area"] * rnd.uniform(550, 650), -2)))
    R("APPLIED_TO", "Process", rid, "Compartment", c["id"], False, rwhen)
    R("FOLLOWED_BY", "Process", f"MainFelling_2026_{n}", "Process", rid, False, rwhen)

# --------------------------------------------------------------------------
# 6. Метеоспостереження та пожежні заходи
# --------------------------------------------------------------------------
N("MeteoObservation", "MeteoObs_2026_09_05_LS01", True, observationDate=date(2026, 9, 5),
  airTemperatureC=31.0, airHumidityPercent=27.0, daysWithoutRain=9, soilMoisturePercent=24.0)
N("MeteoObservation", "MeteoObs_2026_10_28_LS01", True, observationDate=date(2026, 10, 28),
  airTemperatureC=14.5, airHumidityPercent=75.0, daysWithoutRain=0, soilMoisturePercent=None)
R("MONITORS_UNIT", "MeteoObservation", "MeteoObs_2026_09_05_LS01", "Forestry", "Forestry_LS01", True,
  date(2026, 9, 5))
R("MONITORS_UNIT", "MeteoObservation", "MeteoObs_2026_10_28_LS01", "Forestry", "Forestry_LS01", True,
  date(2026, 10, 28))

# (лісництво, режим): high = перевищено усі три пороги; nm_h/nm_d = «майже»
SYN_METEO = [("Forestry_LS01", "nm_h"), ("Forestry_LS01", "normal"), ("Forestry_LS01", "normal"),
             ("Forestry_LS02", "high"), ("Forestry_LS02", "nm_d"), ("Forestry_LS02", "normal"),
             ("Forestry_LS02", "normal"), ("Forestry_LS02", "normal"),
             ("Forestry_LS03", "high"), ("Forestry_LS03", "normal"), ("Forestry_LS03", "normal"),
             ("Forestry_LS03", "normal"), ("Forestry_LS03", "normal"),
             ("Forestry_LS04", "high"), ("Forestry_LS04", "normal"), ("Forestry_LS04", "normal"),
             ("Forestry_LS04", "normal"), ("Forestry_LS04", "normal")]
used = {("Forestry_LS01", date(2026, 9, 5)), ("Forestry_LS01", date(2026, 10, 28))}
high_obs = [("MeteoObs_2026_09_05_LS01", "Forestry_LS01", date(2026, 9, 5), True)]
for fid, mode in SYN_METEO:
    while True:
        d = rdate(date(2026, 9, 1), date(2026, 10, 31)) if mode != "high" else rdate(date(2026, 9, 3), date(2026, 9, 20))
        if (fid, d) not in used:
            used.add((fid, d)); break
    if mode == "high":
        t, h, dd = round(rnd.uniform(30.5, 34.0), 1), round(rnd.uniform(18.0, 29.0), 1), rnd.randint(7, 14)
    elif mode == "nm_h":  # спека і посуха, але вологість >= 30
        t, h, dd = round(rnd.uniform(30.5, 32.5), 1), round(rnd.uniform(38.0, 46.0), 1), rnd.randint(7, 10)
    elif mode == "nm_d":  # спека і сухе повітря, але лише 5 діб без опадів
        t, h, dd = round(rnd.uniform(30.5, 33.0), 1), round(rnd.uniform(22.0, 28.0), 1), 5
    else:
        t, h, dd = round(rnd.uniform(6.0, 24.0), 1), round(rnd.uniform(45.0, 92.0), 1), rnd.randint(0, 5)
    oid = f"MeteoObs_{d:%Y_%m_%d}_{fid[-4:]}"
    N("MeteoObservation", oid, False, observationDate=d, airTemperatureC=t, airHumidityPercent=h,
      daysWithoutRain=dd, soilMoisturePercent=round(rnd.uniform(22.0, 60.0), 1))
    R("MONITORS_UNIT", "MeteoObservation", oid, "Forestry", fid, False, d)
    if mode == "high":
        high_obs.append((oid, fid, d, False))

for oid, fid, d, base in high_obs:
    pid = "FirePatrol_Sept2026_LS01" if base else f"FirePatrol_{d:%Y_%m_%d}_{fid[-4:]}"
    N("Process", pid, base, subtype="FirePreventionMeasure",
      name=f"Протипожежне патрулювання {fid[-4:].replace('LS', 'LS-')}", plannedDate=None if base else d,
      harvestVolumeM3=None, plantedSeedlingsCount=None)
    R("TRIGGERS", "MeteoObservation", oid, "Process", pid, base, d)
    fo = "Forester_F104" if base else rnd.choice(FORESTERS[fid])
    R("PERFORMED_BY", "Process", pid, "Actor", fo, base, d)
    R("NOTIFIES", "Process", pid, "Actor", FIRE_SERVICE[fid], base, d)

# --------------------------------------------------------------------------
# 7. Запис CSV
# --------------------------------------------------------------------------


def cell(v):
    if v is None:
        return ""
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


os.makedirs(DATA, exist_ok=True)
os.makedirs(IMPORT, exist_ok=True)
for f in os.listdir(DATA):
    if f.endswith(".csv"):
        os.remove(os.path.join(DATA, f))

for label, (fname, cols, subtypes) in NODE_SPECS.items():
    header = ["id"] + (["subtype"] if subtypes else []) + [c for c, _ in cols]
    with open(os.path.join(DATA, fname), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for row in nodes[label]:
            w.writerow([cell(row.get(h)) for h in header])

REL_HEADER = ["start_label", "start_id", "end_label", "end_id", "source", "confidence", "validFrom"]
for typ in REL_ORDER:
    seen = set()
    with open(os.path.join(DATA, f"rels_{typ}.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(REL_HEADER)
        for r in rels[typ]:
            key = (r["start_id"], r["end_id"])
            assert key not in seen, (typ, key)  # один зв'язок типу між парою вузлів
            seen.add(key)
            w.writerow([cell(r[h]) for h in REL_HEADER])

# --------------------------------------------------------------------------
# 8. Cypher-імпорт
# --------------------------------------------------------------------------
CAST = {"s": "{v}", "f": "toFloat({v})", "i": "toInteger({v})", "d": "date({v})"}


def val(col, t):
    v = f"row.{col}"
    return f"CASE {v} WHEN '' THEN null ELSE {CAST[t].format(v=v)} END"


out = ["// ЛР 9. Імпорт вузлів (ідемпотентний: MERGE за унікальним id).",
       "// Файли CSV монтуються у каталог import контейнера Neo4j (див. docker-compose.yml).", ""]
for label, (fname, cols, subtypes) in NODE_SPECS.items():
    sets = ",\n    ".join(f"n.{c} = {val(c, t)}" for c, t in cols)
    if subtypes:
        for st in subtypes:
            out.append(f"// {label}:{st}")
            out.append(f"LOAD CSV WITH HEADERS FROM 'file:///{fname}' AS row")
            out.append(f"WITH row WHERE row.subtype = '{st}'")
            # SanitaryFelling і MainFelling — підкласи TimberHarvesting в онтології ЛР 6
            extra = ":TimberHarvesting" if st in ("SanitaryFelling", "MainFelling") else ""
            out.append(f"MERGE (n:{label}{extra}:{st} {{id: row.id}})")
            out.append(f"SET {sets};\n")
    else:
        out.append(f"// {label}")
        out.append(f"LOAD CSV WITH HEADERS FROM 'file:///{fname}' AS row")
        out.append(f"MERGE (n:{label} {{id: row.id}})")
        out.append(f"SET {sets};\n")
with open(os.path.join(IMPORT, "01_import_nodes.cypher"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))

out = ["// ЛР 9. Імпорт зв'язків із властивостями походження (source, confidence, validFrom).",
       "// MERGE за шаблоном (a)-[:TYPE]->(b) гарантує відсутність дублікатів при повторному запуску.", ""]
for typ in REL_ORDER:
    combos = sorted({(r["start_label"], r["end_label"]) for r in rels[typ]})
    for sl, el in combos:
        out.append(f"// {typ}: {sl} -> {el}")
        out.append(f"LOAD CSV WITH HEADERS FROM 'file:///rels_{typ}.csv' AS row")
        out.append(f"WITH row WHERE row.start_label = '{sl}' AND row.end_label = '{el}'")
        out.append(f"MATCH (a:{sl} {{id: row.start_id}})")
        out.append(f"MATCH (b:{el} {{id: row.end_id}})")
        out.append(f"MERGE (a)-[r:{typ}]->(b)")
        out.append("SET r.source = row.source, r.confidence = toFloat(row.confidence),"
                   " r.validFrom = date(row.validFrom);\n")
with open(os.path.join(IMPORT, "02_import_rels.cypher"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))

# --------------------------------------------------------------------------
# 9. Підсумок
# --------------------------------------------------------------------------
n_nodes = sum(len(v) for v in nodes.values())
n_rels = sum(len(v) for v in rels.values())
print(f"nodes={n_nodes}  relationships={n_rels}")
for k, v in nodes.items():
    print(f"  {k:18s} {len(v)}")
for k in REL_ORDER:
    print(f"  {k:22s} {len(rels[k])}")
print("anomaly compartment:", ANOMALY["code"])
