#!/usr/bin/env python3
"""
Результат 2 (ELT): Генерація документованого набору подій (>= 1000 рядків),
завантаження зіркової схеми, перевірка ключів (відсутність «сиріт»),
>= 5 перевірок якості даних, збереження у Parquet та діаграма зірки.

Підтримує DuckDB як основний рушій (якщо встановлено `duckdb`) та
автоматичний SQLite + PyArrow Parquet fallback для офлайн-середовищ.
"""
import hashlib
import json
import os
import sqlite3
from datetime import date, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

SEED = 42
DATASET_VERSION = "1.0.0"
N_FACTS = 1500
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
DDL_PATH = os.path.join(BASE_DIR, "sql", "ddl.sql")


def build_dim_date() -> pd.DataFrame:
    months_uk = {
        1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
        5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
        9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
    }
    seasons = {
        12: "Зима", 1: "Зима", 2: "Зима",
        3: "Весна", 4: "Весна", 5: "Весна",
        6: "Літо", 7: "Літо", 8: "Літо",
        9: "Осінь", 10: "Осінь", 11: "Осінь",
    }
    rows = []
    cur = date(2024, 1, 1)
    end = date(2026, 10, 31)
    while cur <= end:
        q = (cur.month - 1) // 3 + 1
        rows.append({
            "date_sk": int(cur.strftime("%Y%m%d")),
            "full_date": cur.isoformat(),
            "year": cur.year,
            "quarter": q,
            "quarter_label": f"Q{q}",
            "month": cur.month,
            "month_name_uk": months_uk[cur.month],
            "year_month": cur.strftime("%Y-%m"),
            "season": seasons[cur.month],
            "is_fire_hazard_season": cur.month in (6, 7, 8, 9),
        })
        cur += timedelta(days=1)
    return pd.DataFrame(rows)


def build_dim_product_taxonomy() -> pd.DataFrame:
    """Таксономія лісових продуктів із ЛР 5 з IRI (простір https://foresthub.ua/onto/)."""
    items = [
        (1, "https://foresthub.ua/onto/Product_SpruceTimber", "https://foresthub.ua/onto/ConiferousTimber",
         "FP-TIM-CON-01", "Деревинні продукти", "Хвойна деревина", "Деревина ялини", "м³", True, 3450.0),
        (2, "https://foresthub.ua/onto/Product_FirTimber", "https://foresthub.ua/onto/ConiferousTimber",
         "FP-TIM-CON-02", "Деревинні продукти", "Хвойна деревина", "Деревина ялиці", "м³", True, 3300.0),
        (3, "https://foresthub.ua/onto/Product_PineTimber", "https://foresthub.ua/onto/ConiferousTimber",
         "FP-TIM-CON-03", "Деревинні продукти", "Хвойна деревина", "Деревина сосни", "м³", True, 3150.0),
        (4, "https://foresthub.ua/onto/Product_LarchTimber", "https://foresthub.ua/onto/ConiferousTimber",
         "FP-TIM-CON-04", "Деревинні продукти", "Хвойна деревина", "Деревина модрини", "м³", True, 3900.0),
        (5, "https://foresthub.ua/onto/Product_BeechTimber", "https://foresthub.ua/onto/BroadleafTimber",
         "FP-TIM-BRD-01", "Деревинні продукти", "Листяна деревина", "Деревина бука", "м³", True, 4200.0),
        (6, "https://foresthub.ua/onto/Product_OakTimber", "https://foresthub.ua/onto/BroadleafTimber",
         "FP-TIM-BRD-02", "Деревинні продукти", "Листяна деревина", "Деревина дуба", "м³", True, 5600.0),
        (7, "https://foresthub.ua/onto/Product_HardwoodFirewood", "https://foresthub.ua/onto/Fuelwood",
         "FP-TIM-FUL-01", "Деревинні продукти", "Паливна деревина", "Дрова твердолистяних", "м³", False, 1450.0),
        (8, "https://foresthub.ua/onto/Product_BoletusMushrooms", "https://foresthub.ua/onto/Mushrooms",
         "FP-NTF-MSH-01", "Недеревинні продукти", "Гриби", "Білі гриби", "кг", True, 380.0),
        (9, "https://foresthub.ua/onto/Product_Blueberries", "https://foresthub.ua/onto/Berries",
         "FP-NTF-BER-01", "Недеревинні продукти", "Ягоди", "Чорниця", "кг", True, 210.0),
        (10, "https://foresthub.ua/onto/Product_Raspberries", "https://foresthub.ua/onto/Berries",
         "FP-NTF-BER-02", "Недеревинні продукти", "Ягоди", "Малина лісова", "кг", False, 240.0),
        (11, "https://foresthub.ua/onto/Product_StJohnsWort", "https://foresthub.ua/onto/MedicinalHerbs",
         "FP-NTF-HRB-01", "Недеревинні продукти", "Лікарські рослини", "Звіробій", "кг", True, 290.0),
    ]
    rows = []
    for rec in items:
        rows.append({
            "product_sk": rec[0],
            "product_iri": rec[1],
            "parent_iri": rec[2],
            "skos_notation": rec[3],
            "top_class_uk": rec[4],
            "subclass_uk": rec[5],
            "product_name_uk": rec[6],
            "unit_base": rec[7],
            "fsc_eligible": rec[8],
            "ref_price_uah": rec[9],
            "scd_type": "SCD1",
            "updated_at": "2026-01-15",
        })
    return pd.DataFrame(rows)


def build_dim_location() -> pd.DataFrame:
    """Виділи та лісництва з ЛР 7–11 із підтримкою SCD Type 2 (зміна FSC-статусу)."""
    forestries = {
        "LS-01": ("Лісництво «Карпатське»", "Львівська обл."),
        "LS-02": ("Лісництво «Бескидське»", "Львівська обл."),
        "LS-03": ("Лісництво «Верховинське»", "Івано-Франківська обл."),
        "LS-04": ("Лісництво «Дністровське»", "Львівська обл."),
    }
    compartments = [
        ("V-001", "LS-01", 7.3, "Ялина європейська", 175.0, "Середній (0.60-0.75)", True),
        ("V-002", "LS-01", 12.1, "Бук лісовий", 470.0, "Високий (>=0.75)", True),
        ("V-003", "LS-01", 12.0, "Ялина європейська", 280.0, "Високий (>=0.75)", True),
        ("V-008", "LS-01", 6.5, "Ялиця біла", 210.0, "Високий (>=0.75)", True),
        ("V-012", "LS-01", 8.4, "Ялина європейська", 320.0, "Середній (0.60-0.75)", True),
        ("V-014", "LS-01", 10.4, "Сосна звичайна", 319.0, "Низький (<0.60)", False),
        ("V-101", "LS-02", 10.6, "Бук лісовий", 339.0, "Середній (0.60-0.75)", True),
        ("V-102", "LS-02", 14.3, "Дуб звичайний", 555.0, "Середній (0.60-0.75)", True),
        ("V-105", "LS-02", 7.3, "Сосна звичайна", 241.0, "Високий (>=0.75)", True),
        ("V-107", "LS-02", 15.2, "Ялина європейська", 476.0, "Середній (0.60-0.75)", False),
        ("V-201", "LS-03", 10.7, "Ялиця біла", 287.0, "Високий (>=0.75)", True),
        ("V-202", "LS-03", 13.3, "Модрина європейська", 345.0, "Середній (0.60-0.75)", True),
        ("V-203", "LS-03", 7.8, "Ялина європейська", 251.0, "Низький (<0.60)", False),
        ("V-204", "LS-03", 15.3, "Бук лісовий", 545.0, "Середній (0.60-0.75)", True),
        ("V-205", "LS-04", 11.9, "Дуб звичайний", 368.0, "Середній (0.60-0.75)", True),
        ("V-206", "LS-04", 9.5, "Бук лісовий", 257.0, "Середній (0.60-0.75)", False),
    ]
    rows = []
    sk = 1
    for code, fcode, area, sp, inc, ndvi_b, fsc in compartments:
        fname, reg = forestries[fcode]
        # Для V-107 та V-206 моделюємо SCD Type 2 перехід (отримання FSC з 2025-07-01)
        if code in ("V-107", "V-206"):
            rows.append({
                "location_sk": sk, "compartment_code": code, "compartment_name": f"Лісовий виділ {code}",
                "forestry_code": fcode, "forestry_name": fname, "region_name": reg,
                "area_ha": area, "dominant_species": sp, "annual_increment_m3": inc,
                "ndvi_band": ndvi_b, "fsc_certified": False,
                "valid_from": "2024-01-01", "valid_to": "2025-06-30", "is_current": False,
            })
            sk += 1
            rows.append({
                "location_sk": sk, "compartment_code": code, "compartment_name": f"Лісовий виділ {code}",
                "forestry_code": fcode, "forestry_name": fname, "region_name": reg,
                "area_ha": area, "dominant_species": sp, "annual_increment_m3": inc,
                "ndvi_band": ndvi_b, "fsc_certified": True,
                "valid_from": "2025-07-01", "valid_to": "9999-12-31", "is_current": True,
            })
            sk += 1
        else:
            rows.append({
                "location_sk": sk, "compartment_code": code, "compartment_name": f"Лісовий виділ {code}",
                "forestry_code": fcode, "forestry_name": fname, "region_name": reg,
                "area_ha": area, "dominant_species": sp, "annual_increment_m3": inc,
                "ndvi_band": ndvi_b, "fsc_certified": fsc,
                "valid_from": "2024-01-01", "valid_to": "9999-12-31", "is_current": True,
            })
            sk += 1
    return pd.DataFrame(rows)


def build_dim_actor() -> pd.DataFrame:
    actors = [
        (1, "Forester_F104", "F-104", "Фомін О.В.", "Forester", "LS-01", "Старший лісник"),
        (2, "Forester_F101", "F-101", "Лісник F-101", "Forester", "LS-01", "Лісник I кат."),
        (3, "Forester_F201", "F-201", "Лісник F-201", "Forester", "LS-02", "Старший лісник"),
        (4, "Forester_F202", "F-202", "Лісник F-202", "Forester", "LS-02", "Лісник I кат."),
        (5, "Forester_F301", "F-301", "Лісник F-301", "Forester", "LS-03", "Старший лісник"),
        (6, "Forester_F302", "F-302", "Лісник F-302", "Forester", "LS-03", "Лісник II кат."),
        (7, "Forester_F401", "F-401", "Лісник F-401", "Forester", "LS-04", "Старший лісник"),
        (8, "Brigade_01", "BR-01", "Бригада лісозаготівлі №1", "HarvestBrigade", "LS-01", "Механізована"),
        (9, "Brigade_02", "BR-02", "Бригада лісозаготівлі №2", "HarvestBrigade", "LS-02", "Механізована"),
        (10, "Brigade_03", "BR-03", "Бригада лісозаготівлі №3", "HarvestBrigade", "LS-03", "Гірська канатна"),
    ]
    rows = []
    for a in actors:
        rows.append({
            "actor_sk": a[0], "actor_id": a[1], "staff_code": a[2], "actor_name": a[3],
            "actor_type": a[4], "forestry_code": a[5], "qualification_level": a[6],
            "valid_from": "2024-01-01", "valid_to": "9999-12-31", "is_current": True,
        })
    return pd.DataFrame(rows)


def build_dim_permit() -> pd.DataFrame:
    permits = [
        (1, "LK-2024-01", "Лісорубний квиток", "Низький", 450.0, 2024),
        (2, "LK-2024-02", "Санітарний дозвіл", "Високий", 260.0, 2024),
        (3, "LK-2024-03", "Лісовий квиток (НДП)", "Низький", 0.0, 2024),
        (4, "LK-2025-01", "Лісорубний квиток", "Низький", 520.0, 2025),
        (5, "LK-2025-02", "Санітарний дозвіл", "Середній", 300.0, 2025),
        (6, "LK-2025-03", "Лісовий квиток (НДП)", "Низький", 0.0, 2025),
        (7, "LK-2026-01", "Лісорубний квиток", "Низький", 550.0, 2026),
        (8, "LK-2026-02", "Санітарний дозвіл", "Високий", 280.0, 2026),
        (9, "LK-2026-03", "Лісовий квиток (НДП)", "Низький", 0.0, 2026),
    ]
    return pd.DataFrame(permits, columns=[
        "permit_sk", "permit_code", "permit_type", "eco_risk_level", "quota_limit_m3", "issued_year"
    ])


def build_fact_harvest(dim_date, dim_prod, dim_loc, dim_actor, dim_permit) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    date_records = dim_date.to_dict("records")
    prod_records = dim_prod.to_dict("records")
    loc_records = dim_loc.to_dict("records")
    actor_records = dim_actor.to_dict("records")
    permit_records = dim_permit.to_dict("records")

    # Індекси для швидкого підбору за лісництвом, роком і SCD2-датою
    actors_by_f = {}
    for a in actor_records:
        actors_by_f.setdefault(a["forestry_code"], []).append(a)
    permits_by_yr_type = {}
    for p in permit_records:
        permits_by_yr_type[(p["issued_year"], p["permit_type"])] = p

    # Ваги продуктів (75% деревина, 25% недеревинні)
    p_weights = np.array([0.16, 0.11, 0.12, 0.07, 0.13, 0.10, 0.08, 0.07, 0.07, 0.05, 0.04])
    p_weights = p_weights / p_weights.sum()

    rows = []
    for fid in range(1, N_FACTS + 1):
        d = date_records[int(rng.integers(0, len(date_records)))]
        prod = prod_records[int(rng.choice(len(prod_records), p=p_weights))]

        # Сезонне коригування: ягоди/гриби переважно влітку/восени
        if prod["top_class_uk"] == "Недеревинні продукти" and d["month"] in (1, 2, 12):
            summer_dates = [x for x in date_records if x["year"] == d["year"] and x["month"] in (6, 7, 8, 9, 10)]
            d = summer_dates[int(rng.integers(0, len(summer_dates)))]

        # Вибір активної на дату SCD2-версії виділу
        valid_locs = [l for l in loc_records if l["valid_from"] <= d["full_date"] <= l["valid_to"]]
        loc = valid_locs[int(rng.integers(0, len(valid_locs)))]

        # Виконавець із цього ж лісництва
        f_actors = actors_by_f[loc["forestry_code"]]
        actor = f_actors[int(rng.integers(0, len(f_actors)))]

        # Дозвіл відповідного року та типу
        if prod["top_class_uk"] == "Недеревинні продукти":
            ptype = "Лісовий квиток (НДП)"
        else:
            ptype = "Санітарний дозвіл" if loc["ndvi_band"].startswith("Низький") or rng.random() < 0.22 else "Лісорубний квиток"
        perm = permits_by_yr_type[(d["year"], ptype)]

        # Генерація мір
        price_mult = rng.uniform(0.92, 1.12) * (1.06 if loc["fsc_certified"] else 1.0)
        unit_price = round(prod["ref_price_uah"] * price_mult, 2)

        if prod["unit_base"] == "м³":
            # Вищі обсяги для бригад та у невисокопожежний період
            base_vol = rng.uniform(14.0, 52.0) if actor["actor_type"] == "HarvestBrigade" else rng.uniform(6.0, 26.0)
            if d["is_fire_hazard_season"]:
                base_vol *= 0.85
            volume_m3 = round(float(base_vol), 2)
            mass_kg = 0.0
            revenue = round(volume_m3 * unit_price, 2)
            cost_ratio = rng.uniform(0.56, 0.72)
        else:
            volume_m3 = 0.0
            mass_kg = round(float(rng.uniform(45.0, 320.0)), 2)
            revenue = round(mass_kg * unit_price, 2)
            cost_ratio = rng.uniform(0.42, 0.58)

        cost = round(revenue * cost_ratio, 2)
        margin = round(revenue - cost, 2)
        margin_pct = round(100.0 * margin / revenue, 2)

        # Напівадитивні й неадитивні екологічні метрики
        rem_quota = round(max(0.0, perm["quota_limit_m3"] - volume_m3 * rng.uniform(1.0, 4.5)), 2)
        standing_stock = round(loc["annual_increment_m3"] * rng.uniform(7.5, 10.5), 1)
        if loc["ndvi_band"].startswith("Високий"):
            ndvi = round(float(rng.uniform(0.75, 0.89)), 3)
            dmg = round(float(rng.uniform(1.0, 4.5)), 2)
        elif loc["ndvi_band"].startswith("Середній"):
            ndvi = round(float(rng.uniform(0.60, 0.74)), 3)
            dmg = round(float(rng.uniform(4.0, 10.5)), 2)
        else:
            ndvi = round(float(rng.uniform(0.48, 0.59)), 3)
            dmg = round(float(rng.uniform(11.0, 22.0)), 2)

        rows.append({
            "fact_id": fid,
            "date_sk": d["date_sk"],
            "product_sk": prod["product_sk"],
            "location_sk": loc["location_sk"],
            "actor_sk": actor["actor_sk"],
            "permit_sk": perm["permit_sk"],
            "volume_m3": volume_m3,
            "mass_kg": mass_kg,
            "revenue_uah": revenue,
            "cost_uah": cost,
            "margin_uah": margin,
            "event_count": 1,
            "remaining_quota_m3": rem_quota,
            "standing_stock_m3": standing_stock,
            "unit_price_uah": unit_price,
            "margin_pct": margin_pct,
            "damaged_trees_share_pct": dmg,
            "ndvi_score": ndvi,
        })
    return pd.DataFrame(rows)


def draw_star_schema(out_path: str):
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=180)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")

    def box(x, y, w, h, title, lines, header_bg="#2C3E50", body_bg="#F8F9FA"):
        # Тіло
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3",
                                    facecolor=body_bg, edgecolor="#111111", linewidth=1.2))
        # Заголовок
        hh = 4.5
        ax.add_patch(FancyBboxPatch((x, y + h - hh), w, hh, boxstyle="round,pad=0.3",
                                    facecolor=header_bg, edgecolor="#111111", linewidth=1.2))
        ax.text(x + w / 2, y + h - hh / 2, title, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="white", family="DejaVu Sans")
        for idx, ln in enumerate(lines):
            ax.text(x + 1.0, y + h - hh - 2.3 - idx * 2.45, ln, ha="left", va="center",
                    fontsize=7.8, color="#111111", family="DejaVu Sans")

    # Центральна таблиця фактів
    box(33, 18, 34, 24, "fact_forest_harvest (Зерно: 1 подія)", [
        "PK  fact_id",
        "FK  date_sk, product_sk, location_sk",
        "FK  actor_sk, permit_sk",
        "Адитивні: volume_m3, mass_kg, revenue_uah,",
        "          cost_uah, margin_uah, event_count",
        "Напівадит.: remaining_quota_m3, standing_stock_m3",
        "Неадитивні: unit_price_uah, margin_pct, ndvi_score",
    ], header_bg="#1B4F72", body_bg="#EBF5FB")

    # Виміри
    box(35, 48, 30, 12.5, "dim_date (SCD0)", [
        "PK  date_sk (YYYYMMDD)",
        "year -> quarter -> month -> full_date",
        "season, is_fire_hazard_season",
    ], header_bg="#2E4053")

    box(2, 23, 27, 17, "dim_product_taxonomy (SCD1)", [
        "PK  product_sk",
        "product_iri (ЛР 5 IRI), parent_iri",
        "top_class_uk -> subclass_uk",
        "-> product_name_uk, unit_base",
        "fsc_eligible, ref_price_uah",
    ], header_bg="#1E8449", body_bg="#EAFAF1")

    box(71, 23, 27, 17, "dim_location (SCD2)", [
        "PK  location_sk",
        "region_name -> forestry_code",
        "-> compartment_code (V-001..V-206)",
        "area_ha, annual_increment_m3, fsc",
        "valid_from, valid_to, is_current",
    ], header_bg="#2E4053")

    box(8, 2, 34, 12, "dim_actor (SCD2)", [
        "PK  actor_sk | staff_code, actor_name",
        "actor_type -> forestry_code",
        "valid_from, valid_to, is_current",
    ], header_bg="#2E4053")

    box(58, 2, 34, 12, "dim_permit (SCD1)", [
        "PK  permit_sk | permit_code",
        "permit_type -> eco_risk_level",
        "quota_limit_m3, issued_year",
    ], header_bg="#2E4053")

    # Зв'язки 1:N
    arrows = [
        ((50, 48), (50, 42.3)),       # dim_date -> fact
        ((29.3, 31.5), (32.7, 31.5)), # dim_product -> fact
        ((70.7, 31.5), (67.3, 31.5)), # dim_location -> fact
        ((30, 14.3), (42, 17.7)),     # dim_actor -> fact
        ((70, 14.3), (58, 17.7)),     # dim_permit -> fact
    ]
    for p1, p2 in arrows:
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="-|>", color="#111111", lw=1.3))

    plt.tight_layout(pad=0.3)
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def run_etl():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    tables = {
        "dim_date": build_dim_date(),
        "dim_product_taxonomy": build_dim_product_taxonomy(),
        "dim_location": build_dim_location(),
        "dim_actor": build_dim_actor(),
        "dim_permit": build_dim_permit(),
    }
    tables["fact_forest_harvest"] = build_fact_harvest(
        tables["dim_date"], tables["dim_product_taxonomy"],
        tables["dim_location"], tables["dim_actor"], tables["dim_permit"]
    )

    # Збереження у Parquet (PyArrow)
    manifest_files = {}
    for name, df in tables.items():
        pq_path = os.path.join(DATA_DIR, f"{name}.parquet")
        df.to_parquet(pq_path, index=False, engine="pyarrow")
        h = hashlib.sha256(open(pq_path, "rb").read()).hexdigest()[:16]
        manifest_files[f"{name}.parquet"] = {"rows": len(df), "cols": len(df.columns), "sha256_16": h}

    # Завантаження у БД (DuckDB якщо є, інакше SQLite з тим самим DDL-контрактом)
    db_engine = "duckdb" if HAS_DUCKDB else "sqlite3"
    if HAS_DUCKDB:
        db_path = os.path.join(DATA_DIR, "forest_olap.duckdb")
        if os.path.exists(db_path):
            os.remove(db_path)
        con = duckdb.connect(db_path)
        con.execute(open(DDL_PATH, encoding="utf-8").read())
        for name in ["dim_date", "dim_product_taxonomy", "dim_location", "dim_actor", "dim_permit", "fact_forest_harvest"]:
            con.execute(f"INSERT INTO {name} SELECT * FROM read_parquet('{os.path.join(DATA_DIR, name + '.parquet')}')")
        def q_scalar(sql):
            return con.execute(sql).fetchone()[0]
    else:
        db_path = os.path.join(DATA_DIR, "forest_olap.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)
        con = sqlite3.connect(db_path)
        ddl_sqlite = open(DDL_PATH, encoding="utf-8").read().replace("DOUBLE", "REAL").replace("VARCHAR", "TEXT")
        con.executescript(ddl_sqlite)
        for name, df in tables.items():
            df.to_sql(name, con, if_exists="append", index=False)
        def q_scalar(sql):
            return con.execute(sql).fetchone()[0]

    # Перевірка «сиріт» (C2) та >= 5 перевірок якості даних (C3)
    checks = [
        ("DQ1_fact_row_count_ge_1000", "Кількість рядків факту >= 1000",
         "SELECT COUNT(*) FROM fact_forest_harvest", lambda v: v >= 1000),
        ("DQ2_no_orphan_keys", "Відсутність «сиріт» за всіма 5 FK",
         """SELECT COUNT(*) FROM fact_forest_harvest f
            LEFT JOIN dim_date d ON f.date_sk = d.date_sk
            LEFT JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
            LEFT JOIN dim_location l ON f.location_sk = l.location_sk
            LEFT JOIN dim_actor a ON f.actor_sk = a.actor_sk
            LEFT JOIN dim_permit pm ON f.permit_sk = pm.permit_sk
            WHERE d.date_sk IS NULL OR p.product_sk IS NULL OR l.location_sk IS NULL
               OR a.actor_sk IS NULL OR pm.permit_sk IS NULL""", lambda v: v == 0),
        ("DQ3_not_null_critical", "Відсутність NULL у ключах і мірах",
         """SELECT COUNT(*) FROM fact_forest_harvest
            WHERE fact_id IS NULL OR revenue_uah IS NULL OR cost_uah IS NULL OR ndvi_score IS NULL""",
         lambda v: v == 0),
        ("DQ4_positive_revenue_and_nonneg_qty", "Діапазон: revenue_uah > 0, volume_m3 >= 0, mass_kg >= 0",
         """SELECT COUNT(*) FROM fact_forest_harvest
            WHERE revenue_uah <= 0 OR volume_m3 < 0 OR mass_kg < 0""", lambda v: v == 0),
        ("DQ5_ndvi_range_0_1", "Діапазон екологічної метрики: 0 <= ndvi_score <= 1",
         "SELECT COUNT(*) FROM fact_forest_harvest WHERE ndvi_score < 0 OR ndvi_score > 1",
         lambda v: v == 0),
        ("DQ6_unique_fact_id_and_iri", "Унікальність fact_id та product_iri",
         """SELECT (COUNT(*) - COUNT(DISTINCT fact_id)) +
                   (SELECT COUNT(*) - COUNT(DISTINCT product_iri) FROM dim_product_taxonomy)
            FROM fact_forest_harvest""", lambda v: v == 0),
        ("DQ7_margin_arithmetic", "Узгодженість формули |margin_uah - (revenue_uah - cost_uah)| < 0.02",
         "SELECT COUNT(*) FROM fact_forest_harvest WHERE ABS(margin_uah - (revenue_uah - cost_uah)) >= 0.02",
         lambda v: v == 0),
    ]

    dq_results = []
    for cid, desc, sql, pred in checks:
        val = q_scalar(sql)
        passed = bool(pred(val))
        dq_results.append({"id": cid, "description": desc, "observed": val, "passed": passed})

    con.close()

    # Збереження маніфесту, звіту якості та діаграми зірки
    manifest = {
        "dataset_version": DATASET_VERSION,
        "generated_at": "2026-11-24",
        "seed": SEED,
        "engine_used": db_engine,
        "fact_rows": len(tables["fact_forest_harvest"]),
        "files": manifest_files,
    }
    json.dump(manifest, open(os.path.join(DATA_DIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(dq_results, open(os.path.join(OUT_DIR, "dq_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    md = [
        "# Звіт якості даних (Результат 2 — ELT)",
        f"- **Версія набору даних**: `{DATASET_VERSION}` (`seed={SEED}`, рушій завантаження: `{db_engine}`)",
        f"- **Рядків у `fact_forest_harvest`**: {len(tables['fact_forest_harvest'])} (вимога ≥ 1000)",
        "",
        "| Код перевірки | Опис | Значення | Статус |",
        "|---|---|---:|---|",
    ]
    for r in dq_results:
        md.append(f"| `{r['id']}` | {r['description']} | {r['observed']} | {'PASS' if r['passed'] else 'FAIL'} |")
    md.append("\n## Parquet-файли (`data/*.parquet`)")
    for fn, meta in manifest_files.items():
        md.append(f"- `{fn}`: {meta['rows']} рядків, {meta['cols']} стовпців, SHA-256=`{meta['sha256_16']}`")
    open(os.path.join(DOCS_DIR, "data_quality_report.md"), "w", encoding="utf-8").write("\n".join(md))

    draw_star_schema(os.path.join(DOCS_DIR, "fig_star_schema.png"))

    print(f"ETL completed ({db_engine}): {len(tables['fact_forest_harvest'])} facts, "
          f"{sum(r['passed'] for r in dq_results)}/{len(dq_results)} DQ checks PASSED")
    for r in dq_results:
        print(f"  {r['id']}: {r['observed']} -> {'PASS' if r['passed'] else 'FAIL'}")


if __name__ == "__main__":
    run_etl()
