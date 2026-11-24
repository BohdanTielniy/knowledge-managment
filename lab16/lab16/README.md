# Лабораторна робота 16: Рекомендаційна система та фінальний демонстратор Domain Knowledge Hub

- **Предметна область**: Довкілля — «Управління лісовими продуктами»
- **Студент**: Тєльний Богдан (група ФЕІ-42, ЛНУ ім. Івана Франка)
- **Склад системи**: Рекомендаційний модуль (`reco/`), Агент + MCP (ЛР 15), Очищений граф (ЛР 14), OLAP-куб (ЛР 12), RAG (ЛР 11), Whitepaper (`docs/whitepaper.pdf`).

## Передумови
- Python 3.11+ або Docker + Docker Compose v2.
- Змінні середовища (опційно): `NEO4J_PASSWORD` (дефолт `foresthub_local`), `HUB_ROLE` (`public_user` / `forester` / `auditor`). Ключі API не зберігаються в коді.

## Запуск однією командою
```bash
# Варіант 1 (Docker Compose):
docker compose up --build

# Варіант 2 (локальний запуск з нуля):
pip install -r requirements.txt && bash scripts/run_all.sh
```
Лог підтвердженого запуску «з нуля» зберігається у `outputs/clean_run_log.txt`.
