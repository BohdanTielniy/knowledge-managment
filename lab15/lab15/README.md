# Лабораторна робота 15: LLM-агент з інструментами (MCP / LangGraph) над сховищем знань

- **Предметна область**: Довкілля — «Управління лісовими продуктами» (Domain Knowledge Hub)
- **Студент**: Тєльний Богдан (група ФЕІ-42, ЛНУ ім. Івана Франка)
- **Архітектура**: граф станів `plan → retrieve → draft → verify` + MCP JSON-RPC 2.0 сервер над 3 read-only сховищами (RAG ЛР 11, OLAP ЛР 12, Граф ЛР 14) + HITL `propose_fact`.

## Запуск з нуля
```bash
pip install -r requirements.txt
bash scripts/run_all.sh
```
