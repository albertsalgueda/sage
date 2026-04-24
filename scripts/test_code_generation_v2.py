#!/usr/bin/env python3
"""
Experiment 1 v2: Sage 200 Code Generation Test (Expanded)
==========================================================
Tests Claude's ability to generate valid Sage 200 artifacts from a functional spec,
using 3 system prompt variants × 2 models = 6 configurations.

Usage:
    python scripts/test_code_generation_v2.py                      # Run all 6 configs
    python scripts/test_code_generation_v2.py --config few_shot    # Only few_shot prompt
    python scripts/test_code_generation_v2.py --model opus         # Only Opus model
    python scripts/test_code_generation_v2.py --skip-api           # Re-evaluate cached results
    python scripts/test_code_generation_v2.py --compare            # Compare all existing results
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher, unified_diff
from pathlib import Path

try:
    import sqlparse
    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False
    print("WARNING: sqlparse not installed. SQL validation will be skipped.")
    print("  Install with: pip install sqlparse")

import anthropic

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "reference" / "prompt_certificacion.md"
SOLUTION_PATH = REPO_ROOT / "reference" / "solution_dat_extract.md"
RESULTS_DIR = REPO_ROOT / "results" / "experiment1_v2"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}

# ---------------------------------------------------------------------------
# Import system prompts
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from system_prompts import PROMPTS

CONFIGS = list(PROMPTS.keys())  # ["basic", "few_shot", "full"]


# ===========================================================================
# API Call
# ===========================================================================

def call_claude(prompt: str, system_prompt: str, model: str) -> tuple[str, dict]:
    """Call Claude API. Returns (text, usage_dict)."""
    client = anthropic.Anthropic()

    user_message = (
        "Given the following functional specification for a Sage 200 module, "
        "generate ALL the required artifacts: SQL tables, primary keys, queries, "
        "4GL screen scripts, 4GL calculation scripts, and screen definitions.\n\n"
        "Be precise and follow Sage 200 conventions exactly. Use the CF_ prefix for all objects.\n\n"
        "## Functional Specification\n\n"
        f"{prompt}\n\n"
        "Generate the complete solution now."
    )

    print(f"  Calling {model}...")
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    usage = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "model": model,
    }
    return message.content[0].text, usage


# ===========================================================================
# Helpers
# ===========================================================================

def load_file(path: Path) -> str:
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Return list of (heading, code) from markdown."""
    pattern = r"(?:#{1,4}\s+(.+?)\n+)?```(?:\w+)?\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)


def normalize_sql(sql: str) -> str:
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = sql.lower()
    sql = re.sub(r"\s+", " ", sql).strip()
    return sql


def normalize_4gl(code: str) -> str:
    code = re.sub(r"'.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"\s+", " ", code).strip()
    return code


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# ===========================================================================
# Evaluation checks
# ===========================================================================

def check_sql_tables(gen: str) -> dict:
    """Check CREATE TABLE presence and fields."""
    gen_lower = gen.lower()
    expected_tables = {
        "CF_Equipos": ["CF_CodigoEquipo", "CF_Nombre", "CF_JuegaEuropa", "CF_Competicion"],
        "CF_Resultados": [
            "CF_Jornada", "CF_EquipoLocal", "CF_GolesLocal",
            "CF_EquipoVisitante", "CF_GolesVisitante", "CF_Fecha",
        ],
        "CF_Clasificacion": [
            "CF_Posicion", "CF_Equipo", "CF_PartidosJugados",
            "CF_PartidosGanados", "CF_PartidosEmpatados", "CF_PartidosPerdidos",
            "CF_GolesFavor", "CF_GolesContra", "CF_Puntos",
            "CF_Positivos", "CF_DiferenciaGoles",
        ],
    }

    results = {}
    for table, fields in expected_tables.items():
        has_create = "create table" in gen_lower and table.lower() in gen_lower
        found = [f for f in fields if f.lower() in gen_lower]
        missing = [f for f in fields if f.lower() not in gen_lower]
        score = len(found) / len(fields)
        results[table] = {
            "present": has_create,
            "fields_found": found,
            "fields_missing": missing,
            "field_score": round(score, 4),
        }
    return results


def check_primary_keys(gen: str) -> dict:
    gen_lower = gen.lower()
    expected = {
        "CF_Clasificacion": ["codigoempresa", "cf_posicion", "cf_equipo"],
        "CF_Equipos": ["codigoempresa", "cf_codigoequipo"],
        "CF_Resultados": ["codigoempresa", "cf_jornada", "cf_equipolocal", "cf_equipovisitante"],
    }
    results = {}
    for table, cols in expected.items():
        has_pk = "primary key" in gen_lower and table.lower() in gen_lower
        all_cols = all(c in gen_lower for c in cols)
        results[table] = {"has_pk": has_pk, "correct_columns": all_cols}
    return results


def check_4gl_keywords(gen: str) -> dict:
    keywords = {
        "AbreConsulta": "Open query workspace",
        "Seleccion": "Execute query / filter records",
        "Primero": "Move to first record",
        "Siguiente": "Move to next record",
        "EjecutaSQL": "Execute raw SQL",
        "EjecutaBorra": "Mass delete records",
        "FrmControl": "Screen control method",
        "MsgBox": "Message dialog",
        "Gosub": "Subroutine call",
        "Return": "Return from subroutine",
        "Whilen": "While loop (numeric)",
        "Ifn": "If condition (numeric)",
        "ListadoEjecuta": "Launch report",
        "IniciaRegistro": "Initialize new record",
        "CierraRegistro": "Close query workspace",
        "Nuevo": "Insert new record",
        "RefrescaRegistro": "Refresh data",
    }
    gen_lower = gen.lower()
    found = {}
    for kw, desc in keywords.items():
        found[kw] = {"present": kw.lower() in gen_lower, "description": desc}
    n_found = sum(1 for v in found.values() if v["present"])
    found["_summary"] = {"found": n_found, "total": len(keywords), "score": round(n_found / len(keywords), 4)}
    return found


def check_query(gen: str) -> dict:
    gen_lower = gen.lower()
    checks = {
        "has_select": "select" in gen_lower,
        "has_join": "join" in gen_lower and "cf_equipos" in gen_lower and "cf_clasificacion" in gen_lower,
        "order_by_puntos": "cf_puntos" in gen_lower and "desc" in gen_lower,
        "order_by_positivos": "cf_positivos" in gen_lower,
        "order_by_dg": "cf_diferenciagoles" in gen_lower,
        "order_by_nombre": "cf_nombre" in gen_lower,
    }
    score = sum(1 for v in checks.values() if v) / len(checks)
    checks["score"] = round(score, 4)
    return checks


def check_sql_validity(gen: str) -> dict:
    """Validate extracted SQL statements with sqlparse."""
    if not HAS_SQLPARSE:
        return {"available": False, "score": 0}

    # Extract SQL code blocks
    blocks = extract_code_blocks(gen)
    sql_blocks = [code for heading, code in blocks
                  if any(kw in heading.lower() for kw in ["sql", "create", "primary", "alter", "query"])
                  or any(kw in code.lower()[:50] for kw in ["create table", "alter table", "select"])]

    if not sql_blocks:
        # Try to find SQL in the full text
        sql_blocks = re.findall(
            r"(CREATE\s+TABLE[^;]+;?|ALTER\s+TABLE[^;]+;?|SELECT[^;]+;?)",
            gen, re.IGNORECASE | re.DOTALL,
        )

    if not sql_blocks:
        return {"available": True, "total": 0, "valid": 0, "score": 0}

    all_sql = "\n".join(sql_blocks)
    parsed = sqlparse.parse(all_sql)
    valid_stmts = 0
    total_stmts = 0
    errors = []

    for stmt in parsed:
        stmt_str = str(stmt).strip()
        if not stmt_str or stmt_str == ";":
            continue
        total_stmts += 1
        # sqlparse doesn't truly validate, but we can check for basic structure
        tokens = [t for t in stmt.tokens if not t.is_whitespace]
        if tokens:
            valid_stmts += 1
        else:
            errors.append(stmt_str[:80])

    score = valid_stmts / total_stmts if total_stmts > 0 else 0
    return {
        "available": True,
        "total": total_stmts,
        "valid": valid_stmts,
        "errors": errors[:3],
        "score": round(score, 4),
    }


def check_sage_conventions(gen: str) -> dict:
    """Check Sage-specific SQL conventions."""
    gen_lower = gen.lower()
    checks = {}

    # CodigoEmpresa as first field in CREATE TABLE
    # Look for CREATE TABLE followed by CodigoEmpresa as first column
    create_tables = re.findall(
        r"create\s+table[^(]+\(\s*\[?(\w+)\]?",
        gen_lower, re.DOTALL,
    )
    if create_tables:
        first_cols_are_empresa = sum(1 for c in create_tables if "codigoempresa" in c)
        checks["codigoempresa_first"] = {
            "pass": first_cols_are_empresa == len(create_tables),
            "detail": f"{first_cols_are_empresa}/{len(create_tables)} tables",
        }
    else:
        checks["codigoempresa_first"] = {"pass": False, "detail": "No CREATE TABLE found"}

    # Check correct types
    checks["uses_smallint"] = {"pass": "smallint" in gen_lower, "detail": "smallint for integers"}
    checks["uses_varchar"] = {"pass": "varchar" in gen_lower, "detail": "varchar for text"}
    checks["uses_datetime"] = {"pass": "datetime" in gen_lower, "detail": "datetime for dates"}

    # Check defaults
    checks["default_numeric"] = {
        "pass": "default" in gen_lower and ("((0))" in gen_lower or "default (0)" in gen_lower),
        "detail": "DEFAULT ((0)) for numeric",
    }
    checks["default_string"] = {
        "pass": "default" in gen_lower and ("('')" in gen_lower or "default ''" in gen_lower),
        "detail": "DEFAULT ('') for strings",
    }
    checks["default_date"] = {
        "pass": "getdate()" in gen_lower,
        "detail": "DEFAULT (getdate()) for dates",
    }

    # CF_ prefix on custom fields
    cf_fields = re.findall(r"cf_\w+", gen_lower)
    checks["cf_prefix_used"] = {
        "pass": len(cf_fields) > 10,
        "detail": f"{len(cf_fields)} CF_ prefixed identifiers",
    }

    # CF_Competicion default should be 1 (Vacio), not 0
    competicion_default_match = re.search(
        r"cf_competicion.*?default.*?\(\((\d+)\)\)", gen_lower, re.DOTALL,
    )
    if competicion_default_match:
        val = competicion_default_match.group(1)
        checks["competicion_default_1"] = {
            "pass": val == "1",
            "detail": f"CF_Competicion DEFAULT (({val})) — should be ((1)) for Vacio",
        }
    else:
        # Check alternate forms
        alt = re.search(r"cf_competicion.*?default\s+\((\d+)\)", gen_lower, re.DOTALL)
        if alt:
            val = alt.group(1)
            checks["competicion_default_1"] = {
                "pass": val == "1",
                "detail": f"CF_Competicion DEFAULT ({val}) — should be 1 for Vacio",
            }
        else:
            checks["competicion_default_1"] = {"pass": False, "detail": "CF_Competicion default not found"}

    # NOT NULL on all columns
    checks["all_not_null"] = {
        "pass": gen_lower.count("not null") >= 15,
        "detail": f"{gen_lower.count('not null')} NOT NULL clauses",
    }

    n_pass = sum(1 for v in checks.values() if v.get("pass"))
    total = len(checks)
    checks["_summary"] = {"passed": n_pass, "total": total, "score": round(n_pass / total, 4)}
    return checks


def check_artifact_completeness(gen: str) -> dict:
    """Check if all expected artifacts are generated."""
    gen_lower = gen.lower()

    expected = {
        "tables": {
            "CF_Equipos": "cf_equipos" in gen_lower and "create table" in gen_lower,
            "CF_Resultados": "cf_resultados" in gen_lower and "create table" in gen_lower,
            "CF_Clasificacion": "cf_clasificacion" in gen_lower and "create table" in gen_lower,
        },
        "queries": {
            "CF_Equipos": True,  # Implicit (table exists)
            "CF_Resultados": True,
            "CF_Clasificacion": True,
            "CF_ClasificacionOrden": any(
                kw in gen_lower for kw in ["clasificacionorden", "clasificacion_orden", "ranking"]
            ),
            "CF_ClasificacionLiga_Lis": any(
                kw in gen_lower for kw in ["clasificacionliga", "clasificacion_liga", "report query"]
            ),
        },
        "screens": {
            "CF_Equipos": any(
                kw in gen_lower
                for kw in ["screen.*cf_equipos", "pantalla.*cf_equipos", "mantenimiento.*cf_equipos",
                           "cf_equipos.*screen", "cf_equipos.*pantalla"]
            ) or ("frmcontrol" in gen_lower and "cf_equipos" in gen_lower),
            "CF_Resultados": any(
                kw in gen_lower
                for kw in ["screen.*cf_resultados", "pantalla.*cf_resultados"]
            ) or ("frmcontrol" in gen_lower and "cf_resultados" in gen_lower),
        },
        "calculations": {
            "CF_Clasificacion": "proceso" in gen_lower or "clasificacion" in gen_lower and "calculo" in gen_lower,
            "CF_Equipos": "cf_equipos" in gen_lower and ("inicio" in gen_lower or "alcambiar" in gen_lower),
            "CF_Resultados": "cf_resultados" in gen_lower,
        },
        "report": {
            "CF_ClasificacionOrden_Lis": any(
                kw in gen_lower
                for kw in ["listadoejecuta", "report", "informe", "clasificacionorden_lis", "clasificacion_lis"]
            ),
        },
        "operations": {
            "OP_CF_Clasificacion": any(
                kw in gen_lower for kw in ["op_cf_clasificacion", "operacion", "operation"]
            ),
            "OP_CF_Equipos": any(kw in gen_lower for kw in ["op_cf_equipos"]),
            "OP_CF_Resultados": any(kw in gen_lower for kw in ["op_cf_resultados"]),
        },
    }

    results = {}
    total_found = 0
    total_expected = 0
    for category, items in expected.items():
        cat_found = sum(1 for v in items.values() if v)
        cat_total = len(items)
        total_found += cat_found
        total_expected += cat_total
        results[category] = {
            "found": cat_found,
            "total": cat_total,
            "items": {k: v for k, v in items.items()},
        }

    results["_summary"] = {
        "found": total_found,
        "total": total_expected,
        "score": round(total_found / total_expected, 4) if total_expected else 0,
    }
    return results


def check_business_logic(gen: str) -> dict:
    """Check specific business rules from the spec."""
    gen_lower = gen.lower()
    checks = {}

    # 1. JuegaEuropa disables Competicion
    checks["juegaeuropa_disables_competicion"] = {
        "pass": (
            "juegaeuropa" in gen_lower
            and "competicion" in gen_lower
            and "controlenabled" in gen_lower
        ),
        "detail": "FrmControl CONTROLENABLED toggles Competicion based on JuegaEuropa",
    }

    # 2. Validation: if JuegaEuropa=yes, Competicion must be set
    checks["competicion_validation"] = {
        "pass": (
            "cancelaraccion" in gen_lower
            and "competicion" in gen_lower
        ),
        "detail": "Apli.CancelarAccion when JuegaEuropa=yes but Competicion empty",
    }

    # 3. Points: victory=3, draw=1, loss=0
    checks["points_victory_3"] = {
        "pass": "puntos" in gen_lower and ("+ 3" in gen_lower or "+3" in gen_lower or "puntos + 3" in gen_lower),
        "detail": "Victory = +3 points",
    }
    checks["points_draw_1"] = {
        "pass": "puntos" in gen_lower and ("+ 1" in gen_lower or "+1" in gen_lower),
        "detail": "Draw = +1 point",
    }

    # 4. Positivos calculation (visitor win=+3, visitor draw=+1, local draw=-1, local loss=-3)
    checks["positivos_calculated"] = {
        "pass": "positivos" in gen_lower and (
            ("- 3" in gen_lower or "-3" in gen_lower or "positivos - 3" in gen_lower)
            and ("- 1" in gen_lower or "-1" in gen_lower)
        ),
        "detail": "Positivos: local loss=-3, local draw=-1, visitor win=+3, visitor draw=+1",
    }

    # 5. DiferenciaGoles = GF - GC
    checks["diferencia_goles"] = {
        "pass": "diferenciagoles" in gen_lower and (
            "golesfavor" in gen_lower and "golescontra" in gen_lower
        ),
        "detail": "DiferenciaGoles = GolesFavor - GolesContra",
    }

    # 6. Ordering: Puntos DESC, Positivos DESC, DG DESC, PJ, Nombre
    checks["ordering_correct"] = {
        "pass": (
            "cf_puntos" in gen_lower
            and "desc" in gen_lower
            and "cf_positivos" in gen_lower
            and "cf_diferenciagoles" in gen_lower
        ),
        "detail": "ORDER BY Puntos DESC, Positivos DESC, DG DESC",
    }

    # 7. EjecutaBorra to clear classification before recalc
    checks["clears_before_recalc"] = {
        "pass": (
            "ejecutaborra" in gen_lower
            or ("delete" in gen_lower and "cf_clasificacion" in gen_lower)
        ),
        "detail": "Clears CF_Clasificacion before recalculation",
    }

    # 8. Launches report at end
    checks["launches_report"] = {
        "pass": "listadoejecuta" in gen_lower,
        "detail": "ListadoEjecuta called to launch classification report",
    }

    # 9. Uses EjecutaSQL("exec:=") for direct SQL
    checks["ejecutasql_exec"] = {
        "pass": 'exec:=' in gen_lower or "exec:=" in gen_lower,
        "detail": 'Uses EjecutaSQL("exec:=" & sql) for direct SQL execution',
    }

    # 10. Default date NOW for CF_Fecha
    checks["fecha_default_now"] = {
        "pass": "getdate()" in gen_lower or "now" in gen_lower and "fecha" in gen_lower,
        "detail": "CF_Fecha defaults to current date (NOW/getdate)",
    }

    n_pass = sum(1 for v in checks.values() if isinstance(v, dict) and v.get("pass"))
    total = len(checks)
    checks["_summary"] = {"passed": n_pass, "total": total, "score": round(n_pass / total, 4)}
    return checks


def compute_section_similarity(gen: str, sol: str) -> dict:
    """Compute similarity scores per section type."""
    results = {}

    # Overall
    gen_norm = normalize_sql(gen)
    sol_norm = normalize_sql(sol)
    results["overall"] = round(similarity(gen_norm, sol_norm), 4)

    # SQL blocks
    gen_blocks = extract_code_blocks(gen)
    sol_blocks = extract_code_blocks(sol)

    gen_sql = " ".join(
        code for h, code in gen_blocks
        if any(kw in h.lower() for kw in ["sql", "create", "primary", "alter"])
        or any(kw in code.lower()[:30] for kw in ["create table", "alter table"])
    )
    sol_sql = " ".join(
        code for h, code in sol_blocks
        if any(kw in h.lower() for kw in ["sql", "create", "primary", "alter"])
        or any(kw in code.lower()[:30] for kw in ["create table", "alter table"])
    )
    if gen_sql and sol_sql:
        results["sql"] = round(similarity(normalize_sql(gen_sql), normalize_sql(sol_sql)), 4)

    # 4GL blocks
    gen_4gl = " ".join(
        code for h, code in gen_blocks
        if any(kw in h.lower() for kw in ["4gl", "script", "calculation", "calculo"])
        or any(kw in code[:50] for kw in ["Dim ", "Inicio:", "Gosub", "AbreConsulta"])
    )
    sol_4gl = " ".join(
        code for h, code in sol_blocks
        if any(kw in h.lower() for kw in ["4gl", "script", "calculation", "calculo"])
        or any(kw in code[:50] for kw in ["Dim ", "Inicio:", "Gosub", "AbreConsulta"])
    )
    if gen_4gl and sol_4gl:
        results["4gl"] = round(similarity(normalize_4gl(gen_4gl), normalize_4gl(sol_4gl)), 4)

    return results


# ===========================================================================
# Composite evaluation
# ===========================================================================

def run_evaluation(generated: str, solution: str) -> dict:
    """Run all evaluation checks."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {},
    }

    results["checks"]["sql_tables"] = check_sql_tables(generated)
    results["checks"]["primary_keys"] = check_primary_keys(generated)
    results["checks"]["4gl_keywords"] = check_4gl_keywords(generated)
    results["checks"]["ranking_query"] = check_query(generated)
    results["checks"]["sql_validity"] = check_sql_validity(generated)
    results["checks"]["sage_conventions"] = check_sage_conventions(generated)
    results["checks"]["artifact_completeness"] = check_artifact_completeness(generated)
    results["checks"]["business_logic"] = check_business_logic(generated)
    results["checks"]["similarity"] = compute_section_similarity(generated, solution)

    # Compute summary scores
    table_scores = [v["field_score"] for v in results["checks"]["sql_tables"].values() if isinstance(v, dict)]
    pk_scores = [
        1.0 if v.get("has_pk") and v.get("correct_columns") else 0.0
        for v in results["checks"]["primary_keys"].values()
        if isinstance(v, dict)
    ]

    summary = {
        "sql_tables": round(sum(table_scores) / len(table_scores), 4) if table_scores else 0,
        "primary_keys": round(sum(pk_scores) / len(pk_scores), 4) if pk_scores else 0,
        "4gl_keywords": results["checks"]["4gl_keywords"]["_summary"]["score"],
        "ranking_query": results["checks"]["ranking_query"]["score"],
        "sql_validity": results["checks"]["sql_validity"].get("score", 0),
        "sage_conventions": results["checks"]["sage_conventions"]["_summary"]["score"],
        "artifact_completeness": results["checks"]["artifact_completeness"]["_summary"]["score"],
        "business_logic": results["checks"]["business_logic"]["_summary"]["score"],
        "similarity_overall": results["checks"]["similarity"].get("overall", 0),
        "similarity_sql": results["checks"]["similarity"].get("sql", 0),
        "similarity_4gl": results["checks"]["similarity"].get("4gl", 0),
    }

    # Weighted overall grade (similarity has lower weight since it's formatting-sensitive)
    weights = {
        "sql_tables": 1.0,
        "primary_keys": 1.0,
        "4gl_keywords": 1.0,
        "ranking_query": 1.0,
        "sql_validity": 0.5,
        "sage_conventions": 1.5,       # Important for real-world usability
        "artifact_completeness": 1.5,  # Important for completeness
        "business_logic": 2.0,         # Most important — functional correctness
        "similarity_sql": 0.3,
        "similarity_4gl": 0.2,
    }
    weighted_sum = sum(summary.get(k, 0) * w for k, w in weights.items())
    total_weight = sum(weights.values())
    summary["overall_grade"] = round(weighted_sum / total_weight * 100, 1)

    results["summary"] = summary
    return results


# ===========================================================================
# Reporting
# ===========================================================================

def print_report(results: dict, config_name: str, model_name: str):
    """Print evaluation report for one configuration."""
    s = results["summary"]
    print(f"\n{'=' * 60}")
    print(f"  {model_name.upper()} + {config_name.upper()}")
    print(f"  Overall Grade: {s['overall_grade']}%")
    print(f"{'=' * 60}")

    metrics = [
        ("SQL Tables (fields)", s["sql_tables"]),
        ("Primary Keys", s["primary_keys"]),
        ("4GL Keywords", s["4gl_keywords"]),
        ("Ranking Query", s["ranking_query"]),
        ("SQL Validity", s["sql_validity"]),
        ("Sage Conventions", s["sage_conventions"]),
        ("Artifact Completeness", s["artifact_completeness"]),
        ("Business Logic", s["business_logic"]),
        ("Similarity (SQL)", s.get("similarity_sql", 0)),
        ("Similarity (4GL)", s.get("similarity_4gl", 0)),
    ]
    for name, score in metrics:
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {name:<25} {bar} {score * 100:5.1f}%")


def generate_section_diffs(gen: str, sol: str) -> dict:
    """Generate side-by-side diffs for SQL and 4GL sections."""
    diffs = {}

    gen_blocks = extract_code_blocks(gen)
    sol_blocks = extract_code_blocks(sol)

    # SQL diff
    gen_sql_parts = [code for h, code in gen_blocks
                     if any(kw in h.lower() for kw in ["sql", "create", "primary"])
                     or "create table" in code.lower()[:30] or "alter table" in code.lower()[:30]]
    sol_sql_parts = [code for h, code in sol_blocks
                     if any(kw in h.lower() for kw in ["sql", "create", "primary"])
                     or "create table" in code.lower()[:30] or "alter table" in code.lower()[:30]]

    if gen_sql_parts and sol_sql_parts:
        gen_sql = "\n\n".join(gen_sql_parts)
        sol_sql = "\n\n".join(sol_sql_parts)
        diff = list(unified_diff(
            sol_sql.splitlines(keepends=True),
            gen_sql.splitlines(keepends=True),
            fromfile="solution (SQL)", tofile="generated (SQL)",
        ))
        diffs["sql"] = "".join(diff)

    # 4GL diff
    gen_4gl_parts = [code for h, code in gen_blocks
                     if any(kw in h.lower() for kw in ["4gl", "script", "calculation"])
                     or "Dim " in code[:30] or "Inicio:" in code[:50]]
    sol_4gl_parts = [code for h, code in sol_blocks
                     if any(kw in h.lower() for kw in ["4gl", "script", "calculation"])
                     or "Dim " in code[:30] or "Inicio:" in code[:50]]

    if gen_4gl_parts and sol_4gl_parts:
        gen_4gl = "\n\n".join(gen_4gl_parts)
        sol_4gl = "\n\n".join(sol_4gl_parts)
        diff = list(unified_diff(
            sol_4gl.splitlines(keepends=True),
            gen_4gl.splitlines(keepends=True),
            fromfile="solution (4GL)", tofile="generated (4GL)",
        ))
        diffs["4gl"] = "".join(diff)

    return diffs


def generate_comparison_table(all_results: dict) -> str:
    """Generate markdown comparison table from all results."""
    lines = []
    lines.append("# Experiment 1 v2 — Comparison Results\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Header
    configs = sorted(all_results.keys())
    lines.append("| Metric | " + " | ".join(configs) + " |")
    lines.append("|--------|" + "|".join(["--------"] * len(configs)) + "|")

    # Get metric names from first result
    if not configs:
        return "\n".join(lines)

    first = all_results[configs[0]]
    metrics = [
        ("Overall Grade", "overall_grade"),
        ("SQL Tables", "sql_tables"),
        ("Primary Keys", "primary_keys"),
        ("4GL Keywords", "4gl_keywords"),
        ("Ranking Query", "ranking_query"),
        ("SQL Validity", "sql_validity"),
        ("Sage Conventions", "sage_conventions"),
        ("Artifact Completeness", "artifact_completeness"),
        ("Business Logic", "business_logic"),
        ("Similarity (SQL)", "similarity_sql"),
        ("Similarity (4GL)", "similarity_4gl"),
    ]

    for label, key in metrics:
        vals = []
        for config in configs:
            r = all_results[config]
            v = r["summary"].get(key, 0)
            if key == "overall_grade":
                vals.append(f"**{v}%**")
            else:
                vals.append(f"{v * 100:.1f}%")
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    # Token usage
    lines.append("\n## API Usage\n")
    lines.append("| Config | Input Tokens | Output Tokens | Model |")
    lines.append("|--------|-------------|--------------|-------|")
    for config in configs:
        r = all_results[config]
        usage = r.get("usage", {})
        lines.append(
            f"| {config} | {usage.get('input_tokens', 'N/A')} | "
            f"{usage.get('output_tokens', 'N/A')} | {usage.get('model', 'N/A')} |"
        )

    return "\n".join(lines)


# ===========================================================================
# Main
# ===========================================================================

def run_single(config: str, model_key: str, prompt_text: str, solution_text: str,
               skip_api: bool = False) -> dict | None:
    """Run a single configuration."""
    model = MODELS[model_key]
    config_name = f"{model_key}_{config}"
    config_dir = RESULTS_DIR / config_name

    print(f"\n--- Running: {config_name} ---")

    if skip_api:
        # Load cached results
        cached = sorted(config_dir.glob("generated_*.md")) if config_dir.exists() else []
        if not cached:
            print(f"  No cached results for {config_name}. Skipping.")
            return None
        gen_path = cached[-1]
        print(f"  Loading cached: {gen_path.name}")
        generated = gen_path.read_text(encoding="utf-8")
        usage = {}
    else:
        system_prompt = PROMPTS[config]
        generated, usage = call_claude(prompt_text, system_prompt, model)
        config_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        gen_path = config_dir / f"generated_{ts}.md"
        gen_path.write_text(generated, encoding="utf-8")
        print(f"  Saved: {gen_path.name}")

    # Evaluate
    results = run_evaluation(generated, solution_text)
    results["config"] = config_name
    results["model"] = model
    results["prompt_variant"] = config
    results["usage"] = usage

    # Save evaluation JSON
    config_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_path = config_dir / f"evaluation_{ts}.json"
    eval_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save section diffs
    diffs = generate_section_diffs(generated, solution_text)
    for section, diff_text in diffs.items():
        if diff_text:
            diff_path = config_dir / f"diff_{section}_{ts}.txt"
            diff_path.write_text(diff_text, encoding="utf-8")

    # Print report
    print_report(results, config, model_key)

    return results


def main():
    parser = argparse.ArgumentParser(description="Sage 200 Code Generation Test v2")
    parser.add_argument("--config", choices=CONFIGS, help="Run only this prompt variant")
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Run only this model")
    parser.add_argument("--skip-api", action="store_true", help="Re-evaluate cached results")
    parser.add_argument("--compare", action="store_true", help="Compare all existing results")
    args = parser.parse_args()

    # Check API key
    if not args.skip_api and not args.compare and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Load inputs
    prompt_text = load_file(PROMPT_PATH)
    solution_text = load_file(SOLUTION_PATH)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Determine which configs to run
    configs_to_run = [args.config] if args.config else CONFIGS
    models_to_run = [args.model] if args.model else list(MODELS.keys())

    if args.compare:
        # Load all existing results and compare
        all_results = {}
        for config_dir in sorted(RESULTS_DIR.iterdir()):
            if not config_dir.is_dir():
                continue
            evals = sorted(config_dir.glob("evaluation_*.json"))
            if evals:
                latest = json.loads(evals[-1].read_text(encoding="utf-8"))
                all_results[config_dir.name] = latest
                print_report(latest, latest.get("prompt_variant", "?"), config_dir.name.split("_")[0])

        if all_results:
            table = generate_comparison_table(all_results)
            comparison_path = RESULTS_DIR / "COMPARISON.md"
            comparison_path.write_text(table, encoding="utf-8")
            print(f"\n\nComparison saved: {comparison_path}")
            print("\n" + table)
        else:
            print("No results found. Run tests first.")
        return

    # Run configurations
    all_results = {}
    total_cost = 0.0

    for model_key in models_to_run:
        for config in configs_to_run:
            result = run_single(config, model_key, prompt_text, solution_text, args.skip_api)
            if result:
                config_name = f"{model_key}_{config}"
                all_results[config_name] = result

                # Estimate cost
                usage = result.get("usage", {})
                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                if "opus" in model_key:
                    cost = inp * 15 / 1_000_000 + out * 75 / 1_000_000
                else:
                    cost = inp * 3 / 1_000_000 + out * 15 / 1_000_000
                total_cost += cost
                print(f"  Estimated cost: ${cost:.4f}")

    # Generate comparison
    if len(all_results) > 1:
        table = generate_comparison_table(all_results)
        comparison_path = RESULTS_DIR / "COMPARISON.md"
        comparison_path.write_text(table, encoding="utf-8")
        print(f"\n{'=' * 60}")
        print("  COMPARISON TABLE")
        print(f"{'=' * 60}")
        print(table)

    if total_cost > 0:
        print(f"\n  Total estimated API cost: ${total_cost:.4f}")

    # Find winner
    if all_results:
        best_config = max(all_results.items(), key=lambda x: x[1]["summary"]["overall_grade"])
        print(f"\n  WINNER: {best_config[0]} with {best_config[1]['summary']['overall_grade']}%")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
