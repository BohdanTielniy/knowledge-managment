#!/usr/bin/env python3
"""
СР 9, Крок 3: автоматизований бенчмарк 5 еквівалентних запитів у трьох
графових сховищах — Neo4j (Cypher), Memgraph (Cypher) та GraphDB Free (SPARQL 1.1).

Запуск у Docker: docker compose run --rm bench
Вихід: outputs/benchmark_results.json, outputs/benchmark_summary.txt
"""
import json
import os
import statistics
import time
import requests
from neo4j import GraphDatabase

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_JSON = os.path.join(ROOT, "data", "dataset.json")
DATA_TTL = os.path.join(ROOT, "data", "forest_sr09.ttl")
OUT_DIR = os.path.join(ROOT, "outputs")

RUNS = 5

CYPHER_QUERIES = {
    "Q1": """
        MATCH (c:Compartment)-[:AFFECTED_BY]->(t:Threat),
              (c)-[:PART_OF_FORESTRY]->(f:Forestry)
        WHERE c.damagedTreesShare > 10.0
        RETURN count(DISTINCT c) AS val
    """,
    "Q2": """
        MATCH (c:Compartment)-[:HAS_DOMINANT_SPECIES]->(s:ConiferousSpecies)
        WHERE c.standAgeYears >= 81
        RETURN count(DISTINCT c) AS val
    """,
    "Q3": """
        MATCH (h:TimberHarvesting)
        OPTIONAL MATCH (h)-[:FOLLOWED_BY]->(r:Reforestation)
        WITH h, r WHERE r IS NULL
        RETURN count(h) AS val
    """,
    "Q4": """
        MATCH (h:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry)
        RETURN round(sum(h.harvestVolumeM3) * 10) / 10.0 AS val
    """,
    "Q5": """
        MATCH (t:Threat)<-[:AFFECTED_BY]-(c:Compartment)<-[:APPLIED_TO]-(h:TimberHarvesting)-[:FOLLOWED_BY]->(r:Reforestation)
        RETURN count(DISTINCT c) AS val
    """,
}

SPARQL_PREFIX = "PREFIX fm: <http://lnu.edu.ua/ontologies/2026/forest-sr09#>\n"
SPARQL_QUERIES = {
    "Q1": SPARQL_PREFIX + """
        SELECT (COUNT(DISTINCT ?c) AS ?val) WHERE {
          ?c a fm:Compartment ;
             fm:damagedTreesShare ?d ;
             fm:affectedBy ?t ;
             fm:partOfForestry ?f .
          FILTER(?d > 10.0)
        }
    """,
    "Q2": SPARQL_PREFIX + """
        SELECT (COUNT(DISTINCT ?c) AS ?val) WHERE {
          ?c a fm:Compartment ;
             fm:standAgeYears ?age ;
             fm:hasDominantSpecies ?s .
          ?s a fm:ConiferousSpecies .
          FILTER(?age >= 81)
        }
    """,
    "Q3": SPARQL_PREFIX + """
        SELECT (COUNT(DISTINCT ?h) AS ?val) WHERE {
          ?h a fm:TimberHarvesting .
          FILTER NOT EXISTS { ?h fm:followedBy ?r . ?r a fm:Reforestation . }
        }
    """,
    "Q4": SPARQL_PREFIX + """
        SELECT (SUM(?v) AS ?val) WHERE {
          ?h a fm:TimberHarvesting ;
             fm:harvestVolumeM3 ?v ;
             fm:appliedTo ?c .
          ?c fm:partOfForestry ?f .
        }
    """,
    "Q5": SPARQL_PREFIX + """
        SELECT (COUNT(DISTINCT ?c) AS ?val) WHERE {
          ?c fm:affectedBy ?t .
          ?h a fm:TimberHarvesting ;
             fm:appliedTo ?c ;
             fm:followedBy ?r .
          ?r a fm:Reforestation .
        }
    """,
}


def wait_bolt(uri, auth, name, retries=40):
    for _ in range(retries):
        try:
            with GraphDatabase.driver(uri, auth=auth) as drv:
                with drv.session() as s:
                    s.run("RETURN 1").consume()
            print(f"[{name}] готовий ({uri})")
            return True
        except Exception:
            time.sleep(2)
    print(f"[{name}] НЕ вдалося підключитися ({uri})")
    return False


def load_bolt(uri, auth, data, is_memgraph=False):
    t0 = time.perf_counter()
    with GraphDatabase.driver(uri, auth=auth) as drv:
        with drv.session() as s:
            s.run("MATCH (n) DETACH DELETE n").consume()
            # Індекси
            idx_stmts = (
                [
                    "CREATE INDEX ON :Forestry(id)",
                    "CREATE INDEX ON :TreeSpecies(id)",
                    "CREATE INDEX ON :Threat(id)",
                    "CREATE INDEX ON :Forester(id)",
                    "CREATE INDEX ON :Compartment(id)",
                    "CREATE INDEX ON :Compartment(damagedTreesShare)",
                    "CREATE INDEX ON :Compartment(standAgeYears)",
                    "CREATE INDEX ON :TimberHarvesting(id)",
                    "CREATE INDEX ON :Reforestation(id)",
                ]
                if is_memgraph
                else [
                    "CREATE INDEX IF NOT EXISTS FOR (n:Forestry) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:TreeSpecies) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Threat) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Forester) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Compartment) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Compartment) ON (n.damagedTreesShare)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Compartment) ON (n.standAgeYears)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:TimberHarvesting) ON (n.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Reforestation) ON (n.id)",
                ]
            )
            for st in idx_stmts:
                try:
                    s.run(st).consume()
                except Exception:
                    pass

            n = data["nodes"]
            s.run("UNWIND $rows AS r CREATE (:Forestry {id:r.id, unitCode:r.unitCode, name:r.name})", rows=n["forestries"]).consume()
            s.run("UNWIND $rows AS r WITH r WHERE r.coniferous CREATE (:TreeSpecies:ConiferousSpecies {id:r.id, name:r.name})", rows=n["species"]).consume()
            s.run("UNWIND $rows AS r WITH r WHERE NOT r.coniferous CREATE (:TreeSpecies:DeciduousSpecies {id:r.id, name:r.name})", rows=n["species"]).consume()
            s.run("UNWIND $rows AS r CREATE (:Threat {id:r.id, name:r.name, kind:r.kind})", rows=n["threats"]).consume()
            s.run("UNWIND $rows AS r CREATE (:Forester {id:r.id, staffCode:r.staffCode, name:r.name})", rows=n["foresters"]).consume()
            s.run(
                "UNWIND $rows AS r CREATE (:Compartment {id:r.id, unitCode:r.unitCode, areaHectares:r.areaHectares, "
                "standAgeYears:r.standAgeYears, timberStockM3:r.timberStockM3, damagedTreesShare:r.damagedTreesShare, ndviValue:r.ndviValue})",
                rows=n["compartments"],
            ).consume()
            s.run("UNWIND $rows AS r CREATE (:TimberHarvesting {id:r.id, kind:r.kind, harvestVolumeM3:r.harvestVolumeM3})", rows=n["harvests"]).consume()
            s.run("UNWIND $rows AS r CREATE (:Reforestation {id:r.id, seedlings:r.seedlings})", rows=n["reforestations"]).consume()

            rel_specs = [
                ("PART_OF_FORESTRY", "Compartment", "Forestry"),
                ("HAS_DOMINANT_SPECIES", "Compartment", "TreeSpecies"),
                ("SUPERVISES", "Forester", "Compartment"),
                ("AFFECTED_BY", "Compartment", "Threat"),
                ("APPLIED_TO", "TimberHarvesting", "Compartment"),
                ("FOLLOWED_BY", "TimberHarvesting", "Reforestation"),
            ]
            for rtype, sl, el in rel_specs:
                s.run(
                    f"UNWIND $rows AS r MATCH (a:{sl} {{id:r.start}}), (b:{el} {{id:r.end}}) CREATE (a)-[:{rtype}]->(b)",
                    rows=data["rels"][rtype],
                ).consume()
    return round((time.perf_counter() - t0) * 1000.0, 2)


def bench_bolt(uri, auth):
    res = {}
    with GraphDatabase.driver(uri, auth=auth) as drv:
        with drv.session() as s:
            for qid, cypher in CYPHER_QUERIES.items():
                times = []
                val = None
                for _ in range(RUNS):
                    t0 = time.perf_counter()
                    rec = s.run(cypher).single()
                    times.append((time.perf_counter() - t0) * 1000.0)
                    val = rec["val"]
                res[qid] = {
                    "value": round(float(val), 1) if isinstance(val, float) else int(val),
                    "cold_ms": round(times[0], 3),
                    "warm_avg_ms": round(statistics.mean(times[1:]), 3),
                    "min_ms": round(min(times), 3),
                }
    return res


def wait_and_bench_graphdb(base_url):
    repo_id = "sr09"
    for _ in range(45):
        try:
            r = requests.get(f"{base_url}/rest/repositories", timeout=3)
            if r.status_code == 200:
                print(f"[GraphDB] готовий ({base_url})")
                break
        except Exception:
            time.sleep(2)
    else:
        print(f"[GraphDB] НЕ вдалося підключитися ({base_url})")
        return None

    # Створення репозиторію sr09 (якщо ще немає)
    repos = [x["id"] for x in requests.get(f"{base_url}/rest/repositories", timeout=10).json()]
    if repo_id not in repos:
        cfg = f"""
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix gdb: <http://www.ontotext.com/config/graphdb#>.
[] a rep:Repository ;
   rep:repositoryID "{repo_id}" ;
   rdfs:label "SR09 Forest Benchmark" ;
   rep:repositoryImpl [
     rep:repositoryType "graphdb:SailRepository" ;
     sr:sailImpl [
       sail:sailType "graphdb:Sail" ;
       gdb:ruleset "rdfsplus-optimized" ;
       gdb:storage-folder "storage"
     ]
   ].
"""
        r = requests.post(
            f"{base_url}/rest/repositories",
            files={"config": ("repo.ttl", cfg.encode("utf-8"), "text/turtle")},
            timeout=30,
        )
        r.raise_for_status()

    # Очищення та завантаження Turtle
    t0 = time.perf_counter()
    requests.delete(f"{base_url}/repositories/{repo_id}/statements", timeout=30).raise_for_status()
    with open(DATA_TTL, "rb") as fh:
        r = requests.post(
            f"{base_url}/repositories/{repo_id}/statements",
            headers={"Content-Type": "text/turtle;charset=utf-8"},
            data=fh.read(),
            timeout=60,
        )
        r.raise_for_status()
    load_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # Бенчмарк 5 SPARQL-запитів
    res = {}
    for qid, sparql in SPARQL_QUERIES.items():
        times = []
        val = None
        for _ in range(RUNS):
            tq0 = time.perf_counter()
            r = requests.post(
                f"{base_url}/repositories/{repo_id}",
                headers={"Accept": "application/sparql-results+json", "Content-Type": "application/sparql-query"},
                data=sparql.encode("utf-8"),
                timeout=30,
            )
            r.raise_for_status()
            times.append((time.perf_counter() - tq0) * 1000.0)
            raw_v = r.json()["results"]["bindings"][0]["val"]["value"]
            val = round(float(raw_v), 1) if "." in raw_v else int(raw_v)
        res[qid] = {
            "value": val,
            "cold_ms": round(times[0], 3),
            "warm_avg_ms": round(statistics.mean(times[1:]), 3),
            "min_ms": round(min(times), 3),
        }
    return {"load_ms": load_ms, "queries": res}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(DATA_JSON):
        import gen_dataset
        gen_dataset.generate()

    with open(DATA_JSON, encoding="utf-8") as fh:
        data = json.load(fh)

    results = {"dataset": data["summary"], "stores": {}}

    neo_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo_auth = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "sr09password"))
    if wait_bolt(neo_uri, neo_auth, "Neo4j"):
        lm = load_bolt(neo_uri, neo_auth, data, is_memgraph=False)
        results["stores"]["Neo4j"] = {"load_ms": lm, "queries": bench_bolt(neo_uri, neo_auth)}

    mem_uri = os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688")
    if wait_bolt(mem_uri, ("", ""), "Memgraph"):
        lm = load_bolt(mem_uri, ("", ""), data, is_memgraph=True)
        results["stores"]["Memgraph"] = {"load_ms": lm, "queries": bench_bolt(mem_uri, ("", ""))}

    gdb_url = os.environ.get("GRAPHDB_URL", "http://localhost:7200")
    gdb_res = wait_and_bench_graphdb(gdb_url)
    if gdb_res is not None:
        results["stores"]["GraphDB"] = gdb_res

    with open(os.path.join(OUT_DIR, "benchmark_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    lines = [
        f"Датасет: {data['summary']['total_nodes']} вузлів, {data['summary']['total_rels']} зв'язків (seed=42)",
        f"Очікувані результати: {data['summary']['expected']}",
        "",
        f"{'Сховище':10s} | {'Load(ms)':9s} | {'Q1(ms)':8s} | {'Q2(ms)':8s} | {'Q3(ms)':8s} | {'Q4(ms)':8s} | {'Q5(ms)':8s} | Значення Q1..Q5",
        "-" * 105,
    ]
    for st, info in results["stores"].items():
        q = info["queries"]
        vals = [q[f"Q{i}"]["value"] for i in range(1, 6)]
        lines.append(
            f"{st:10s} | {info['load_ms']:9.2f} | "
            + " | ".join(f"{q[f'Q{i}']['warm_avg_ms']:8.2f}" for i in range(1, 6))
            + f" | {vals}"
        )
    summary_txt = "\n".join(lines)
    with open(os.path.join(OUT_DIR, "benchmark_summary.txt"), "w", encoding="utf-8") as fh:
        fh.write(summary_txt + "\n")
    print("\n" + summary_txt)


if __name__ == "__main__":
    main()
