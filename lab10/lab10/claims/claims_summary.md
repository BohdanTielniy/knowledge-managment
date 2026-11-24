# Підсумок верифікації тверджень (Протокол «LLM-експерт», ЛР 10)

| Показник | Значення |
|----------|----------|
| Усього тверджень | 11 (`C001`–`C011`) |
| Підтверджено (`verified`) | **8** (**72.7 %** від усіх, **80.0 %** від перевірених) |
| Відхилено (`rejected`) | **2** (`C010`, `C011` — **18.2 %**) |
| Очікує локального запуску `--backend neural` (`pending`) | **1** (`C009` — **9.1 %**) |

## Відхилені твердження (з поясненням)
1. **`C010` (рівень V4, `rejected`):** гіпотеза про безумовну перевагу чистого RRF над Dense та придатність RRF-скорів для відсікання `no-answer`. Експериментально спростовано на запиті `G22` (де BM25 не знайшов перефразований запит, опустивши `DOC-09` поза топ-10 у RRF) та на 6 запитах без відповіді (рангові скори RRF мають фіксований максимум ~0.0328, тому відсікання потребує reranker або dense-порогу).
2. **`C011` (рівень V3, `rejected`):** кандидат синтетичного питання від LLM щодо середньої висоти бука по 4 лісництвах відхилено під час ручної перевірки V3, оскільки відповідного числового факту в `DOC-14` немає.

## Перелік джерел
1. Лекція 10 «Векторні представлення знань і семантичний пошук», ЛНУ ім. Івана Франка, 2026–2027 н. р.
2. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019.
3. Malkov, Y. A., & Yashunin, D. A. (2020). *Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs*. IEEE TPAMI, 42(4), 824–836.
4. Johnson, J., Douze, M., & Jégou, H. (2021). *Billion-Scale Similarity Search with GPUs* (FAISS). IEEE Transactions on Big Data, 7(3), 535–547.
5. Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*. SIGIR 2009.
6. Внутрішні артефакти проєкту Domain Knowledge Hub (ЛР 6–9, «Управління лісовими продуктами»).
