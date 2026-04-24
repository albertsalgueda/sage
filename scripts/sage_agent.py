#!/usr/bin/env python3
"""
Sage 200 End-to-End Agent: Spec -> .dat file.

Agentic workflow that:
1. Reads a functional spec
2. Calls Claude API to generate SQL + 4GL code
3. Injects SQL into the Sage database (tables, fields, queries, scripts)
4. Uses computer-use to create screens and reports in the Sage IDE
5. Uses computer-use to export .dat file
6. Downloads and compares with reference .dat

Usage:
    python sage_agent.py --host <IP> --password <VM_PW> --sql-password <SQL_PW>
    python sage_agent.py --step generate    # Only generate code (no VM needed)
    python sage_agent.py --step inject      # Only run SQL injection
    python sage_agent.py --step screens     # Only create screens via computer-use
    python sage_agent.py --step export      # Only export .dat
    python sage_agent.py --step compare     # Only compare .dat files
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Paths
SAGE_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SAGE_DIR / "scripts"
REFERENCE_DIR = SAGE_DIR / "reference"
RESULTS_DIR = SAGE_DIR / "results" / "experiment1_reloaded"
ASSETS_DIR = SAGE_DIR.parent / "assets"

# Import sibling scripts
sys.path.insert(0, str(SCRIPTS_DIR))


def ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


# ---------------------------------------------------------------------------
# Step 1: Generate SQL + 4GL from functional spec
# ---------------------------------------------------------------------------

def step_generate(spec_path: str = None, model: str = "claude-sonnet-4-20250514") -> dict:
    """Call Claude API to generate SQL + 4GL from a functional specification."""
    import anthropic

    if spec_path is None:
        spec_path = str(REFERENCE_DIR / "prompt_certificacion.md")

    spec = Path(spec_path).read_text()

    # Load system prompt (FULL_CONTEXT from test_code_generation_v2.py)
    from system_prompts import FULL_CONTEXT
    system_prompt = FULL_CONTEXT

    client = anthropic.Anthropic()

    print(f"  Generating code with {model}...")
    start = time.time()

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Generate the complete Sage 200 solution for this specification:\n\n{spec}"
        }]
    )

    elapsed = time.time() - start
    output = response.content[0].text

    result = {
        "model": model,
        "elapsed_seconds": round(elapsed, 1),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "output": output,
        "cost_estimate": _estimate_cost(model, response.usage),
    }

    # Save output
    out_dir = ensure_results_dir()
    (out_dir / "generated_code.md").write_text(output)
    (out_dir / "generation_metadata.json").write_text(json.dumps(result, indent=2, default=str))

    print(f"  Generated {len(output)} chars in {elapsed:.1f}s")
    print(f"  Cost: ~${result['cost_estimate']:.2f}")
    print(f"  Saved to: {out_dir / 'generated_code.md'}")

    return result


def _estimate_cost(model: str, usage) -> float:
    """Estimate API cost based on model and token usage."""
    rates = {
        "claude-sonnet-4-20250514": (3.0, 15.0),    # per 1M tokens
        "claude-opus-4-20250514": (15.0, 75.0),
    }
    input_rate, output_rate = rates.get(model, (3.0, 15.0))
    return (usage.input_tokens * input_rate + usage.output_tokens * output_rate) / 1_000_000


# ---------------------------------------------------------------------------
# Step 2: SQL Injection (tables, fields, queries, scripts)
# ---------------------------------------------------------------------------

def step_inject(host: str, sql_password: str, db: str = "Sage"):
    """Inject SQL objects into the Sage database."""
    from sql_injection_test import get_all_sql, execute_via_ssh, SQL_VERIFY

    print("  Injecting SQL objects...")
    sql = get_all_sql()
    print(f"  Total SQL: {len(sql)} chars")

    success = execute_via_ssh(host, sql, db, "sa", sql_password)
    if not success:
        print("  ERROR: SQL injection failed")
        return False

    print("\n  Verifying injection...")
    execute_via_ssh(host, SQL_VERIFY, db, "sa", sql_password)
    return True


# ---------------------------------------------------------------------------
# Step 3: Create screens via computer-use
# ---------------------------------------------------------------------------

def step_screens(host: str, vm_password: str):
    """Create Sage screens using computer-use (SSH+PowerShell approach)."""
    from computer_use_ssh import SSHController, run_computer_use_loop

    controller = SSHController(host)

    # Task: Create CF_Equipos screen
    task_equipos = (
        "In the Sage 200 Consola de Administracion, create a new screen (pantalla) "
        "called CF_Equipos with data source CF_Equipos. Add these controls:\n"
        "- txtCF_CodigoEquipo (label: 'Cod. Equipo')\n"
        "- txtCF_Nombre (label: 'Nombre Equipo')\n"
        "- txtCF_JuegaEuropa (label: 'Juega en Europa', type: checkbox)\n"
        "- txtCF_Competicion (label: 'Competicion', type: list of values: "
        "'Vacio;Europa League;Champions League')\n"
        "- grdDataForm grid with all fields\n"
        "Save the screen."
    )

    # Task: Create CF_Resultados screen
    task_resultados = (
        "In the Sage 200 Consola de Administracion, create a new screen (pantalla) "
        "called CF_Resultados with data source CF_Resultados. Add these controls:\n"
        "- txtCF_Jornada (label: 'Jornada')\n"
        "- txtCF_EquipoLocal (label: 'Local', with relation to CF_Equipos showing CF_Nombre)\n"
        "- txtCF_GolesLocal (label: 'Goles Local', default: 0)\n"
        "- txtCF_EquipoVisitante (label: 'Visitante', with relation to CF_Equipos showing CF_Nombre)\n"
        "- txtCF_GolesVisitante (label: 'Goles Visitante', default: 0)\n"
        "- txtCF_Fecha (label: 'Fecha', default: NOW)\n"
        "- grdDataForm grid with all fields\n"
        "Save the screen."
    )

    screens = [
        ("CF_Equipos", task_equipos),
        ("CF_Resultados", task_resultados),
    ]

    out_dir = ensure_results_dir()
    for name, task in screens:
        print(f"\n  Creating screen: {name}")
        try:
            result = run_computer_use_loop(
                controller=controller,
                task=task,
                max_steps=30,
                model="claude-sonnet-4-20250514",
            )
            (out_dir / f"screen_{name}_log.json").write_text(
                json.dumps(result, indent=2, default=str)
            )
            print(f"  Screen {name}: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"  ERROR creating screen {name}: {e}")


# ---------------------------------------------------------------------------
# Step 4: Export .dat file via computer-use
# ---------------------------------------------------------------------------

def step_export(host: str, vm_password: str):
    """Export CF_* objects as .dat file using computer-use."""
    from computer_use_ssh import SSHController, run_computer_use_loop

    controller = SSHController(host)

    task = (
        "In the Sage 200 Consola de Administracion:\n"
        "1. Go to Herramientas > Exportar Objetos de Repositorio\n"
        "2. Select all objects with prefix CF_ (tables, screens, queries, "
        "calculations, reports, operations)\n"
        "3. Export them as a .dat file to C:\\export\\CF_generated.dat\n"
        "4. Confirm the export is complete"
    )

    print("  Exporting .dat file via computer-use...")
    out_dir = ensure_results_dir()
    try:
        result = run_computer_use_loop(
            controller=controller,
            task=task,
            max_steps=20,
            model="claude-sonnet-4-20250514",
        )
        (out_dir / "export_log.json").write_text(
            json.dumps(result, indent=2, default=str)
        )
        print(f"  Export: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"  ERROR during export: {e}")
        return False

    # Download .dat file
    ssh_key = Path.home() / ".ssh" / "google_compute_engine"
    scp_cmd = [
        "scp", "-i", str(ssh_key), "-o", "StrictHostKeyChecking=no",
        f"albert@{host}:C:/export/CF_generated.dat",
        str(out_dir / "CF_generated.dat"),
    ]
    print("  Downloading .dat file...")
    r = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        print(f"  Downloaded to: {out_dir / 'CF_generated.dat'}")
        return True
    else:
        print(f"  Download failed: {r.stderr}")
        return False


# ---------------------------------------------------------------------------
# Step 5: Compare generated .dat with reference
# ---------------------------------------------------------------------------

def step_compare():
    """Compare generated .dat with reference .dat."""
    from compare_dat import (
        extract_strings, extract_from_zip, classify_strings,
        compare_categories, print_report
    )

    out_dir = ensure_results_dir()
    gen_dat = out_dir / "CF_generated.dat"
    ref_zip = ASSETS_DIR / "knowledge" / "Cert_JaviCoboHAvanzada.zip"

    if not gen_dat.exists():
        print(f"  Generated .dat not found: {gen_dat}")
        print("  Run --step export first")
        return None

    if not ref_zip.exists():
        print(f"  Reference zip not found: {ref_zip}")
        return None

    # Extract
    gen_strings = extract_strings(gen_dat)
    ref_all = extract_from_zip(ref_zip)
    ref_strings = []
    for strings in ref_all.values():
        ref_strings.extend(strings)

    # Classify
    gen_cats = classify_strings(gen_strings)
    ref_cats = classify_strings(ref_strings)

    # Compare
    scores = compare_categories(ref_cats, gen_cats)
    print_report(scores, ref_cats, gen_cats)

    # Save
    result = {
        "scores": scores,
        "timestamp": datetime.now().isoformat(),
        "reference": str(ref_zip),
        "generated": str(gen_dat),
    }
    (out_dir / "comparison_result.json").write_text(
        json.dumps(result, indent=2, default=str)
    )

    return scores


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_full_pipeline(host: str, vm_password: str, sql_password: str,
                      model: str = "claude-sonnet-4-20250514"):
    """Run the complete end-to-end pipeline."""
    out_dir = ensure_results_dir()
    start = time.time()

    results = {
        "timestamp": datetime.now().isoformat(),
        "host": host,
        "model": model,
        "steps": {},
    }

    # Step 1: Generate
    print("\n" + "=" * 60)
    print("  STEP 1: Generate SQL + 4GL from spec")
    print("=" * 60)
    try:
        gen_result = step_generate(model=model)
        results["steps"]["generate"] = {
            "status": "success",
            "elapsed": gen_result["elapsed_seconds"],
            "cost": gen_result["cost_estimate"],
        }
    except Exception as e:
        print(f"  FAILED: {e}")
        results["steps"]["generate"] = {"status": "failed", "error": str(e)}

    # Step 2: Inject SQL
    print("\n" + "=" * 60)
    print("  STEP 2: Inject SQL objects into Sage database")
    print("=" * 60)
    try:
        success = step_inject(host, sql_password)
        results["steps"]["inject"] = {"status": "success" if success else "failed"}
    except Exception as e:
        print(f"  FAILED: {e}")
        results["steps"]["inject"] = {"status": "failed", "error": str(e)}

    # Step 3: Create screens
    print("\n" + "=" * 60)
    print("  STEP 3: Create screens via computer-use")
    print("=" * 60)
    try:
        step_screens(host, vm_password)
        results["steps"]["screens"] = {"status": "attempted"}
    except Exception as e:
        print(f"  FAILED: {e}")
        results["steps"]["screens"] = {"status": "failed", "error": str(e)}

    # Step 4: Export .dat
    print("\n" + "=" * 60)
    print("  STEP 4: Export .dat file")
    print("=" * 60)
    try:
        success = step_export(host, vm_password)
        results["steps"]["export"] = {"status": "success" if success else "failed"}
    except Exception as e:
        print(f"  FAILED: {e}")
        results["steps"]["export"] = {"status": "failed", "error": str(e)}

    # Step 5: Compare
    print("\n" + "=" * 60)
    print("  STEP 5: Compare .dat files")
    print("=" * 60)
    try:
        scores = step_compare()
        if scores:
            results["steps"]["compare"] = {
                "status": "success",
                "overall_score": scores["overall"]["score"],
            }
        else:
            results["steps"]["compare"] = {"status": "skipped"}
    except Exception as e:
        print(f"  FAILED: {e}")
        results["steps"]["compare"] = {"status": "failed", "error": str(e)}

    elapsed = time.time() - start
    results["total_elapsed_seconds"] = round(elapsed, 1)

    # Save pipeline results
    (out_dir / "pipeline_result.json").write_text(
        json.dumps(results, indent=2, default=str)
    )

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    for step, data in results["steps"].items():
        status = data.get("status", "unknown")
        icon = "OK" if status == "success" else "FAIL" if status == "failed" else "??"
        print(f"  [{icon}] {step}: {status}")
    print(f"\n  Total time: {elapsed:.1f}s")
    print(f"  Results: {out_dir}")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sage 200 End-to-End Agent")
    parser.add_argument("--host", help="GCP host IP")
    parser.add_argument("--password", help="Sage VM password")
    parser.add_argument("--sql-password", help="SQL Server SA password")
    parser.add_argument("--db", default="Sage")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Claude model for code generation")
    parser.add_argument("--step", choices=["generate", "inject", "screens", "export", "compare"],
                        help="Run only a specific step")
    parser.add_argument("--spec", help="Path to functional spec file")
    args = parser.parse_args()

    print(f"=== Sage 200 End-to-End Agent ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Model: {args.model}")
    print()

    if args.step == "generate":
        step_generate(spec_path=args.spec, model=args.model)
    elif args.step == "inject":
        if not args.host or not args.sql_password:
            print("ERROR: --host and --sql-password required for inject step")
            sys.exit(1)
        step_inject(args.host, args.sql_password, args.db)
    elif args.step == "screens":
        if not args.host or not args.password:
            print("ERROR: --host and --password required for screens step")
            sys.exit(1)
        step_screens(args.host, args.password)
    elif args.step == "export":
        if not args.host or not args.password:
            print("ERROR: --host and --password required for export step")
            sys.exit(1)
        step_export(args.host, args.password)
    elif args.step == "compare":
        step_compare()
    else:
        # Full pipeline
        if not args.host:
            print("ERROR: --host required for full pipeline (or use --step generate)")
            sys.exit(1)
        run_full_pipeline(
            host=args.host,
            vm_password=args.password or "",
            sql_password=args.sql_password or "",
            model=args.model,
        )


if __name__ == "__main__":
    main()
