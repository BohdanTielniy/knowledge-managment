# Результат 4. Семантичний шар (`semantic/metrics.yml`)
- Версія: `1.0.0`, кількість затверджених метрик: **6** (вимога ≥ 5).

| Метрика | Тип | Одиниця | Значення (усі роки) | Власник | Дата перегляду | Статус |
|---|---|---|---:|---|---|---|
| `total_revenue_uah` | additive | грн | 109226686.7 | Фінансово-аналітичний відділ ЛГ | 2026-11-24 | approved |
| `timber_volume_m3` | additive | м³ | 23951.98 | Відділ лісокористування | 2026-11-24 | approved |
| `gross_margin_pct` | non_additive | % | 38.52 | Фінансово-аналітичний відділ ЛГ | 2026-11-24 | approved |
| `fsc_certified_share_pct` | non_additive | % | 80.45 | Служба екологічної сертифікації | 2026-11-24 | approved |
| `nontimber_revenue_share_pct` | non_additive | % | 16.1 | Відділ побічного лісокористування | 2026-11-24 | approved |
| `avg_ndvi_health` | non_additive | індекс (0..1) | 0.698 | Служба екологічного моніторингу | 2026-11-24 | approved |

## Перевірка узгодженості (C3)
1. **Рентабельність (`gross_margin_pct`) по лісництвах за 2025 р.** (Semantic SQL vs pandas): макс. розбіжність = **0.0000 п.п.** (`CONSISTENT`).
2. **Частка FSC-виручки (`fsc_certified_share_pct`) за роками** (Semantic SQL vs pandas): макс. розбіжність = **0.0000 п.п.** (`CONSISTENT`).