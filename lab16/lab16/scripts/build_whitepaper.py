#!/usr/bin/env python3
"""
Результат 5 (Whitepaper: docs/whitepaper.pdf, обсяг 8–12 сторінок):
Технічна записка проєкту Domain Knowledge Hub («Управління лісовими продуктами»)
із реальними результатами ЛР 9–16, 5 реальними рисунками, 3 таблицями,
оцінкою ризиків за EU AI Act і NIST AI RMF 1.0, економікою, розділом ШІ,
10 джерелами літератури та Додатком А (Топ-20 тверджень із claims/claims.csv).
"""
import csv
import os
import shutil
import subprocess
import tempfile
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
import pypdfium2 as pdfium

BLACK = RGBColor(0x00, 0x00, 0x00)
FONT_MAIN = "Times New Roman"

WORK = "/working_dir/c_e29ea41a69b8cab6"
LAB16 = os.path.join(WORK, "work_lab16", "lab16")
MID_DIR = os.path.join(WORK, "artifacts", "file_generation", "ttl=63d", "intermediate")
OUT_DIR = os.path.join(WORK, "artifacts", "file_generation", "ttl=63d", "output")
WP_DOCX = os.path.join(MID_DIR, "whitepaper.docx")
WP_PDF_REPO = os.path.join(LAB16, "docs", "whitepaper.pdf")
WP_PDF_OUT = os.path.join(OUT_DIR, "Whitepaper_Domain_Knowledge_Hub_Тєльний_ФЕІ-42.pdf")


def set_run_font(run, name=FONT_MAIN, size_pt=12, bold=False, italic=False):
    run.font.name = name; run.font.size = Pt(size_pt)
    run.font.bold = bold; run.font.italic = italic; run.font.color.rgb = BLACK
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), name); rFonts.set(qn("w:hAnsi"), name); rFonts.set(qn("w:cs"), name)


def add_p(doc, text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=12, bold=False, italic=False,
          space_before=0, space_after=4, line_spacing=1.15, keep_with_next=False):
    p = doc.add_paragraph(); p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before); pf.space_after = Pt(space_after)
    pf.line_spacing = line_spacing; pf.keep_with_next = keep_with_next
    if text:
        r = p.add_run(text); set_run_font(r, FONT_MAIN, size, bold=bold, italic=italic)
    return p


def add_h1(doc, text):
    p = add_p(doc, text, align=WD_ALIGN_PARAGRAPH.LEFT, size=13, bold=True,
              space_before=9, space_after=3, keep_with_next=True)
    ol = OxmlElement("w:outlineLvl"); ol.set(qn("w:val"), "0")
    p._p.get_or_add_pPr().append(ol)
    return p


def add_table(doc, headers, rows, col_widths, font_size=9.5, center_cols=None):
    center_cols = set(center_cols or [])
    tbl = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER; tbl.autofit = False
    tbl._tbl.tblPr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '</w:tblBorders>'
    ))

    def style_cell(cell, text, width_in, is_header=False, align=WD_ALIGN_PARAGRAPH.LEFT):
        cell.width = Inches(width_in); cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{int(width_in * 1440)}" w:type="dxa"/>'))
        tcPr.append(parse_xml(
            f'<w:tcMar {nsdecls("w")}>'
            '<w:top w:w="28" w:type="dxa"/><w:bottom w:w="28" w:type="dxa"/>'
            '<w:left w:w="48" w:type="dxa"/><w:right w:w="48" w:type="dxa"/>'
            '</w:tcMar>'
        ))
        if is_header:
            tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="EFEFEF"/>'))
        p = cell.paragraphs[0]; p.alignment = align
        p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.03
        if is_header:
            p.paragraph_format.keep_with_next = True
        r = p.add_run(str(text)); set_run_font(r, FONT_MAIN, font_size, bold=is_header)

    hdr_trPr = tbl.rows[0]._tr.get_or_add_trPr()
    hdr_trPr.append(OxmlElement("w:tblHeader")); hdr_trPr.append(OxmlElement("w:cantSplit"))
    for j, h in enumerate(headers):
        style_cell(tbl.rows[0].cells[j], h, col_widths[j], is_header=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for i, row in enumerate(rows):
        trPr = tbl.rows[i + 1]._tr.get_or_add_trPr(); trPr.append(OxmlElement("w:cantSplit"))
        for j, val in enumerate(row):
            al = WD_ALIGN_PARAGRAPH.CENTER if j in center_cols else WD_ALIGN_PARAGRAPH.LEFT
            style_cell(tbl.rows[i + 1].cells[j], val, col_widths[j], is_header=False, align=al)
    sp = doc.add_paragraph(); sp.paragraph_format.space_before = Pt(0); sp.paragraph_format.space_after = Pt(3)


def add_fig(doc, path, caption, width_in=5.8):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3); p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Inches(width_in))
    add_p(doc, caption, align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5, italic=True, space_after=5)


def add_page_number_footer(section):
    section.different_first_page_header_footer = True
    p = section.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts"); rFonts.set(qn("w:ascii"), FONT_MAIN); rFonts.set(qn("w:hAnsi"), FONT_MAIN)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "22")
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000")
    rPr.append(rFonts); rPr.append(sz); rPr.append(color)
    r.append(rPr); fld.append(r); p._p.append(fld)


def build():
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.27); sec.page_height = Inches(11.69)
    sec.top_margin = Inches(0.8); sec.bottom_margin = Inches(0.8)
    sec.left_margin = Inches(0.95); sec.right_margin = Inches(0.82)
    normal = doc.styles["Normal"]; normal.font.name = FONT_MAIN; normal.font.size = Pt(12); normal.font.color.rgb = BLACK
    add_page_number_footer(sec)

    # СТАНДАРТНА ТИТУЛЬНА СТОРІНКА ЛНУ
    for line in [
        "Міністерство освіти і науки України",
        "Львівський національний університет імені Івана Франка",
        "Факультет електроніки та комп’ютерних технологій",
        "Кафедра системного проектування",
    ]:
        add_p(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=2)
    add_p(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_before=65, space_after=0)
    add_p(doc, "Технічна записка (Whitepaper)", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=2)
    add_p(doc, "з курсу «Сховища знань та управління знаннями»", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=14)
    add_p(doc, "«Domain Knowledge Hub: Гібридна система управління знаннями для сталого лісокористування»",
          align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=55)
    for line in ["Виконав:", "Студент групи ФЕІ-42", "Тєльний Богдан"]:
        add_p(doc, line, align=WD_ALIGN_PARAGRAPH.RIGHT, size=14, space_after=2)
    add_p(doc, "", align=WD_ALIGN_PARAGRAPH.RIGHT, size=14, space_before=12, space_after=0)
    for line in ["Перевірив:", "ас. Патинко А.М."]:
        add_p(doc, line, align=WD_ALIGN_PARAGRAPH.RIGHT, size=14, space_after=2)
    add_p(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_before=65, space_after=0)
    add_p(doc, "Львів 2026", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=0)
    doc.add_page_break()
    add_p(
        doc,
        "Анотація. У цій технічній записці описано архітектуру, методи інженерії знань, результати експериментальної "
        "верифікації (ЛР 9–16), оцінку ризиків за EU AI Act та NIST AI RMF 1.0 і економічну модель експлуатації "
        "гібридної платформи Domain Knowledge Hub. Система об’єднує граф знань (Neo4j / RDF), векторно-лексичний "
        "пошук (FAISS / multilingual-e5-small), OLAP-куб із семантичним шаром (DuckDB / Parquet), конвеєр витягу "
        "знань із текстів, автоматичний CI-контроль якості (12 перевірок), LLM-агента з MCP-інструментами та "
        "пояснювану рекомендаційну систему. У результаті очищення бази знань досягнуто 100 % за 8 вимірами якості, "
        "Faithfulness RAG зріс до 0.969, блокування атак Red Teaming склало 100 % (8/8), а пояснюваність рекомендацій "
        "зі шляху графа — 100 %.",
        size=11.5, space_after=0
    )
    doc.add_page_break()

    # РОЗДІЛ 1
    add_h1(doc, "1. Індустріальна проблема та цільові користувачі")
    add_p(
        doc,
        "Сучасне лісове господарство Карпатського регіону стикається з фрагментацією даних між таксаційними "
        "описами виділів, наказами про лісозаготівлю, актами лісопатологічного моніторингу, метеоспостереженнями "
        "та вимогами міжнародної сертифікації FSC. На практиці це спричиняє три критичні проблеми: (1) суперечності "
        "між паперовими й електронними квотами (наприклад, розбіжність квот на виділі V-102: 720 м³ проти 620 м³ при "
        "річному прирості 555 м³); (2) затримку виявлення комплексних загроз (посуха + короїд-типограф на ялині); "
        "(3) неможливість швидко перевірити походження аналітичних показників під час екологічного аудиту."
    )
    add_p(
        doc,
        "Проєкт Domain Knowledge Hub розв’язує цю проблему для трьох груп користувачів із розмежуванням прав (RBAC): "
        "(а) Публічні користувачі (public_user) — доступ лише до відкритих довідкових даних та сертифікованих "
        "характеристик без персональних і внутрішніх записів; (б) Лісники та інженери (forester) — оперативний "
        "пошук регламентів, контроль стану виділів V-001..V-206 і отримання рекомендацій щодо профілактики загроз; "
        "(в) Екологічні аудитори та керівництво (auditor) — OLAP-звітність за семантичним шаром, перевірка "
        "альтернатив конфліктів і затвердження нових фактів через контур Human-in-the-Loop (HITL)."
    )

    # РОЗДІЛ 2
    add_h1(doc, "2. Архітектура Domain Knowledge Hub")
    add_p(
        doc,
        "Платформа побудована за принципом поліглотного (гібридного) сховища, де кожен тип запитів обслуговується "
        "оптимальним рушієм: (1) Графовий шар (Neo4j 5.26 + GDS / RDF Turtle, ЛР 9, 13, 14) зберігає зв’язки між "
        "4 лісництвами (LS-01..LS-04), 30 виділами, 11 продуктами таксономії ЛР 5, породами, загрозами та виконавцями; "
        "(2) Векторний шар (FAISS HNSW + multilingual-e5-small, ЛР 10–11) індексує 217 чанків галузевих документів; "
        "(3) Аналітичний OLAP-шар (DuckDB + PyArrow Parquet + semantic/metrics.yml, ЛР 12) зберігає 1 500 фактів "
        "заготівлі у зірковій схемі з SCD Type 2; (4) Шар інтелектуальних сервісів об’єднує GraphRAG-чатбот (ЛР 11), "
        "LLM-агента з MCP-сервером (ЛР 15) і гібридну рекомендаційну систему (ЛР 16)."
    )
    add_fig(doc, os.path.join(WORK, "work_lab12", "lab12", "docs", "fig_star_schema.png"),
            "Рисунок 1. Зіркова схема аналітичного OLAP-шару з інтеграцією таксономії ЛР 5 (ЛР 12)", width_in=5.5)

    # РОЗДІЛ 3
    add_h1(doc, "3. Знання, таксономія та походження (Provenance)")
    add_p(
        doc,
        "Ядром інтероперабельності Hub є єдина система ідентифікаторів IRI у просторі https://foresthub.ua/onto/, "
        "створена в ЛР 5–7 і перевикористана в усіх наступних модулях: у вимірі dim_product_taxonomy (ЛР 12), "
        "при нормалізації та entity linking 52 сутностей із текстів (ЛР 13), у SHACL-формах якості (ЛР 14) і в "
        "графових шляхах рекомендацій (ЛР 16). Кожне твердження, видобуте з текстів або внесене через HITL, "
        "супроводжується метаданими походження за стандартом W3C PROV-O: source_doc / source_url, символьні офсети "
        "[start_offset, end_offset), ідентифікатор моделі, версія підказки, рівень довіри (confidence) та автор "
        "схвалення (approved_by). Для конфліктів значень (CF-01, CF-03, CF-05) реалізовано збереження альтернатив "
        "у conflict_alternatives.json, а для дедуплікації — зворотний журнал злиття з операцією unmerge()."
    )

    # РОЗДІЛ 4
    add_h1(doc, "4. Еволюція метрик якості та результати експериментів (ЛР 9–16)")
    add_p(
        doc,
        "Усі модулі Hub пройшли кількісне оцінювання на відтворюваних тестових наборах (табл. 1). На рис. 2–5 "
        "подано ключові експериментальні результати видобування знань (ЛР 13), очищення бази та впливу на RAG "
        "(ЛР 14), сценарного тестування й Red Teaming агента (ЛР 15) та офлайн-оцінки рекомендацій (ЛР 16)."
    )
    add_p(doc, "Таблиця 1. Зведені експериментальні метрики Domain Knowledge Hub (ЛР 9–16)",
          align=WD_ALIGN_PARAGRAPH.LEFT, size=11, italic=True, space_after=2, keep_with_next=True)
    add_table(
        doc,
        ["Модуль (ЛР)", "Ключова технологія", "Тестовий набір", "Досягнуті метрики"],
        [
            ["Граф знань (ЛР 9 / СР 9)", "Neo4j 5.26 + GDS 2.13", "30 виділів, бенчмарк 3 СУБД", "6/6 Cypher + PageRank/Louvain; Neo4j найстабільніша"],
            ["Векторний пошук (ЛР 10 / СР 10)", "FAISS HNSW + e5-small", "30 укр. запитів, 3 моделі", "Recall@5 = 0.900, MRR = 0.854, 14.5 мс/запит"],
            ["GraphRAG (ЛР 11 / СР 11)", "Hybrid + Graph + Rerank", "32 + 20 стрес-запитів", "Faithfulness 0.906, Recall 0.975, Injection 100%"],
            ["OLAP + Text-to-SQL (ЛР 12)", "DuckDB/Parquet + AST", "1500 фактів, 9 OLAP, 12 T2SQL", "7/7 DQ PASS, pandas diff=0.00, Safety 100%"],
            ["Витяг знань IE (ЛР 13 / СР 13)", "Правила vs LLM + PROV", "24 док., 168 тв., κ=0.913", "LLM F1=0.970 vs Правила 0.923; 3 правила (lift≤3.0)"],
            ["Якість і CI (ЛР 14 / СР 14)", "SHACL + Dedup + CI-gate", "80→74 зап., 100 пар, 12 CI", "8/8 вимірів = 100%; RAG Faithfulness 0.906→0.969"],
            ["LLM-агент + MCP (ЛР 15 / СР 15)", "plan→retrieve→draft→verify", "12 сценаріїв, 8 атак, 3 HITL", "Сценарії 50%→100%; Атаки 0%→100%; HITL 2/3"],
            ["Рекомендації (ЛР 16)", "Graph + Emb + Hybrid RRF", "60 корист., часовий split", "Graph nDCG@10=0.555, Hybrid=0.515, Explain 100%"],
        ],
        [1.45, 1.45, 1.55, 2.05],
        font_size=9.0,
    )
    add_fig(doc, os.path.join(WORK, "work_lab13", "lab13", "docs", "fig_ie_comparison.png"),
            "Рисунок 2. Порівняння F1-міри видобування знань: Метод А (правила) vs Метод Б (LLM) (ЛР 13)", width_in=5.4)
    add_fig(doc, os.path.join(WORK, "work_lab14", "lab14", "docs", "fig_quality_before_after.png"),
            "Рисунок 3. Покращення 8 вимірів якості сховища та вплив очищення на метрики RAG (ЛР 14)", width_in=5.8)
    add_fig(doc, os.path.join(WORK, "work_lab15", "lab15", "docs", "fig_agent_eval.png"),
            "Рисунок 4. Динаміка сценарних тестів агента (v1 → v2) та блокування атак Red Teaming (ЛР 15)", width_in=5.6)
    add_fig(doc, os.path.join(WORK, "work_lab16", "lab16", "docs", "fig_reco_eval.png"),
            "Рисунок 5. Офлайн-оцінка 4 конфігурацій рекомендаційної системи на 60 користувачах (ЛР 16)", width_in=5.4)

    # РОЗДІЛ 5
    add_h1(doc, "5. Управління ризиками: EU AI Act та NIST AI RMF 1.0")
    add_p(
        doc,
        "Згідно з Регламентом ЄС 2024/1689 (EU AI Act), поточна версія Domain Knowledge Hub класифікується як "
        "система обмеженого ризику (Limited Risk, ст. 50), оскільки виконує довідково-аналітичну та рекомендаційну "
        "функцію без автономного ухвалення юридично зобов’язуючих рішень. Обов’язки прозорості виконуються через "
        "явне маркування відповідей ШІ, обов’язкові цитати, журнали трасування (trace_log.jsonl) та аудит HITL "
        "(hitl_audit.jsonl). У разі розширення системи до автоматичного видання лісорубних квитків вона перейшла б "
        "у категорію High-Risk (Додаток III), для якої вже закладено архітектурний фундамент: людський нагляд "
        "(ст. 14 — HITL propose_fact), CI-управління якістю даних (ст. 10) та оцінку ризиків (ст. 9)."
    )
    add_p(
        doc,
        "За фреймворком NIST AI RMF 1.0 (GOVERN / MAP / MEASURE / MANAGE) ідентифіковано й пом’якшено 8 ключових "
        "ризиків: прямий і непрямий prompt injection (ізоляція <untrusted_data>, фільтри), надмірні повноваження "
        "(read-only, AST SELECT, HITL), витік PII (RBAC), галюцинації (вузол verify + автоперевірка пояснень), "
        "tool poisoning (валідація дескрипторів MCP), DoS/зациклення (max_steps = 5, LIMIT 50, timeout = 10 с) "
        "та непрозорість змін (provenance). На 8 атаках Red Teaming досягнуто 100 % блокування."
    )

    # РОЗДІЛ 6
    add_h1(doc, "6. Економіка, продуктивність та вартість експлуатації")
    add_p(
        doc,
        "Архітектура Hub оптимізована за принципом мінімізації викликів дорогих LLM за рахунок локальних "
        "детермінованих шарів (FAISS, Neo4j, DuckDB/Parquet, правиловий IE для кодів). Оцінка операційних витрат "
        "(при використанні Gemini 2.5 Flash / GPT-4o-mini) наведена в табл. 2. Сумарна змінна вартість обробки "
        "1 000 запитів користувачів становить менше $2.15, а локальне розгортання через Docker Compose потребує "
        "лише 1 стандартного вузла (4 vCPU, 8 GB RAM)."
    )
    add_p(doc, "Таблиця 2. Економічна модель та затримки компонентів Hub",
          align=WD_ALIGN_PARAGRAPH.LEFT, size=11, italic=True, space_after=2, keep_with_next=True)
    add_table(
        doc,
        ["Компонент", "Середня затримка", "Вартість / 1 000 операцій", "Спосіб оптимізації витрат"],
        [
            ["Векторний пошук (e5-small, CPU)", "14.5 мс", "$0.00 (локально)", "Квантування / HNSW індекс"],
            ["OLAP-запити + семантичний шар", "< 10 мс", "$0.00 (локально)", "Parquet + кешування метрик"],
            ["Text-to-SQL (з AST-захистом)", "~350 мс", "$0.42", "Шаблони semantic/metrics.yml"],
            ["Витяг знань (гібрид Правила+LLM)", "~220 мс/док", "$0.70 (50% LLM)", "Правила для кодів, LLM для тексту"],
            ["GraphRAG + LLM-агент (4 вузли)", "~420 мс", "$2.15", "Ліміт max_steps=5, max_tokens=3000"],
        ],
        [1.95, 1.15, 1.40, 2.00],
        font_size=9.5,
        center_cols=[1, 2],
    )

    # РОЗДІЛ 7
    add_h1(doc, "7. Використання генеративного ШІ та протокол верифікації")
    add_p(
        doc,
        "Генеративний ШІ (Gemini 2.5 Pro / Flash) застосовувався протягом ЛР 9–16 за протоколом «LLM-експерт»: "
        "як генератор чернеток схем/SQL/SHACL, як екстрактор відношень (ЛР 13), як суддя спірних пар дедуплікації "
        "(ЛР 14), як «мозок» агента й red-team генератор атак (ЛР 15), а також для структурування цієї записки "
        "(ЛР 16). Жодне твердження ШІ не приймалося без незалежної перевірки (V1: цитата в тексті; V2: парсер/SHACL/CI; "
        "V3: рецензент/red team; V4: живий бенчмарк і pandas). У ході проєкту систематично відхилялися помилкові "
        "пропозиції LLM (20 % у Топ-20 таблиці тверджень): AVG(margin_pct) для неадитивної міри (CL-05), "
        "дедуплікація без коду (CL-13), автозапис квот без HITL (CL-16) і випадковий split рекомендацій (CL-20)."
    )

    # РОЗДІЛ 8
    add_h1(doc, "8. Обмеження та наступні кроки розвитку")
    add_p(
        doc,
        "Основні обмеження поточної версії: (1) частина транзакцій OLAP (1 500 фактів) і взаємодій рекомендацій "
        "(60 користувачів) згенерована детерміновано (seed = 42) на основі реальних сутностей домену; (2) сигнатурні "
        "фільтри непрямих ін’єкцій потребують доповнення семантичним класифікатором LLM-guard; (3) офлайн-метрики "
        "рекомендацій мають бути підтверджені польовим A/B-тестуванням. Наступні кроки (Roadmap 2027): інтеграція "
        "з державним реєстром лісорубних квитків та Sentinel-2 API, впровадження NLI-перевірки предиката для "
        "Abstention Rate ≥ 95 %, додавання семантичного фаєрвола для багатомовних атак і пілотне розгортання у "
        "лісництвах Львівської області."
    )

    # РОЗДІЛ 9: СПИСОК ЛІТЕРАТУРИ (>= 8 джерел)
    add_h1(doc, "9. Список літератури")
    refs = [
        "1. Конспект лекцій 1–16 курсу «Сховища знань та управління знаннями». — Львів: ЛНУ ім. Івана Франка, 2026.",
        "2. Kimball R., Ross M. The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling. — 3rd ed. — Wiley, 2013.",
        "3. Ricci F., Rokach L., Shapira B. Recommender Systems Handbook. — 2nd ed. — Springer, 2015.",
        "4. Aggarwal C. C. Recommender Systems: The Textbook. — Springer, 2016.",
        "5. Pipino L. L., Lee Y. W., Wang R. Y. Data Quality Assessment // Communications of the ACM. — 2002. — Vol. 45(4). — P. 211–218.",
        "6. Batini C., Scannapieco M. Data and Information Quality: Dimensions, Principles and Techniques. — Springer, 2016.",
        "7. Yao S. et al. ReAct: Synergizing Reasoning and Acting in Language Models // ICLR, 2023.",
        "8. Es S. et al. RAGAS: Automated Evaluation of Retrieval Augmented Generation // EACL, 2024.",
        "9. NIST. Artificial Intelligence Risk Management Framework (AI RMF 1.0). — NIST AI 100-1, 2023.",
        "10. European Parliament & Council. Regulation (EU) 2024/1689 (Artificial Intelligence Act). — Official Journal of the EU, 2024.",
    ]
    for r in refs:
        add_p(doc, r, size=10.5, space_after=2, line_spacing=1.08)

    # ДОДАТОК А: ТАБЛИЦЯ ТОП-20 ТВЕРДЖЕНЬ
    doc.add_page_break()
    add_h1(doc, "Додаток А. Таблиця Топ-20 тверджень проєкту (claims/claims.csv)")
    add_p(doc, "Підсумок: 20 тверджень — 16 підтверджено (80.0 %), 4 відхилено (20.0 %: CL-05, CL-13, CL-16, CL-20).",
          size=11, italic=True, space_after=3)
    claims_rows = []
    with open(os.path.join(LAB16, "claims", "claims.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            claims_rows.append([row["id"], row["claim"], row["verification_level"], row["status"], row["comment"]])
    add_table(
        doc,
        ["ID", "Твердження", "Рів.", "Статус", "Верифікація / пояснення"],
        claims_rows,
        [0.48, 2.52, 0.38, 0.68, 2.44],
        font_size=8.8,
        center_cols=[0, 2, 3],
    )

    os.makedirs(MID_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    doc.save(WP_DOCX)

    with tempfile.TemporaryDirectory(prefix="lo_wp_") as lo_profile:
        subprocess.run(
            [
                "libreoffice", f"-env:UserInstallation=file://{lo_profile}",
                "--headless", "--nologo", "--nolockcheck", "--norestore",
                "--convert-to", "pdf", "--outdir", MID_DIR, WP_DOCX,
            ],
            env={**os.environ, "HOME": "/tmp", "TMPDIR": "/tmp"},
            timeout=60,
            check=True,
        )
    pdf_mid = os.path.join(MID_DIR, "whitepaper.pdf")
    shutil.copyfile(pdf_mid, WP_PDF_REPO)
    shutil.copyfile(pdf_mid, WP_PDF_OUT)

    pdf = pdfium.PdfDocument(WP_PDF_REPO)
    print(f"Whitepaper PDF generated: {len(pdf)} pages (target 8-12) -> {WP_PDF_REPO}")
    for i in (1, len(pdf)):
        png_path = os.path.join(MID_DIR, f"wp_page_{i}.png")
        pdf[i - 1].render(scale=1.5).to_pil().save(png_path)
    pdf.close()


if __name__ == "__main__":
    build()
