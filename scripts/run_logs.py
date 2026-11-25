"""Run an answer key's files through the CLI in order and keep each run's console output and transcript in docs/runs."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.scorecard import ANSWER_KEYS, load_answer_key  # noqa: E402
from invoice_agents.observability import RUNS_DIR  # noqa: E402

DOCS = ROOT / "docs" / "runs"


def run_cli(file: str, db: Path) -> tuple[str, Path | None]:
    """Process one file through the brief's command; returns the console output and the new run folder."""
    before = set((ROOT / RUNS_DIR).glob("*"))
    env = {**os.environ, "COLUMNS": "100"}
    result = subprocess.run([sys.executable, "main.py", "--db", str(db), f"--invoice_path={file}"], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=900)
    new = sorted(set((ROOT / RUNS_DIR).glob("*")) - before)
    return result.stdout + result.stderr, (new[-1] if new else None)


def main() -> int:
    """Write docs/runs/<tier>/<file>.txt for each file; the live tier also keeps report.md as the transcript."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=list(ANSWER_KEYS))
    parser.add_argument("tier", choices=["live", "replay", "alone"],
                        help="live and replay share one ledger in answer-key order; alone runs each file on its own")
    args = parser.parse_args()
    out = DOCS / args.tier
    with tempfile.TemporaryDirectory() as tmp:
        for file in load_answer_key(ANSWER_KEYS[args.set]):
            db = Path(tmp) / (f"{Path(file).name}.db" if args.tier == "alone" else "ledger.db")
            text, run = run_cli(file, db)
            name = Path(file).name
            print(f"{name}: {text.strip().splitlines()[-1] if text.strip() else 'no output'}", flush=True)
            if args.tier == "alone":
                continue
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.txt").write_text(text)
            if args.tier == "live" and run:
                (DOCS / "reports").mkdir(parents=True, exist_ok=True)
                shutil.copy(run / "report.md", DOCS / "reports" / f"{name}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
