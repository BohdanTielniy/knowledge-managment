#!/usr/bin/env python3
"""
Автоматична верифікація REST API (Результат 3, C1–C4):
  - GET /health (200)
  - POST /ask для 2 ролей (public_user vs forester_admin) — перевірка ізоляції restricted
  - GET /sources/{id}: 200 (public), 403 (public -> restricted), 200 (admin -> restricted), 404 (missing)
  - Коди помилок: 401 (без ключа), 422 (невалідний Pydantic-запит), 429 (rate limit)
  - Експорт OpenAPI-схеми у docs/openapi.json
"""
import json
import os
import sys
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from api.main import app, _rate_buckets, RATE_LIMIT_PER_MIN

client = TestClient(app)


def main():
    _rate_buckets.clear()
    results = []

    # 1. GET /health
    r = client.get("/health")
    assert r.status_code == 200
    results.append({"test": "GET /health", "status": r.status_code, "body": r.json()})

    # 2. 401 без ключа
    r = client.post("/ask", json={"question": "Яка площа LS-01?"})
    assert r.status_code == 401
    results.append({"test": "POST /ask without API key -> 401", "status": r.status_code})

    # 3. 422 невалідний вхід (занадто коротке питання)
    r = client.post("/ask", headers={"X-API-Key": "demo-public-key"}, json={"question": "a"})
    assert r.status_code == 422
    results.append({"test": "POST /ask invalid Pydantic -> 422", "status": r.status_code})

    # 4. POST /ask як public_user (restricted-джерела мають бути відфільтровані)
    r_pub = client.post(
        "/ask",
        headers={"X-API-Key": "demo-public-key"},
        json={"question": "Акт внутрішнього аудиту перевищення квоти V-102 та гніздування чорного лелеки"},
    )
    assert r_pub.status_code == 200
    pub_sens = {s["sensitivity"] for s in r_pub.json()["sources"]}
    assert pub_sens <= {"public"}, f"Витік непублічних джерел: {pub_sens}"
    results.append({"test": "POST /ask (public_user)", "status": 200, "sensitivities": sorted(pub_sens),
                    "citations_valid": r_pub.json()["citations_valid"]})

    # 5. POST /ask як forester_admin (має доступ до restricted DOC-11)
    r_adm = client.post(
        "/ask",
        headers={"X-API-Key": "demo-admin-key"},
        json={"question": "Яке перевищення квоти та призупинення квитка ЛК-2026-047 виявлено на V-102?"},
    )
    assert r_adm.status_code == 200
    adm_sens = {s["sensitivity"] for s in r_adm.json()["sources"]}
    assert "restricted" in adm_sens, f"Адмін не отримав restricted: {adm_sens}"
    results.append({"test": "POST /ask (forester_admin)", "status": 200, "sensitivities": sorted(adm_sens),
                    "citations": r_adm.json()["citations"][:4]})

    # 6. GET /sources/{id}: 403 для public на restricted, 200 для admin, 404 для неіснуючого
    r403 = client.get("/sources/DOC-11_C01", headers={"X-API-Key": "demo-public-key"})
    assert r403.status_code == 403
    r200 = client.get("/sources/DOC-11_C01", headers={"X-API-Key": "demo-admin-key"})
    assert r200.status_code == 200
    r404 = client.get("/sources/NON_EXISTENT_ID", headers={"X-API-Key": "demo-admin-key"})
    assert r404.status_code == 404
    results.append({"test": "GET /sources access control", "public_to_restricted": r403.status_code,
                    "admin_to_restricted": r200.status_code, "missing_id": r404.status_code})

    # 7. Rate limit -> 429
    _rate_buckets.clear()
    statuses = []
    for _ in range(RATE_LIMIT_PER_MIN + 1):
        resp = client.get("/sources/DOC-05_C01", headers={"X-API-Key": "demo-public-key"})
        statuses.append(resp.status_code)
    assert statuses[-1] == 429, f"Очікувався 429, отримано {statuses}"
    results.append({"test": f"Rate limit ({RATE_LIMIT_PER_MIN}/min) -> 429", "last_status": statuses[-1]})

    # 8. Експорт OpenAPI
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    with open(os.path.join(ROOT, "docs", "openapi.json"), "w", encoding="utf-8") as fh:
        json.dump(app.openapi(), fh, ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT, "outputs", "api_test_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    print("УСІ API-ТЕСТИ ПРОЙДЕНО УСПІШНО!")
    for item in results:
        print(" ", item)


if __name__ == "__main__":
    main()
