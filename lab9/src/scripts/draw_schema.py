#!/usr/bin/env python3
"""Малює docs/graph_schema.png — схему LPG (мітки, типи зв'язків, ключові властивості)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "graph_schema.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

W, H = 3.1, 1.55  # розмір рамки вузла
NODES = {  # мітка: (x, y, колір, підмітки, ключові властивості)
    "Forestry": (2.0, 9.0, "#e1f0f5", "", "id, unitCode, name, areaHectares"),
    "Compartment": (8.6, 9.0, "#e1f0f5", "", "id, unitCode, areaHectares, standAgeYears,\ndamagedTreesShare, ndviValue"),
    "TreeSpecies": (15.2, 9.0, "#e3f1df", ":ConiferousSpecies | :DeciduousSpecies", "id, name, latinName"),
    "Threat": (2.0, 5.2, "#fbe3d6", ":InsectPest | :ForestDisease\n:Drought | :Windthrow", "id, name, kind, detectedOn"),
    "Process": (8.6, 5.2, "#e3f1df", ":TimberHarvesting (:SanitaryFelling | :MainFelling)\n:Reforestation | :FirePreventionMeasure",
                "id, name, plannedDate, harvestVolumeM3,\nplantedSeedlingsCount"),
    "ForestProduct": (15.2, 5.2, "#e3f1df", ":TimberProduct | :NonTimberProduct", "id, name, category"),
    "MeteoObservation": (2.0, 1.2, "#fbe3d6", "", "id, observationDate, airTemperatureC,\nairHumidityPercent, daysWithoutRain"),
    "Actor": (6.0, 1.2, "#fff0c9", ":Forester | :ChiefForester\n:HarvestBrigade | :EmergencyService", "id, name, staffCode"),
    "Permit": (10.6, 1.2, "#ececec", ":FellingTicket", "id, number, issuedOn"),
    "Quota": (15.2, 1.2, "#ececec", ":HarvestQuota | :NonTimberCollectionLimit", "id, name, limitValue, unit"),
}
fig, ax = plt.subplots(figsize=(19, 12))
ax.set_xlim(-0.5, 17.8)
ax.set_ylim(-0.4, 10.6)
ax.axis("off")
ax.set_title("Графова схема (LPG): управління лісовими продуктами. Усі зв'язки мають властивості "
             "source, confidence, validFrom", fontsize=15, pad=8)


def box(label):
    x, y, col, sub, props = NODES[label]
    ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.05,rounding_size=0.15",
                                fc=col, ec="#2d4a3e", lw=1.6, zorder=2))
    ax.text(x, y + 0.48, f":{label}", ha="center", va="center", fontsize=13, fontweight="bold", zorder=3)
    yy = y + 0.16
    if sub:
        ax.text(x, yy, sub, ha="center", va="top", fontsize=7.0, color="#7a2b20", zorder=3)
    ax.text(x, y - H / 2 + 0.08, props, ha="center", va="bottom", fontsize=7.3, color="#333", zorder=3)


for k in NODES:
    box(k)


def edge(a, b, label, rad=0.0, off=(0, 0), pa=None, pb=None, color="#2d4a3e", lx=None, ly=None):
    xa, ya = NODES[a][:2]
    xb, yb = NODES[b][:2]
    xa, ya = (pa if pa else (xa, ya))
    xb, yb = (pb if pb else (xb, yb))
    ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), connectionstyle=f"arc3,rad={rad}",
                                 arrowstyle="-|>", mutation_scale=16, lw=1.5, color=color,
                                 shrinkA=0, shrinkB=0, zorder=1))
    mx = (xa + xb) / 2 + off[0] if lx is None else lx
    my = (ya + yb) / 2 + off[1] if ly is None else ly
    ax.text(mx, my, label, ha="center", va="center", fontsize=8.6, color="#8a1c1c", zorder=4,
            bbox=dict(fc="white", ec="none", pad=1.2, alpha=0.95))


# Головні зв'язки
edge("Compartment", "Forestry", "PART_OF_FORESTRY", pa=(8.6 - W / 2, 9.0), pb=(2.0 + W / 2, 9.0))
edge("Compartment", "TreeSpecies", "HAS_DOMINANT_SPECIES", pa=(8.6 + W / 2, 9.0), pb=(15.2 - W / 2, 9.0))
edge("Compartment", "ForestProduct", "YIELDS_PRODUCT", pa=(8.6 + 1.2, 9.0 - H / 2), pb=(15.2 - 1.2, 5.2 + H / 2),
     lx=12.6, ly=7.15)
edge("Compartment", "Threat", "AFFECTED_BY", pa=(8.6 - 1.2, 9.0 - H / 2), pb=(2.0 + 1.2, 5.2 + H / 2),
     lx=4.6, ly=7.15)
edge("Process", "Compartment", "APPLIED_TO", pa=(8.6, 5.2 + H / 2), pb=(8.6, 9.0 - H / 2))
edge("Threat", "Process", "TRIGGERS", pa=(2.0 + W / 2, 5.2), pb=(8.6 - W / 2, 5.2))
edge("MeteoObservation", "Process", "TRIGGERS", pa=(2.0 + 1.0, 1.2 + H / 2), pb=(8.6 - 1.2, 5.2 - H / 2),
     lx=4.0, ly=2.52)
edge("Process", "Permit", "REQUIRES_PERMIT", pa=(8.6 + 0.8, 5.2 - H / 2), pb=(10.6 - 0.3, 1.2 + H / 2),
     lx=10.1, ly=3.2)
edge("Process", "Quota", "CONSTRAINED_BY", pa=(8.6 + 1.3, 5.2 - H / 2), pb=(15.2 - 0.8, 1.2 + H / 2),
     lx=13.0, ly=3.4)
edge("Process", "Actor", "PERFORMED_BY", pa=(8.6 - 1.0, 5.2 - H / 2), pb=(6.0 + 0.9, 1.2 + H / 2),
     lx=7.0, ly=3.05)
edge("ForestProduct", "Quota", "LIMITED_BY", pa=(15.2, 5.2 - H / 2), pb=(15.2, 1.2 + H / 2))
edge("MeteoObservation", "Forestry", "MONITORS_UNIT", rad=-0.18, pa=(2.0 - W / 2, 1.2 + 0.3),
     pb=(2.0 - W / 2, 9.0 - 0.3), lx=-0.0, ly=5.2)
edge("Actor", "Compartment", "SUPERVISES\n(→ Compartment, → Forestry)", rad=-0.35,
     pa=(6.0 - 0.6, 1.2 + H / 2), pb=(8.6 - 1.45, 9.0 - 0.4), lx=4.9, ly=6.2)

# Зв'язки Process -> Actor (NOTIFIES) та Process -> Process (FOLLOWED_BY)
ax.annotate("", xy=(6.0 + 1.35, 1.2 + H / 2), xytext=(8.6 - 0.1, 5.2 - H / 2),
            arrowprops=dict(arrowstyle="-|>", color="#2d4a3e", lw=1.5, connectionstyle="arc3,rad=0.12"))
ax.text(8.75, 2.45, "NOTIFIES\n(патруль → ДСНС)", ha="center", va="center", fontsize=8.6, color="#8a1c1c",
        bbox=dict(fc="white", ec="none", pad=1.2, alpha=0.95), zorder=4)
ax.add_patch(FancyArrowPatch((8.6 + 1.0, 5.2 + H / 2), (8.6 + 1.55, 5.2 + 0.25),
                             connectionstyle="arc3,rad=-1.6", arrowstyle="-|>", mutation_scale=16,
                             lw=1.5, color="#2d4a3e", zorder=1))
ax.text(11.5, 6.55, "FOLLOWED_BY\n(рубка → лісовідновлення)", ha="center", va="center", fontsize=8.6,
        color="#8a1c1c", bbox=dict(fc="white", ec="none", pad=1.2, alpha=0.95), zorder=4)

ax.text(-0.3, -0.3, "Червоні підписи — типи зв'язків (14). Червоні мітки в рамках — додаткові мітки "
        "(підкласи онтології). Чорний рядок — ключові властивості вузла.",
        fontsize=9, color="#555")
fig.savefig(OUT, dpi=140, bbox_inches="tight", facecolor="white")
print("saved", OUT)
