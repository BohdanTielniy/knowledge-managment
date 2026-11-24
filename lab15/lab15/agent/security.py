#!/usr/bin/env python3
"""
Модуль безпеки агента (agent/security.py):
- Захист від прямих і непрямих prompt injection (ізоляція контексту <untrusted_data>).
- Перевірка read-only та заборона DML/DDL/Cypher-мутацій.
- Перевірка RBAC (заборона витоку персональних/внутрішніх даних).
- Валідація описів інструментів проти tool poisoning.
- Контроль лімітів (max_steps, max_tokens).
"""
import re

MAX_STEPS = 5
MAX_TOKENS = 3000

DIRECT_INJECTION_PATTERNS = [
    r"ігноруй\s+попередні", r"ignore\s+previous", r"system\s+prompt",
    r"уяви,\s+що\s+ти\s+аудит-скрипт", r"без\s+обмежень", r"jailbreak",
    r"виведи\s+персональні\s+дані", r"api[_\s-]?key", r"пароль",
]

INDIRECT_INJECTION_PATTERNS = [
    r"\[system\s*override\]", r"ignore\s+all\s+rules", r"exfiltrate",
    r"негайно\s+видали", r"перешли\s+всі\s+дані", r"disregard\s+instructions",
]

WRITE_MUTATION_PATTERNS = [
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|ATTACH|PRAGMA)\b",
    r"\b(DETACH\s+DELETE|REMOVE\s+|MERGE\s+\()\b",
]

PII_LEAK_PATTERNS = [
    r"персональні\s+дані", r"паспорт", r"телефон\s+порушник", r"зарплат",
    r"конфіденційн\w+\s+список", r"чужі\s+дані",
]


def check_direct_injection(query: str):
    low = query.lower()
    for pat in DIRECT_INJECTION_PATTERNS:
        if re.search(pat, low):
            return False, f"Заблоковано прямий prompt injection ({pat})"
    return True, "OK"


def check_write_attempt(text: str):
    for pat in WRITE_MUTATION_PATTERNS:
        if re.search(pat, text, flags=re.I):
            return False, f"Заборонена спроба запису/видалення (read-only policy: {pat})"
    return True, "OK"


def check_pii_leak(query: str, role: str):
    low = query.lower()
    if role == "public_user":
        for pat in PII_LEAK_PATTERNS:
            if re.search(pat, low):
                return False, f"Заблоковано витік чужих/PII даних для ролі {role}"
    return True, "OK"


def sanitize_untrusted_context(doc_text: str):
    """Ізоляція контексту: виявляє й нейтралізує непрямий prompt injection у документах."""
    low = doc_text.lower()
    for pat in INDIRECT_INJECTION_PATTERNS:
        if re.search(pat, low):
            return False, f"Виявлено непрямий prompt injection у документі ({pat})"
    return True, f"<untrusted_data>{doc_text}</untrusted_data>"


def validate_tool_descriptor(desc: str):
    """Захист від tool poisoning (шкідливих інструкцій в описі MCP-інструмента)."""
    low = desc.lower()
    for pat in INDIRECT_INJECTION_PATTERNS + DIRECT_INJECTION_PATTERNS:
        if re.search(pat, low):
            return False, f"Заблоковано шкідливий опис інструмента (tool poisoning: {pat})"
    return True, "OK"
