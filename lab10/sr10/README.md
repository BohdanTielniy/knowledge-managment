# СР 10. Експеримент з embeddings (3 моделі × 30 запитів)

Порівняння трьох моделей `sentence-transformers` у `FAISS IndexHNSWFlat (M=32, efSearch=64)` на корпусі ПдО «Управління лісовими продуктами» (213 фрагментів, 30 золотих запитів):
1. `sentence-transformers/all-MiniLM-L6-v2` (англомовна, 384d)
2. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (мультимовна, 384d)
3. `intfloat/multilingual-e5-small` (мультимовна асиметрична, 384d)

## Запуск у Docker (2 команди)
```bash
cd sr10
docker compose build
docker compose run --rm sr10
```
Результати зберігаються в `outputs/sr10_results.json`, `outputs/sr10_summary.txt` та `outputs/fig_sr10_embeddings.png`.
