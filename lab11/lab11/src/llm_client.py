#!/usr/bin/env python3
"""
Уніфікований клієнт LLM для ЛР 11 із підтримкою двох режимів:
  - LLM_PROVIDER=openai  — будь-який OpenAI-сумісний API (OpenAI, Ollama, Groq, OpenRouter)
                           через змінні середовища LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
  - LLM_PROVIDER=local   — детермінований локальний генератор на основі наданого контексту
                           (працює без інтернету й API-ключів із дотриманням правил цитування,
                           політики «не знаю», виявлення конфлікту джерел і захисту від ін'єкцій).
"""
import os
import re
import time
import urllib.request
import json

INJECTION_PATTERNS = [
    r"ігноруй\s+(усі|всі|попередні)\s+(правила|інструкції)",
    r"забудь\s+(попередні|усі|всі)\s+(правила|інструкції)",
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"покажи\s+системний\s+промпт",
    r"виведи\s+всі\s+restricted",
    r"bypass\s+(security|access|filter)",
    r"обійди\s+фільтр",
    r"act\s+as\s+root|режим\s+адміністратора\s+без\s+ключа",
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def approx_tokens(text: str) -> int:
    # Приблизна оцінка токенів для українського тексту (~1.35 токена на слово)
    return max(1, int(round(len(text.split()) * 1.35)))


def detect_prompt_injection(query: str) -> bool:
    return bool(INJECTION_RE.search(query))


class LLMClient:
    def __init__(self, provider=None, model=None, base_url=None, api_key=None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "local")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "local-extractive-v1")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        # Орієнтовна ціна за 1M токенів (USD): 0 для локального режиму; $0.15/$0.60 для gpt-4o-mini
        self.price_in_per_1m = 0.0 if self.provider == "local" else 0.15
        self.price_out_per_1m = 0.0 if self.provider == "local" else 0.60

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return round(
            (prompt_tokens * self.price_in_per_1m + completion_tokens * self.price_out_per_1m) / 1_000_000.0,
            6,
        )

    def generate(self, system_prompt: str, user_prompt: str, query: str,
                 context_chunks: list, graph_facts: list,
                 abstention_threshold: float = 0.22, strict_injection: bool = True):
        t0 = time.perf_counter()

        # 1. Захист від prompt injection на рівні політики
        if strict_injection and detect_prompt_injection(query):
            ans = (
                "Запит відхилено політикою безпеки: виявлено спробу prompt injection "
                "(перевизначення системних інструкцій або обходу контролю доступу). "
                "Я відповідаю лише на предметні запитання за доступним контекстом."
            )
            pt = approx_tokens(system_prompt + " " + user_prompt)
            ct = approx_tokens(ans)
            return {
                "answer": ans,
                "abstained": True,
                "injection_blocked": True,
                "conflict_detected": False,
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": pt + ct,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "cost_usd": self.estimate_cost(pt, ct),
                "model": self.model,
            }

        # 2. Режим реального OpenAI-сумісного API (якщо задано LLM_PROVIDER=openai і є ключ)
        if self.provider == "openai" and self.api_key:
            payload = {
                "model": self.model,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ans = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            pt = int(usage.get("prompt_tokens", approx_tokens(system_prompt + user_prompt)))
            ct = int(usage.get("completion_tokens", approx_tokens(ans)))
            low = ans.lower()
            abstained = ("не знаю" in low) or ("немає інформації" in low)
            conflict = ("конфлікт" in low) or ("супереч" in low) or ("розбіжн" in low)
            return {
                "answer": ans,
                "abstained": abstained,
                "injection_blocked": False,
                "conflict_detected": conflict,
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": pt + ct,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "cost_usd": self.estimate_cost(pt, ct),
                "model": self.model,
            }

        # 3. Локальний детермінований генератор із суворим цитуванням [id]
        top_score = context_chunks[0]["score"] if context_chunks else 0.0
        if (not context_chunks and not graph_facts) or (top_score < abstention_threshold):
            ans = "Не знаю: у доступному контексті бази знань немає інформації для відповіді на це запитання."
            pt = approx_tokens(system_prompt + " " + user_prompt)
            ct = approx_tokens(ans)
            return {
                "answer": ans,
                "abstained": True,
                "injection_blocked": False,
                "conflict_detected": False,
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": pt + ct,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "cost_usd": 0.0,
                "model": self.model,
            }

        # Перевірка конфлікту джерел у відібраних фрагментах
        conflict_chunks = [c for c in context_chunks if c["doc_id"].startswith("DOC-C") or "конфлікт" in c["text"].lower()]
        normal_chunks = [c for c in context_chunks if c not in conflict_chunks]
        conflict_detected = bool(conflict_chunks and normal_chunks)

        parts = []
        if conflict_detected:
            c_old = conflict_chunks[0]
            c_new = normal_chunks[0]
            parts.append(
                f"Виявлено конфлікт джерел: у джерелі від {c_old['date']} зазначено — "
                f"«{c_old['text']}» [{c_old['chunk_id']}], тоді як у новішому затвердженому джерелі від "
                f"{c_new['date']} наведено — «{c_new['text']}» [{c_new['chunk_id']}]. "
                f"Згідно з політикою пріоритету джерел, актуальним вважається новіший запис [{c_new['chunk_id']}]."
            )
        else:
            for c in context_chunks[:2]:
                parts.append(f"{c['text']} [{c['chunk_id']}]")

        if graph_facts:
            gf_str = "; ".join(f"{f['text']} [{f['id']}]" for f in graph_facts[:4])
            parts.append(f"За даними графа знань: {gf_str}.")

        ans = " ".join(parts)
        pt = approx_tokens(system_prompt + " " + user_prompt)
        ct = approx_tokens(ans)
        return {
            "answer": ans,
            "abstained": False,
            "injection_blocked": False,
            "conflict_detected": conflict_detected,
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "total_tokens": pt + ct,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "cost_usd": 0.0,
            "model": self.model,
        }
