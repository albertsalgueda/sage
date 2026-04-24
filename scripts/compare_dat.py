#!/usr/bin/env python3
"""
Compare generated .dat with reference .dat for Sage 200.

Since .dat files are binary/proprietary, comparison is done by:
1. Extracting readable strings from both files
2. Identifying SQL (CREATE TABLE, ALTER TABLE, etc.)
3. Identifying 4GL code (Dim, Ifn, Whilen, etc.)
4. Identifying metadata (query names, screen names, etc.)
5. Scoring similarity across categories

Usage:
    python compare_dat.py <reference.dat> <generated.dat>
    python compare_dat.py --extract <file.dat>         # Extract and display contents
    python compare_dat.py --reference-only              # Analyze reference .dat from assets/
"""

import argparse
import re
import sys
import json
import subprocess
from pathlib import Path
from difflib import SequenceMatcher, unified_diff
from collections import defaultdict

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
REFERENCE_ZIP = ASSETS_DIR / "knowledge" / "Cert_JaviCoboHAvanzada.zip"
RESULTS_DIR = Path(__file__).parent.parent / "results" / "dat_comparison"


# ---------------------------------------------------------------------------
# String extraction
# ---------------------------------------------------------------------------

def extract_strings(dat_path: Path, min_length: int = 6) -> list[str]:
    """Extract readable strings from a binary .dat file."""
    try:
        r = subprocess.run(
            ["strings", "-n", str(min_length), str(dat_path)],
            capture_output=True, text=True, timeout=30
        )
        return r.stdout.splitlines()
    except Exception as e:
        print(f"Warning: strings command failed: {e}")
        # Fallback: manual extraction
        data = dat_path.read_bytes()
        result = []
        current = []
        for byte in data:
            if 32 <= byte < 127:
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    result.append("".join(current))
                current = []
        if len(current) >= min_length:
            result.append("".join(current))
        return result


def extract_from_zip(zip_path: Path) -> dict[str, list[str]]:
    """Extract strings from all .dat/.da1 files in a zip."""
    import zipfile
    import tempfile

    results = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        with tempfile.TemporaryDirectory() as tmpdir:
            zf.extractall(tmpdir)
            for f in Path(tmpdir).rglob("*"):
                if f.suffix.lower() in (".dat", ".da1"):
                    results[f.name] = extract_strings(f)
    return results


# ---------------------------------------------------------------------------
# Content classification
# ---------------------------------------------------------------------------

SQL_PATTERNS = [
    re.compile(r"CREATE\s+TABLE", re.IGNORECASE),
    re.compile(r"ALTER\s+TABLE", re.IGNORECASE),
    re.compile(r"PRIMARY\s+KEY", re.IGNORECASE),
    re.compile(r"DEFAULT\s*\(", re.IGNORECASE),
    re.compile(r"\bSELECT\b.*\bFROM\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bLEFT\s+JOIN\b", re.IGNORECASE),
    re.compile(r"\bORDER\s+BY\b", re.IGNORECASE),
]

FOURGL_PATTERNS = [
    re.compile(r"\bDim\s+\w+\s+As\b"),
    re.compile(r"\bIfn\b.*\bThen\b"),
    re.compile(r"\bWhilen\b.*\bThen\b"),
    re.compile(r"\bAbreConsulta\b"),
    re.compile(r"\bEjecutaSQL\b"),
    re.compile(r"\bEjecutaBorra\b"),
    re.compile(r"\bFrmControl\b"),
    re.compile(r"\bSeleccion\b"),
    re.compile(r"\bPrimero\b"),
    re.compile(r"\bSiguiente\b"),
    re.compile(r"\bNuevo\b"),
    re.compile(r"\bGosub\b"),
    re.compile(r"\bReturn\b"),
    re.compile(r"\bListadoEjecuta\b"),
    re.compile(r"\bRefrescaRegistro\b"),
    re.compile(r"\bCierraRegistro\b"),
    re.compile(r"\bIniciaRegistro\b"),
    re.compile(r"\bMsgBox\b"),
]

METADATA_PATTERNS = [
    re.compile(r"CF_\w+"),
    re.compile(r"OP_CF_\w+"),
    re.compile(r"lyt\w+"),
    re.compile(r"txt\w+"),
    re.compile(r"lbl\w+"),
    re.compile(r"grdDataForm"),
    re.compile(r"Mantenimiento\s+de"),
    re.compile(r"Clasificacion"),
]


def classify_strings(strings: list[str]) -> dict[str, list[str]]:
    """Classify extracted strings into categories."""
    categories = {
        "sql": [],
        "fourgl": [],
        "metadata": [],
        "table_names": set(),
        "field_names": set(),
        "query_names": set(),
        "screen_names": set(),
        "other": [],
    }

    for s in strings:
        s_stripped = s.strip()
        if not s_stripped:
            continue

        is_sql = any(p.search(s_stripped) for p in SQL_PATTERNS)
        is_4gl = any(p.search(s_stripped) for p in FOURGL_PATTERNS)
        is_meta = any(p.search(s_stripped) for p in METADATA_PATTERNS)

        if is_sql:
            categories["sql"].append(s_stripped)
        if is_4gl:
            categories["fourgl"].append(s_stripped)
        if is_meta:
            categories["metadata"].append(s_stripped)

        # Extract specific names
        for m in re.finditer(r"\bCF_(\w+)\b", s_stripped):
            name = "CF_" + m.group(1)
            if name in ("CF_Equipos", "CF_Resultados", "CF_Clasificacion"):
                categories["table_names"].add(name)
            elif name.endswith("_Lis"):
                categories["query_names"].add(name)
            else:
                categories["field_names"].add(name)

        if not (is_sql or is_4gl or is_meta):
            categories["other"].append(s_stripped)

    # Convert sets to sorted lists
    for key in ("table_names", "field_names", "query_names", "screen_names"):
        categories[key] = sorted(categories[key])

    return categories


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {"CF_Clasificacion", "CF_Equipos", "CF_Resultados"}
EXPECTED_FIELDS = {
    "CF_Posicion", "CF_Equipo", "CF_PartidosJugados", "CF_PartidosGanados",
    "CF_PartidosEmpatados", "CF_PartidosPerdidos", "CF_GolesFavor",
    "CF_GolesContra", "CF_Puntos", "CF_Positivos", "CF_DiferenciaGoles",
    "CF_CodigoEquipo", "CF_Nombre", "CF_JuegaEuropa", "CF_Competicion",
    "CF_Jornada", "CF_EquipoLocal", "CF_GolesLocal", "CF_EquipoVisitante",
    "CF_GolesVisitante", "CF_Fecha",
}
EXPECTED_QUERIES = {
    "CF_Clasificacion", "CF_ClasificacionLiga_Lis", "CF_ClasificacionOrden",
    "CF_Equipos", "CF_Resultados",
}
EXPECTED_4GL_KEYWORDS = {
    "AbreConsulta", "EjecutaBorra", "EjecutaSQL", "FrmControl",
    "Seleccion", "Primero", "Siguiente", "Nuevo", "Gosub", "Return",
    "ListadoEjecuta", "RefrescaRegistro", "CierraRegistro", "IniciaRegistro",
    "MsgBox", "Ifn", "Whilen",
}
EXPECTED_OPERATIONS = {"OP_CF_Clasificacion", "OP_CF_Equipos", "OP_CF_Resultados"}


def compare_categories(ref: dict, gen: dict) -> dict:
    """Compare two classified string sets and produce a score."""
    scores = {}

    # Table names
    ref_tables = set(ref.get("table_names", []))
    gen_tables = set(gen.get("table_names", []))
    expected = EXPECTED_TABLES
    found = gen_tables & expected
    scores["tables"] = {
        "expected": sorted(expected),
        "found": sorted(found),
        "missing": sorted(expected - found),
        "extra": sorted(gen_tables - expected),
        "score": len(found) / len(expected) * 100 if expected else 100,
    }

    # Field names
    ref_fields = set(ref.get("field_names", []))
    gen_fields = set(gen.get("field_names", []))
    found_fields = gen_fields & EXPECTED_FIELDS
    scores["fields"] = {
        "expected": len(EXPECTED_FIELDS),
        "found": len(found_fields),
        "missing": sorted(EXPECTED_FIELDS - found_fields),
        "score": len(found_fields) / len(EXPECTED_FIELDS) * 100,
    }

    # 4GL keywords
    ref_4gl_text = "\n".join(ref.get("fourgl", []))
    gen_4gl_text = "\n".join(gen.get("fourgl", []))
    found_kw = set()
    for kw in EXPECTED_4GL_KEYWORDS:
        if kw in gen_4gl_text:
            found_kw.add(kw)
    scores["fourgl_keywords"] = {
        "expected": sorted(EXPECTED_4GL_KEYWORDS),
        "found": sorted(found_kw),
        "missing": sorted(EXPECTED_4GL_KEYWORDS - found_kw),
        "score": len(found_kw) / len(EXPECTED_4GL_KEYWORDS) * 100,
    }

    # SQL similarity
    ref_sql_text = "\n".join(sorted(ref.get("sql", [])))
    gen_sql_text = "\n".join(sorted(gen.get("sql", [])))
    sql_sim = SequenceMatcher(None, ref_sql_text, gen_sql_text).ratio() * 100
    scores["sql_similarity"] = {"score": round(sql_sim, 1)}

    # 4GL similarity
    fourgl_sim = SequenceMatcher(None, ref_4gl_text, gen_4gl_text).ratio() * 100
    scores["fourgl_similarity"] = {"score": round(fourgl_sim, 1)}

    # Operations check
    all_gen_text = "\n".join(gen.get("metadata", []) + gen.get("other", []))
    found_ops = set()
    for op in EXPECTED_OPERATIONS:
        if op in all_gen_text:
            found_ops.add(op)
    scores["operations"] = {
        "expected": sorted(EXPECTED_OPERATIONS),
        "found": sorted(found_ops),
        "missing": sorted(EXPECTED_OPERATIONS - found_ops),
        "score": len(found_ops) / len(EXPECTED_OPERATIONS) * 100,
    }

    # Overall score (weighted)
    weights = {
        "tables": 15,
        "fields": 20,
        "fourgl_keywords": 20,
        "sql_similarity": 10,
        "fourgl_similarity": 10,
        "operations": 10,
    }
    total_weight = sum(weights.values())
    weighted_score = sum(
        scores[k]["score"] * w for k, w in weights.items()
    ) / total_weight
    scores["overall"] = {"score": round(weighted_score, 1)}

    return scores


def print_report(scores: dict, ref_cats: dict, gen_cats: dict):
    """Print a formatted comparison report."""
    print("\n" + "=" * 60)
    print("  .dat Comparison Report")
    print("=" * 60)

    print(f"\n  OVERALL SCORE: {scores['overall']['score']}%\n")

    for category, data in scores.items():
        if category == "overall":
            continue
        score = data["score"]
        bar = "#" * int(score / 5) + "-" * (20 - int(score / 5))
        print(f"  {category:25s} [{bar}] {score:5.1f}%")
        if "missing" in data and data["missing"]:
            print(f"    Missing: {', '.join(data['missing'][:10])}")

    # Stats
    print(f"\n  Reference: {len(ref_cats.get('sql', []))} SQL, "
          f"{len(ref_cats.get('fourgl', []))} 4GL, "
          f"{len(ref_cats.get('metadata', []))} metadata strings")
    print(f"  Generated: {len(gen_cats.get('sql', []))} SQL, "
          f"{len(gen_cats.get('fourgl', []))} 4GL, "
          f"{len(gen_cats.get('metadata', []))} metadata strings")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compare Sage 200 .dat files")
    parser.add_argument("reference", nargs="?", help="Reference .dat file")
    parser.add_argument("generated", nargs="?", help="Generated .dat file")
    parser.add_argument("--extract", help="Extract and display contents of a .dat file")
    parser.add_argument("--reference-only", action="store_true",
                        help="Analyze reference .dat from assets/")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output-dir", help="Save results to directory")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.extract:
        dat_path = Path(args.extract)
        if dat_path.suffix == ".zip":
            all_strings = extract_from_zip(dat_path)
            for fname, strings in all_strings.items():
                print(f"\n=== {fname} ({len(strings)} strings) ===")
                cats = classify_strings(strings)
                for cat, items in cats.items():
                    if items:
                        print(f"\n--- {cat} ({len(items)}) ---")
                        display = items[:50] if isinstance(items, list) else items
                        for item in display:
                            print(f"  {item}")
        else:
            strings = extract_strings(dat_path)
            cats = classify_strings(strings)
            for cat, items in cats.items():
                if items:
                    print(f"\n--- {cat} ({len(items)}) ---")
                    display = items[:100] if isinstance(items, list) else items
                    for item in display:
                        print(f"  {item}")
        return

    if args.reference_only:
        if not REFERENCE_ZIP.exists():
            print(f"Reference zip not found: {REFERENCE_ZIP}")
            sys.exit(1)

        print(f"Analyzing reference: {REFERENCE_ZIP}")
        all_strings = extract_from_zip(REFERENCE_ZIP)
        for fname, strings in all_strings.items():
            print(f"\n{'='*60}")
            print(f"  {fname}: {len(strings)} strings extracted")
            print(f"{'='*60}")
            cats = classify_strings(strings)
            print(f"  SQL statements: {len(cats['sql'])}")
            print(f"  4GL code lines: {len(cats['fourgl'])}")
            print(f"  Metadata: {len(cats['metadata'])}")
            print(f"  Tables: {cats['table_names']}")
            print(f"  Fields: {cats['field_names'][:20]}")
            print(f"  Queries: {cats['query_names']}")

            if args.json:
                result = {
                    "file": fname,
                    "string_count": len(strings),
                    "categories": {
                        k: v if isinstance(v, list) else list(v)
                        for k, v in cats.items()
                    }
                }
                out_path = RESULTS_DIR / f"reference_{fname}.json"
                out_path.write_text(json.dumps(result, indent=2))
                print(f"  Saved to: {out_path}")
        return

    # Full comparison
    if not args.reference or not args.generated:
        parser.print_help()
        sys.exit(1)

    ref_path = Path(args.reference)
    gen_path = Path(args.generated)

    # Extract strings
    if ref_path.suffix == ".zip":
        ref_all = extract_from_zip(ref_path)
        ref_strings = []
        for strings in ref_all.values():
            ref_strings.extend(strings)
    else:
        ref_strings = extract_strings(ref_path)

    if gen_path.suffix == ".zip":
        gen_all = extract_from_zip(gen_path)
        gen_strings = []
        for strings in gen_all.values():
            gen_strings.extend(strings)
    else:
        gen_strings = extract_strings(gen_path)

    # Classify
    ref_cats = classify_strings(ref_strings)
    gen_cats = classify_strings(gen_strings)

    # Compare
    scores = compare_categories(ref_cats, gen_cats)

    if args.json:
        output = {
            "reference": str(ref_path),
            "generated": str(gen_path),
            "scores": scores,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        if args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "comparison.json"
        else:
            out_path = RESULTS_DIR / "comparison.json"
        out_path.write_text(json.dumps(output, indent=2))
        print(f"Results saved to: {out_path}")
    else:
        print_report(scores, ref_cats, gen_cats)

    # Save detailed results
    out_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save diffs
    ref_sql = sorted(ref_cats.get("sql", []))
    gen_sql = sorted(gen_cats.get("sql", []))
    diff = list(unified_diff(ref_sql, gen_sql, fromfile="reference", tofile="generated", lineterm=""))
    if diff:
        (out_dir / "sql_diff.txt").write_text("\n".join(diff))

    ref_4gl = ref_cats.get("fourgl", [])
    gen_4gl = gen_cats.get("fourgl", [])
    diff = list(unified_diff(ref_4gl, gen_4gl, fromfile="reference", tofile="generated", lineterm=""))
    if diff:
        (out_dir / "fourgl_diff.txt").write_text("\n".join(diff))


if __name__ == "__main__":
    main()
