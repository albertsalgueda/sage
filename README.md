# Sage 200 AI Audit

Scripts to test if AI can automate Sage 200 development workflows.

## Setup

```bash
cp .env.example .env        # Fill in your API key and VM details
pip install -r requirements.txt
```

## Experiment 1: Code Generation (no VM needed)

Tests if Claude can generate valid SQL, 4GL scripts, and queries from a functional spec.

```bash
python scripts/test_code_generation.py                    # Run with Claude Sonnet
python scripts/test_code_generation.py --model claude-opus-4-20250514  # Try with Opus
python scripts/test_code_generation.py --skip-api          # Re-evaluate last output
```

Results saved to `results/` (generated output, evaluation JSON, diff).

## Experiment 2: Computer-Use (needs VM)

Controls the Sage 200 VM via VNC using Anthropic's computer-use API.

```bash
python scripts/computer_use_sage.py --dry-run              # Check config
python scripts/computer_use_sage.py --screenshot            # Take a screenshot
python scripts/computer_use_sage.py --demo                  # Navigate to Admin Console
python scripts/computer_use_sage.py --task "Create table CF_Equipos"  # Custom task
```

## Reference Files

- `reference/prompt_certificacion.md` — Functional spec (input)
- `reference/solution_dat_extract.md` — Expected solution (comparison target)
