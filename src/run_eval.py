"""Run both eval suites and write evals/RESULTS.md.

Usage:
  python -m src.run_eval          # real model if a key is set, else mock baseline
  python -m src.run_eval --mock   # force the deterministic baseline
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import llm
from .groundcheck import ground_check, verify_claim
from .summarize import summarize

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "evals" / name).read_text())


def contains_any(text, alternatives):
    t = text.lower()
    return any(a.lower() in t for a in alternatives)


def suite_a(cases):
    rows, passed = [], 0
    for c in cases:
        summary = summarize(c["source"])
        missing = [alts[0] for alts in c["must_include"] if not contains_any(summary, alts)]
        bait_hits = [b for b in c["bait"] if b.lower() in summary.lower()]
        grounded, claim_results = ground_check(c["source"], summary)
        unsupported = [cl for cl, ok in claim_results if not ok]
        ok = not missing and not bait_hits and not unsupported
        passed += ok
        rows.append({
            "id": c["id"], "title": c["title"], "pass": ok,
            "missing": missing, "bait": bait_hits, "unsupported": unsupported,
        })
    return passed, rows


def suite_b(traps):
    caught = total_bad = kept = total_good = 0
    rows = []
    for t in traps:
        bad_flagged = [cl for cl in t["unsupported_claims"] if not verify_claim(t["source"], cl)]
        good_kept = [cl for cl in t["supported_claims"] if verify_claim(t["source"], cl)]
        caught += len(bad_flagged); total_bad += len(t["unsupported_claims"])
        kept += len(good_kept); total_good += len(t["supported_claims"])
        rows.append({
            "id": t["id"],
            "caught": f"{len(bad_flagged)}/{len(t['unsupported_claims'])}",
            "kept": f"{len(good_kept)}/{len(t['supported_claims'])}",
        })
    recall = caught / total_bad if total_bad else 0.0
    precision = kept / total_good if total_good else 0.0
    return recall, precision, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="force deterministic baseline")
    args = ap.parse_args()
    if args.mock:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)

    mode = llm.provider()
    model = {"anthropic": llm.ANTHROPIC_MODEL, "openai": llm.OPENAI_MODEL}.get(mode, "extractive baseline (no LLM)")
    cases, traps = load("cases.json"), load("traps.json")

    a_pass, a_rows = suite_a(cases)
    recall, precision, b_rows = suite_b(traps)
    a_rate = a_pass / len(cases)

    lines = [
        "# Eval results",
        "",
        f"Run date: {date.today().isoformat()} · Mode: **{mode}** · Model: **{model}**",
        "",
        "| Suite | Metric | Result | Target |",
        "|---|---|---|---|",
        f"| A. Summariser quality | Cases passing all checks | **{a_pass}/{len(cases)} ({a_rate:.0%})** | ≥ 90% |",
        f"| B. Checker quality | Hallucination recall | **{recall:.0%}** | ≥ 90% |",
        f"| B. Checker quality | Supported-claim precision | **{precision:.0%}** | ≥ 80% |",
        "",
        "## Suite A detail",
        "",
        "| Case | Title | Pass | Failure notes |",
        "|---|---|---|---|",
    ]
    for r in a_rows:
        notes = []
        if r["missing"]:
            notes.append("missing: " + "; ".join(r["missing"]))
        if r["bait"]:
            notes.append("bait present: " + "; ".join(r["bait"]))
        if r["unsupported"]:
            notes.append(f"{len(r['unsupported'])} unsupported claim(s)")
        lines.append(f"| {r['id']} | {r['title']} | {'✅' if r['pass'] else '❌'} | {' · '.join(notes) or ''} |")

    lines += ["", "## Suite B detail", "", "| Trap | Planted claims caught | Good claims kept |", "|---|---|---|"]
    for r in b_rows:
        lines.append(f"| {r['id']} | {r['caught']} | {r['kept']} |")
    lines.append("")

    out = ROOT / "evals" / "RESULTS.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines[:10]))
    print(f"\nWrote {out}")
    if mode == "mock":
        print("\nNote: mock mode is the no-LLM extractive baseline. Set ANTHROPIC_API_KEY or OPENAI_API_KEY for a real run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
