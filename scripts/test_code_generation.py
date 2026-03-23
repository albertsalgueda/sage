#!/usr/bin/env python3
"""
Experiment 1: Sage 200 Code Generation Test
============================================
Tests if Claude can generate valid Sage 200 artifacts (SQL, 4GL, queries)
from a functional specification, and compares against the known correct solution.

Usage:
    python scripts/test_code_generation.py
    python scripts/test_code_generation.py --model claude-sonnet-4-20250514
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher, unified_diff
from pathlib import Path

import anthropic

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "reference" / "prompt_certificacion.md"
SOLUTION_PATH = REPO_ROOT / "reference" / "solution_dat_extract.md"
RESULTS_DIR = REPO_ROOT / "results"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"

# System prompt: Sage 200 developer context
SYSTEM_PROMPT = """You are an expert Sage 200 developer. You write SQL, 4GL scripts, and query definitions following Sage 200 conventions exactly.

## Sage 4GL Language Reference
- Variables: `Dim X As Registro`, `Dim X.Field As Campo(Table, Field) Tipo`
- Control flow: `Ifn...Then...Else...Endif`, `Whilen...Then...Loop`, `Gosub/Goto`
- Records: AbreConsulta, CierraRegistro, Seleccion, Primero, Siguiente, Nuevo, Graba, Borra, IniciaRegistro, RefrescaRegistro
- SQL: EjecutaSQL("exec:=" & sql), EjecutaBorra, EjecutaInserta, EjecutaModifica
- Forms: FrmControl(screen, action, params...) — CONTROLENABLED, FIELDVALUE, REQUIREDVALUE, ALLOWUPDATE
- Events: Inicio, AlCambiar, AntesInsertar, DespuesInsertar, AntesModificar, DespuesModificar
- Functions: Mid, Left, Right, Trim, Val, Abs, Redondea, Ahora, CalcFecha, MsgBox
- Reports: ListadoEjecuta("ReportName","","","S","","")
- Apli.CancelarAccion = "-1" to cancel an action
- Apli.ApliCodigoEmpresa for the current company code

## SQL Conventions
- All custom tables use the prefix specified in the prompt (e.g., `CF_`)
- Every table starts with `CodigoEmpresa smallint NOT NULL DEFAULT ((0))`
- All custom fields are prefixed with the table prefix (e.g., CF_CodigoEquipo, CF_Nombre)
- PKs: `ALTER TABLE [T] WITH NOCHECK ADD CONSTRAINT [T_Principal] PRIMARY KEY CLUSTERED (...) ON [PRIMARY]`
- Types: `smallint` (integers, booleans), `varchar(N)` (text), `datetime` (dates)
- Booleans: 0=No, non-zero=Yes
- Defaults: ints → `((0))`, strings → `('')`, dates → `(getdate())`

## Screen Conventions
- Controls: `lbl` (labels), `txt` (inputs), `grd` (grids). Grid is always `grdDataForm`
- Grid layout name: `lyt` + TableName
- Relations for lookups: `Rel` + prefix
- List of values: `"Option1;Option2;Option3"`

## Output Format
Generate each artifact in a clearly labeled section with markdown code blocks:
1. **SQL — CREATE TABLE**: All CREATE TABLE statements
2. **SQL — PRIMARY KEYS**: All ALTER TABLE ... PRIMARY KEY statements
3. **SQL — Queries**: Any SELECT queries needed (e.g., ranking/ordering queries with JOINs)
4. **4GL — Screen Scripts**: Scripts for each screen (with events: Inicio, AlCambiar, etc.)
5. **4GL — Calculation Scripts**: Full calculation/process scripts
6. **Screen Definitions**: Control layout, labels, relations, defaults, grid layout"""


def load_file(path: Path) -> str:
    """Load a text file."""
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def call_claude(prompt: str, model: str) -> str:
    """Call Claude API with the Sage 200 context and functional spec."""
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    user_message = f"""Given the following functional specification for a Sage 200 module, generate ALL the required artifacts: SQL tables, primary keys, queries, 4GL screen scripts, 4GL calculation scripts, and screen definitions.

Be precise and follow Sage 200 conventions exactly. Use the CF_ prefix for all objects.

## Functional Specification

{prompt}

Generate the complete solution now."""

    print(f"Calling {model}...")
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text


def extract_sections(text: str) -> dict[str, str]:
    """Extract code blocks from markdown, keyed by their heading/label."""
    sections = {}
    # Find all code blocks with optional language tag
    pattern = r"(?:#{1,3}\s+(.+?)\n+)?```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    for heading, code in matches:
        key = heading.strip() if heading else f"block_{len(sections)}"
        sections[key] = code.strip()
    return sections


def normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison: lowercase, collapse whitespace, remove comments."""
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = sql.lower()
    sql = re.sub(r"\s+", " ", sql).strip()
    return sql


def normalize_4gl(code: str) -> str:
    """Normalize 4GL for comparison: collapse whitespace, strip comments."""
    code = re.sub(r"'.*$", "", code, flags=re.MULTILINE)  # Remove comments
    code = re.sub(r"\s+", " ", code).strip()
    return code


def similarity_score(a: str, b: str) -> float:
    """Compute similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()


def check_sql_tables(generated: str, solution: str) -> dict:
    """Check if generated SQL contains the correct CREATE TABLE statements."""
    expected_tables = ["CF_Clasificacion", "CF_Equipos", "CF_Resultados"]
    gen_lower = generated.lower()

    results = {}
    for table in expected_tables:
        has_create = f"create table" in gen_lower and table.lower() in gen_lower
        results[table] = {"present": has_create}

    # Check specific fields
    expected_fields = {
        "CF_Equipos": ["CF_CodigoEquipo", "CF_Nombre", "CF_JuegaEuropa", "CF_Competicion"],
        "CF_Resultados": ["CF_Jornada", "CF_EquipoLocal", "CF_GolesLocal",
                          "CF_EquipoVisitante", "CF_GolesVisitante", "CF_Fecha"],
        "CF_Clasificacion": ["CF_Posicion", "CF_Equipo", "CF_PartidosJugados",
                             "CF_PartidosGanados", "CF_PartidosEmpatados", "CF_PartidosPerdidos",
                             "CF_GolesFavor", "CF_GolesContra", "CF_Puntos",
                             "CF_Positivos", "CF_DiferenciaGoles"],
    }

    for table, fields in expected_fields.items():
        found = [f for f in fields if f.lower() in gen_lower]
        missing = [f for f in fields if f.lower() not in gen_lower]
        results[table]["fields_found"] = found
        results[table]["fields_missing"] = missing
        results[table]["field_score"] = len(found) / len(fields) if fields else 0

    return results


def check_primary_keys(generated: str, solution: str) -> dict:
    """Check if PRIMARY KEY constraints are correctly defined."""
    gen_lower = generated.lower()
    expected_pks = {
        "CF_Clasificacion": ["codigoempresa", "cf_posicion", "cf_equipo"],
        "CF_Equipos": ["codigoempresa", "cf_codigoequipo"],
        "CF_Resultados": ["codigoempresa", "cf_jornada", "cf_equipolocal", "cf_equipovisitante"],
    }

    results = {}
    for table, pk_cols in expected_pks.items():
        has_pk = "primary key" in gen_lower and table.lower() in gen_lower
        all_cols = all(col in gen_lower for col in pk_cols)
        results[table] = {"has_pk": has_pk, "correct_columns": all_cols}

    return results


def check_4gl_keywords(generated: str) -> dict:
    """Check if 4GL script uses expected keywords and patterns."""
    keywords = {
        "AbreConsulta": "Opens a query/recordset",
        "Seleccion": "Filters records",
        "Primero": "Moves to first record",
        "Siguiente": "Moves to next record",
        "EjecutaSQL": "Executes raw SQL",
        "EjecutaBorra": "Deletes records",
        "FrmControl": "Form control (screen scripts)",
        "MsgBox": "Message box",
        "Gosub": "Subroutine call",
        "Whilen": "While loop",
        "Ifn": "If condition",
        "ListadoEjecuta": "Launches a report",
        "IniciaRegistro": "Initializes a new record",
        "CierraRegistro": "Closes a recordset",
        "Nuevo": "Inserts new record",
    }

    gen_lower = generated.lower()
    results = {}
    for kw, desc in keywords.items():
        results[kw] = {"present": kw.lower() in gen_lower, "description": desc}

    found = sum(1 for v in results.values() if v["present"])
    results["_summary"] = {"found": found, "total": len(keywords), "score": found / len(keywords)}
    return results


def check_query(generated: str) -> dict:
    """Check if the ranking query is present with correct JOIN and ORDER BY."""
    gen_lower = generated.lower()
    checks = {
        "has_select": "select" in gen_lower,
        "has_join": "join" in gen_lower and "cf_equipos" in gen_lower and "cf_clasificacion" in gen_lower,
        "order_by_puntos": "cf_puntos" in gen_lower and "desc" in gen_lower,
        "order_by_positivos": "cf_positivos" in gen_lower,
        "order_by_dg": "cf_diferenciaGoles".lower() in gen_lower or "cf_diferenciagoles" in gen_lower,
        "order_by_nombre": "cf_nombre" in gen_lower,
    }
    score = sum(1 for v in checks.values() if v) / len(checks)
    checks["score"] = score
    return checks


def run_evaluation(generated: str, solution_text: str) -> dict:
    """Run all evaluation checks and produce a report."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {},
    }

    # 1. SQL Tables
    results["checks"]["sql_tables"] = check_sql_tables(generated, solution_text)

    # 2. Primary Keys
    results["checks"]["primary_keys"] = check_primary_keys(generated, solution_text)

    # 3. 4GL Keywords
    results["checks"]["4gl_keywords"] = check_4gl_keywords(generated)

    # 4. Query structure
    results["checks"]["ranking_query"] = check_query(generated)

    # 5. Overall similarity scores per section
    gen_sections = extract_sections(generated)
    sol_sections = extract_sections(solution_text)

    similarity = {}
    gen_all = normalize_sql(generated)
    sol_all = normalize_sql(solution_text)
    similarity["overall_normalized"] = round(similarity_score(gen_all, sol_all), 4)

    # SQL-specific similarity
    gen_sql = " ".join(v for k, v in gen_sections.items() if "sql" in k.lower() or "create" in k.lower() or "primary" in k.lower())
    sol_sql = " ".join(v for k, v in sol_sections.items() if "sql" in k.lower() or "create" in k.lower() or "primary" in k.lower())
    if gen_sql and sol_sql:
        similarity["sql_similarity"] = round(similarity_score(normalize_sql(gen_sql), normalize_sql(sol_sql)), 4)

    # 4GL-specific similarity
    gen_4gl = " ".join(v for k, v in gen_sections.items() if "4gl" in k.lower() or "script" in k.lower() or "calculation" in k.lower())
    sol_4gl = " ".join(v for k, v in sol_sections.items() if "4gl" in k.lower() or "script" in k.lower() or "calculation" in k.lower())
    if gen_4gl and sol_4gl:
        similarity["4gl_similarity"] = round(similarity_score(normalize_4gl(gen_4gl), normalize_4gl(sol_4gl)), 4)

    results["checks"]["similarity"] = similarity

    # Compute final scores
    table_scores = [v.get("field_score", 0) for v in results["checks"]["sql_tables"].values() if isinstance(v, dict)]
    pk_scores = [1.0 if v.get("has_pk") and v.get("correct_columns") else 0.0
                 for v in results["checks"]["primary_keys"].values() if isinstance(v, dict)]

    results["summary"] = {
        "sql_tables_avg": round(sum(table_scores) / len(table_scores), 4) if table_scores else 0,
        "primary_keys_avg": round(sum(pk_scores) / len(pk_scores), 4) if pk_scores else 0,
        "4gl_keyword_coverage": results["checks"]["4gl_keywords"]["_summary"]["score"],
        "ranking_query_score": results["checks"]["ranking_query"]["score"],
        "overall_similarity": similarity.get("overall_normalized", 0),
    }

    # Overall grade
    scores = list(results["summary"].values())
    results["summary"]["overall_grade"] = round(sum(scores) / len(scores) * 100, 1)

    return results


def print_report(results: dict):
    """Print a human-readable evaluation report."""
    print("\n" + "=" * 60)
    print("  SAGE 200 CODE GENERATION — EVALUATION REPORT")
    print("=" * 60)

    summary = results["summary"]
    print(f"\n  Overall Grade: {summary['overall_grade']}%\n")

    metrics = [
        ("SQL Tables (fields)", summary["sql_tables_avg"]),
        ("Primary Keys", summary["primary_keys_avg"]),
        ("4GL Keyword Coverage", summary["4gl_keyword_coverage"]),
        ("Ranking Query", summary["ranking_query_score"]),
        ("Text Similarity", summary["overall_similarity"]),
    ]

    for name, score in metrics:
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {name:<25} {bar} {score*100:5.1f}%")

    # Details: missing fields
    print("\n--- SQL Table Details ---")
    for table, info in results["checks"]["sql_tables"].items():
        if isinstance(info, dict) and "fields_missing" in info:
            status = "OK" if not info["fields_missing"] else f"MISSING: {', '.join(info['fields_missing'])}"
            print(f"  {table}: {status}")

    # Details: 4GL keywords
    print("\n--- 4GL Keyword Coverage ---")
    for kw, info in results["checks"]["4gl_keywords"].items():
        if kw.startswith("_"):
            continue
        symbol = "+" if info["present"] else "-"
        print(f"  [{symbol}] {kw}: {info['description']}")

    print("\n" + "=" * 60)


def generate_diff(generated: str, solution: str, output_path: Path):
    """Generate a unified diff file."""
    gen_lines = generated.splitlines(keepends=True)
    sol_lines = solution.splitlines(keepends=True)
    diff = unified_diff(sol_lines, gen_lines,
                        fromfile="solution (expected)", tofile="generated (actual)")
    diff_text = "".join(diff)
    output_path.write_text(diff_text, encoding="utf-8")
    return len(diff_text)


def main():
    parser = argparse.ArgumentParser(description="Sage 200 Code Generation Test")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Anthropic model to use (default: claude-sonnet-4-20250514)")
    parser.add_argument("--skip-api", action="store_true",
                        help="Skip API call, load last generated output from results/")
    args = parser.parse_args()

    # Check API key
    if not args.skip_api and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Load inputs
    prompt_text = load_file(PROMPT_PATH)
    solution_text = load_file(SOLUTION_PATH)

    # Ensure results directory
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate or load
    generated_path = RESULTS_DIR / f"generated_{timestamp}.md"
    if args.skip_api:
        # Find most recent generated file
        existing = sorted(RESULTS_DIR.glob("generated_*.md"))
        if not existing:
            print("ERROR: No previous generated output found in results/. Run without --skip-api first.")
            sys.exit(1)
        generated_path = existing[-1]
        print(f"Loading previous output: {generated_path.name}")
        generated_text = generated_path.read_text(encoding="utf-8")
    else:
        generated_text = call_claude(prompt_text, args.model)
        generated_path.write_text(generated_text, encoding="utf-8")
        print(f"Generated output saved: {generated_path.name}")

    # Evaluate
    results = run_evaluation(generated_text, solution_text)
    results["model"] = args.model
    results["generated_file"] = generated_path.name

    # Save evaluation report
    eval_path = RESULTS_DIR / f"evaluation_{timestamp}.json"
    eval_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evaluation saved: {eval_path.name}")

    # Save diff
    diff_path = RESULTS_DIR / f"diff_{timestamp}.txt"
    diff_size = generate_diff(generated_text, solution_text, diff_path)
    if diff_size > 0:
        print(f"Diff saved: {diff_path.name} ({diff_size} bytes)")

    # Print report
    print_report(results)

    return results["summary"]["overall_grade"]


if __name__ == "__main__":
    grade = main()
    sys.exit(0 if grade >= 50 else 1)
