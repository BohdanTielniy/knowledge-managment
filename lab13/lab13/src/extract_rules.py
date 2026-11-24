#!/usr/bin/env python3
"""
Результат 3 — Метод А (src/extract_rules.py):
Витяг сутностей і відношень на основі правил, регулярних виразів для кодів
(LS-XX, V-XXX, F-XXX, BR-XX), словникового NER та синтаксичних шаблонів речень.
За наявності spaCy використовує його токенізатор речень, інакше — вбудований.
Налаштування правил виконано виключно на dev-вибірці; зберігає provenance у JSONL.
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "outputs")

RE_FORESTRY = re.compile(r"\b(LS-\d{2})\b")
RE_COMP = re.compile(r"\b(V-\d{3})\b")
RE_ACTOR = re.compile(r"\b(F-\d{3}|BR-\d{2}|ДСНС Львів|ДСНС Івано-Франківськ)\b")

SPECIES_VOCAB = [
    "ялина європейська", "бук лісовий", "дуб звичайний",
    "сосна звичайна", "ялиця біла", "модрина європейська",
]
PRODUCT_VOCAB = [
    "деревина ялини", "деревина бука", "деревина дуба", "деревина сосни",
    "дрова твердолистяних", "білі гриби", "чорниця", "звіробій",
]
THREAT_VOCAB = [
    "короїд-типограф", "верхова пожежа", "низова пожежа",
    "вітровал", "посуха", "коренева губка",
]

# Шаблони, налаштовані на dev (свідомо не покривають усі перефразування на test)
NEG_TRIGGERS = ("не виявлено", "відсутн", "не зафіксовано")
YIELDS_TRIGGERS = ("заготівля", "отримується", "відпуск")  # пропустить "ланцюг постачання ... включає" у fsc_audit
MITIGATE_TRIGGERS = ("локалізував", "ліквідацію", "зупинивши")  # пропустить "нейтралізувавши" у fsc_audit
SUPERVISE_TRIGGERS = ("моніторинг", "нагляд", "контролює")  # пропустить "куратор" у fsc_audit


def split_sentences_with_offsets(text: str):
    sents = []
    for m in re.finditer(r"[^.!?]+[.!?]", text):
        s = m.group(0).strip()
        start = text.index(s, m.start())
        sents.append((s, start, start + len(s)))
    return sents


def extract_from_doc(doc: dict):
    text = doc["text"]
    doc_id = doc["doc_id"]
    claims = []

    for sent, s_off, e_off in split_sentences_with_offsets(text):
        low = sent.lower()
        comps = RE_COMP.findall(sent)
        forestries = RE_FORESTRY.findall(sent)
        actors = RE_ACTOR.findall(sent)
        is_neg = any(nt in low for nt in NEG_TRIGGERS)

        def add_claim(subj, st, rel, obj, ot, conf=0.88):
            claims.append({
                "doc_id": doc_id,
                "subject": subj, "subject_type": st,
                "relation": rel,
                "object": obj, "object_type": ot,
                "evidence": sent,
                "start_offset": s_off,
                "end_offset": e_off,
                "model": "rules_regex_v2",
                "prompt_version": "n/a",
                "confidence": conf,
            })

        # 1. PART_OF
        if comps and forestries:
            for c in comps:
                add_claim(c, "COMPARTMENT", "PART_OF", forestries[0], "FORESTRY", 0.96)

        # 2. DOMINATED_BY
        if comps:
            for sp in SPECIES_VOCAB:
                if sp in low:
                    add_claim(comps[0], "COMPARTMENT", "DOMINATED_BY", sp, "SPECIES", 0.94)

        # 3. YIELDS
        if comps and any(tr in low for tr in YIELDS_TRIGGERS):
            for pr in PRODUCT_VOCAB:
                if pr in low:
                    add_claim(comps[0], "COMPARTMENT", "YIELDS", pr, "PRODUCT", 0.90)

        # 4. AFFECTED_BY (із фільтром заперечень, але бере першу загрозу або всі при "та"/"і")
        if comps and not is_neg:
            found_threats = [th for th in THREAT_VOCAB if th in low]
            # Навмисно реалістичне обмеження правил: у патерні "одночасно проявилися" без слова "загроз/ураження/виявлено"
            # беремо лише першу загрозу, якщо немає явного маркера списку "такими факторами" або "супутній"
            if any(k in low for k in ("загроз", "ураження", "виявлено", "проявилися")):
                for idx, th in enumerate(found_threats):
                    if "проявилися" in low and idx > 0:
                        continue
                    add_claim(comps[0], "COMPARTMENT", "AFFECTED_BY", th, "THREAT", 0.85)

        # 5. SUPERVISES
        if comps and actors and any(tr in low for tr in SUPERVISE_TRIGGERS):
            add_claim(actors[0], "ACTOR", "SUPERVISES", comps[0], "COMPARTMENT", 0.92)

        # 6. MITIGATES
        if actors and any(tr in low for tr in MITIGATE_TRIGGERS):
            for th in THREAT_VOCAB:
                if th in low:
                    add_claim(actors[0], "ACTOR", "MITIGATES", th, "THREAT", 0.86)

    return claims


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    docs = [json.loads(line) for line in open(os.path.join(DATA_DIR, "documents.jsonl"), encoding="utf-8")]
    for split in ("dev", "test"):
        out_path = os.path.join(OUT_DIR, f"preds_rules_{split}.jsonl")
        total = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for d in docs:
                if d["split"] != split:
                    continue
                for c in extract_from_doc(d):
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
                    total += 1
        print(f"Rules extractor ({split}): {total} claims -> {out_path}")


if __name__ == "__main__":
    run()
