# Результат 3. Пояснення рекомендацій зі шляху графа та холодний старт
- **Частка коректних пояснень (автоперевірка C2)**: **100.0 %** (5/5; контрольна галюцинація із зайвими сутностями відхилена = `True`).

## 5 прикладів пояснень зі шляху графа (C1)
- `ITEM-06` | Шлях: `U-001 -> LS-02 -> Species_PinusSylvestris -> Threat_CrownFire -> ITEM-06` | Рекомендовано ITEM-06 («Протипожежний моніторинг та протоколи ДСНС (LS-02)») для U-001, оскільки воно пов’язане у графі знань через вузли [LS-02, Species_PinusSylvestris, Threat_CrownFire].
- `ITEM-07` | Шлях: `U-001 -> LS-03 -> Species_PinusSylvestris -> Threat_CrownFire -> ITEM-07` | Рекомендовано ITEM-07 («Протипожежний моніторинг та протоколи ДСНС (LS-03)») для U-001, оскільки воно пов’язане у графі знань через вузли [LS-03, Species_PinusSylvestris, Threat_CrownFire].
- `ITEM-28` | Шлях: `U-001 -> LS-02 -> Species_FagusSylvatica -> Threat_RootRot -> ITEM-28` | Рекомендовано ITEM-28 («Новий звіт FSC-2026 (cold-start item)») для U-001, оскільки воно пов’язане у графі знань через вузли [LS-02, Species_FagusSylvatica, Threat_RootRot].
- `ITEM-10` | Шлях: `U-001 -> LS-02 -> Species_FagusSylvatica -> Threat_RootRot -> ITEM-10` | Рекомендовано ITEM-10 («Сертифікація FSC та букові деревостани (LS-02)») для U-001, оскільки воно пов’язане у графі знань через вузли [LS-02, Species_FagusSylvatica, Threat_RootRot].
- `ITEM-09` | Шлях: `U-001 -> LS-01 -> Species_FagusSylvatica -> Threat_RootRot -> ITEM-09` | Рекомендовано ITEM-09 («Сертифікація FSC та букові деревостани (LS-01)») для U-001, оскільки воно пов’язане у графі знань через вузли [LS-01, Species_FagusSylvatica, Threat_RootRot].

## 2 сценарії холодного старту та метрики (C3–C4)
1. **Новий користувач (`U-NEW`, 0 кліків)**: використання онтологічного профілю (лісництво `LS-02`, тема `beech_fsc`) + гібрид RRF дає **Precision@5 = 1.00** (топ-5: `ITEM-10, ITEM-28, ITEM-12, ITEM-06, ITEM-18`).
2. **Новий документ (`ITEM-28`, 0 взаємодій у train)**: завдяки content-based embeddings та зв’язку в графі (`LS-02`, `Species_FagusSylvatica`) документ потрапив у топ-5 для **13/25 (52.0 %)** релевантних користувачів (проти 0 % у популярнісного baseline).