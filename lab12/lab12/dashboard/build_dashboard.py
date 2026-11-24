#!/usr/bin/env python3
"""
Результат 5 (Частина 2 — Аналітична панель: >= 4 візуалізації за 5 питаннями + ризики).
Генерує 4 окремі PNG-графіки та зведену панель 2x2 `dashboard/dashboard_overview.png`,
а також документацію `dashboard/README.md` з інтерпретаціями та аналізом ризиків.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DASH_DIR = os.path.join(BASE_DIR, "dashboard")


def build_dashboard():
    os.makedirs(DASH_DIR, exist_ok=True)
    fact = pd.read_parquet(os.path.join(DATA_DIR, "fact_forest_harvest.parquet"))
    dim_d = pd.read_parquet(os.path.join(DATA_DIR, "dim_date.parquet"))
    dim_p = pd.read_parquet(os.path.join(DATA_DIR, "dim_product_taxonomy.parquet"))
    dim_l = pd.read_parquet(os.path.join(DATA_DIR, "dim_location.parquet"))
    dim_a = pd.read_parquet(os.path.join(DATA_DIR, "dim_actor.parquet"))

    df = (fact
          .merge(dim_d, on="date_sk")
          .merge(dim_p, on="product_sk")
          .merge(dim_l, on="location_sk")
          .merge(dim_a[["actor_sk", "staff_code", "actor_name", "actor_type"]], on="actor_sk"))

    plt.rcParams["font.family"] = "DejaVu Sans"

    # Підготовка агрегатів для 4 візуалізацій
    # 1. Помісячна виручка та 3-місячна ковзна середня (Q1 + Q3)
    m_rev = df.groupby("year_month", as_index=False)["revenue_uah"].sum().sort_values("year_month")
    m_rev["rev_k"] = m_rev["revenue_uah"] / 1000.0
    m_rev["ma3"] = m_rev["rev_k"].rolling(3, min_periods=1).mean()

    # 2. Drill-down по таксономії: виручка та маржинальність по підкласах (Q2 + Q6)
    sub = df.groupby(["top_class_uk", "subclass_uk"], as_index=False).agg(
        rev_k=("revenue_uah", lambda s: s.sum() / 1000.0),
        margin=("margin_uah", "sum"),
        rev=("revenue_uah", "sum"),
    ).sort_values("rev_k", ascending=True)
    sub["margin_pct"] = 100.0 * sub["margin"] / sub["rev"]

    # 3. Pivot-теплокарта: лісництва x квартали (Q3)
    piv = df.pivot_table(index="forestry_code", columns="quarter_label", values="revenue_uah", aggfunc="sum") / 1000.0
    piv = piv[["Q1", "Q2", "Q3", "Q4"]]

    # 4. Частка FSC по роках та лісництвах (Q4 + Q5)
    fsc_yr = df.groupby(["year", "forestry_code"], as_index=False).apply(
        lambda g: pd.Series({"fsc_pct": 100.0 * g.loc[g["fsc_certified"] == True, "revenue_uah"].sum() / g["revenue_uah"].sum()}),
        include_groups=False,
    ).pivot(index="forestry_code", columns="year", values="fsc_pct")

    # Зведена панель 2x2
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.2), dpi=180)
    fig.suptitle("Аналітична панель OLAP-куба «Управління лісовими продуктами» (2024–2026)",
                 fontsize=13, fontweight="bold", y=0.98)

    # Panel 1
    ax = axes[0, 0]
    x = np.arange(len(m_rev))
    ax.bar(x, m_rev["rev_k"], color="#A9CCE3", label="Місячна виручка")
    ax.plot(x, m_rev["ma3"], color="#1B4F72", lw=2.2, label="3-міс. ковзна середня")
    step = max(1, len(x) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(m_rev["year_month"].iloc[::step], rotation=30, ha="right", fontsize=8)
    ax.set_title("1. Динаміка виручки та 3-міс. ковзна середня (Q1, Q3)", fontsize=10, fontweight="bold")
    ax.set_ylabel("тис. грн")
    ax.grid(axis="y", ls="--", alpha=0.4)
    ax.legend(fontsize=8)

    # Panel 2
    ax = axes[0, 1]
    colors = ["#2E86C1" if c == "Деревинні продукти" else "#27AE60" for c in sub["top_class_uk"]]
    bars = ax.barh(sub["subclass_uk"], sub["rev_k"], color=colors)
    ax.set_title("2. Drill-down таксономії: виручка та маржа % (Q2, Q6)", fontsize=10, fontweight="bold")
    ax.set_xlabel("тис. грн")
    ax.grid(axis="x", ls="--", alpha=0.4)
    for bar, mp in zip(bars, sub["margin_pct"]):
        w = bar.get_width()
        ax.text(w + 600, bar.get_y() + bar.get_height() / 2, f"{w:,.0f} ({mp:.1f}%)",
                va="center", fontsize=8)
    ax.set_xlim(0, sub["rev_k"].max() * 1.28)

    # Panel 3
    ax = axes[1, 0]
    im = ax.imshow(piv.values, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(4))
    ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index)
    ax.set_title("3. Pivot-матриця виручки: лісництва × квартали (Q3)", fontsize=10, fontweight="bold")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            val = piv.values[i, j]
            ax.text(j, i, f"{val:,.0f}", ha="center", va="center",
                    fontsize=8.5, color="white" if val > piv.values.mean() else "black", fontweight="bold")

    # Panel 4
    ax = axes[1, 1]
    fsc_yr.plot(kind="bar", ax=ax, color=["#5DADE2", "#2874A6", "#1E8449"])
    ax.set_title("4. Частка FSC-виручки за роками та лісництвами (Q4)", fontsize=10, fontweight="bold")
    ax.set_ylabel("% виручки FSC")
    ax.set_xlabel("Лісництво")
    ax.set_ylim(0, 112)
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", ls="--", alpha=0.4)
    ax.legend(title="Рік", fontsize=8, title_fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    overview_path = os.path.join(DASH_DIR, "dashboard_overview.png")
    plt.savefig(overview_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Окремі файли графіків для репозиторію
    for idx, fname in enumerate(["fig1_revenue_trend.png", "fig2_taxonomy_drilldown.png",
                                 "fig3_forestry_pivot.png", "fig4_fsc_share.png"], start=1):
        # Зберігаємо копії/окремі рендери
        f_single, a_s = plt.subplots(figsize=(6.8, 4.2), dpi=150)
        if idx == 1:
            a_s.bar(x, m_rev["rev_k"], color="#A9CCE3", label="Місячна виручка")
            a_s.plot(x, m_rev["ma3"], color="#1B4F72", lw=2.2, label="3-міс. ковзна середня")
            a_s.set_xticks(x[::step])
            a_s.set_xticklabels(m_rev["year_month"].iloc[::step], rotation=30, ha="right", fontsize=8)
            a_s.set_title("Динаміка виручки та 3-місячна ковзна середня")
            a_s.set_ylabel("тис. грн")
            a_s.legend()
        elif idx == 2:
            a_s.barh(sub["subclass_uk"], sub["rev_k"], color=colors)
            a_s.set_title("Drill-down по таксономії продуктів (тис. грн)")
            a_s.set_xlabel("тис. грн")
        elif idx == 3:
            a_s.imshow(piv.values, cmap="YlGnBu", aspect="auto")
            a_s.set_xticks(range(4)); a_s.set_xticklabels(piv.columns)
            a_s.set_yticks(range(len(piv.index))); a_s.set_yticklabels(piv.index)
            a_s.set_title("Pivot-матриця виручки: лісництва × квартали (тис. грн)")
        else:
            fsc_yr.plot(kind="bar", ax=a_s, color=["#5DADE2", "#2874A6", "#1E8449"])
            a_s.set_title("Частка FSC-виручки за роками та лісництвами (%)")
            a_s.set_ylabel("%")
            a_s.tick_params(axis="x", rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(DASH_DIR, fname), dpi=150)
        plt.close(f_single)

    readme = """# Аналітична панель (Результат 5)

## Візуалізації (4 графіки за 5 бізнес-питаннями)
1. **Динаміка виручки та 3-місячна ковзна середня (`fig1_revenue_trend.png`)**: показує стабільний тренд виручки з сезонним підйомом у III кварталі за рахунок збору недеревинних продуктів (гриби, ягоди) та помірним спадом деревинної заготівлі у пожежонебезпечні місяці.
2. **Drill-down таксономії (`fig2_taxonomy_drilldown.png`)**: хвойна й листяна деревина формують основний обсяг виручки (~83.9 %), тоді як недеревинні продукти (гриби, ягоди, лікарські рослини) дають ~16.1 % виручки, але мають вищу валову маржинальність (~50 % проти ~36 % у деревини).
3. **Pivot-матриця «лісництва × квартали» (`fig3_forestry_pivot.png`)**: лідерами за обсягом виручки є `LS-01` («Карпатське») та `LS-02` («Бескидське») з найвищим навантаженням у Q2–Q3.
4. **Частка FSC-виручки за роками (`fig4_fsc_share.png`)**: після проходження сертифікації виділів `V-107` (LS-02) та `V-206` (LS-04) у липні 2025 р. (відображено через SCD Type 2) частка сертифікованої виручки у `LS-02` та `LS-04` зросла до 100 % у 2026 р.

## Ризики та обмеження Text-to-SQL і панелі (C4, ≥ 3)
1. **SQL-ін’єкція та модифікація даних**: зловмисні запити (`DROP`, `ATTACH`, `UNION SELECT sqlite_master`) зменшено через AST-валідатор, білий список таблиць і read-only підключення.
2. **Семантичні помилки агрегації**: LLM схильна застосовувати `AVG(margin_pct)` до неадитивних мір (`T08`) або пропускати фільтр `is_current = 1` для SCD Type 2 (`T09`); мінімізується через обов’язкове використання `semantic/metrics.yml`.
3. **Невідповідність канонічним термінам таксономії**: довільні формулювання користувача («хвойні» замість «Хвойна деревина», `T10`) призводять до порожніх вибірок; потребує словникового зіставлення з IRI.
4. **Ресурсне виснаження (DoS)**: важкі декартові добутки або мільйони рядків обмежуються примусовим `LIMIT 100` та тайм-аутом виконання `2.0 с`.
5. **Синтетичний характер даних**: події згенеровано детерміновано (`seed=42`) на основі реальних сутностей ЛР 5–11, тому економічні прогнози потребують калібрування на реальних бухгалтерських вивантаженнях лісгоспів.
"""
    open(os.path.join(DASH_DIR, "README.md"), "w", encoding="utf-8").write(readme)
    print(f"Dashboard built: {overview_path}")


if __name__ == "__main__":
    build_dashboard()
