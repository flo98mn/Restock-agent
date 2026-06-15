#!/usr/bin/env python3
"""
run_pipeline.py — orchestrator determinist al pipeline-ului Restock-agent v1.

Lanțuiește cei 3 pași ca subprocese, în ordine, oprind la prima eroare:
    stock-analyst -> restock-planner -> report-writer

Pur orchestrare: NU reimplementează logica pașilor, NU calculează nimic, NU atinge sursa,
fără rețea/DB. Folosește sys.executable ca să meargă identic pe Windows și altundeva.
"""

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def run_step(n, script, extra_args):
    cmd = [sys.executable, str(SCRIPTS / script)] + list(extra_args)
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # Streamuiește sumarul pasului către user
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if proc.returncode != 0:
        print("PIPELINE OPRIT la pasul " + str(n) + " (" + script + ")")
        if proc.stderr:
            sys.stderr.write(proc.stderr)
            if not proc.stderr.endswith("\n"):
                sys.stderr.write("\n")
        sys.exit(proc.returncode)
    # stderr pe succes (avertismente eventuale)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    print("[OK] pasul " + str(n) + ": " + script)


def main():
    ap = argparse.ArgumentParser(description="Restock-agent: orchestrator pipeline v1.")
    ap.add_argument("--report", help="cale către un xlsx anume (pass-through la stock_analyst)")
    args = ap.parse_args()

    analyst_args = []
    if args.report:
        analyst_args = ["--report", args.report]

    run_step(1, "stock_analyst.py", analyst_args)
    run_step(2, "restock_planner.py", [])
    run_step(3, "report_writer.py", [])

    # Localizează cel mai recent output
    out_dir = REPO_ROOT / "output" / "stock_reports"
    candidates = glob.glob(str(out_dir / "Stoc_viitor_completat_*.xlsx"))
    if not candidates:
        print("EROARE: niciun output Stoc_viitor_completat_*.xlsx în " + str(out_dir))
        sys.exit(1)
    latest = max(candidates, key=os.path.getmtime)
    print("PIPELINE COMPLET. Output: " + str(Path(latest).resolve()))


if __name__ == "__main__":
    main()
