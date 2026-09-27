"""Run both eval suites, write the results file, and enforce the release gate.

Usage:
  python3 -m src.run_eval                   # real model if a key is set, else mock baseline
  python3 -m src.run_eval --mock            # force the deterministic no-LLM baseline
  python3 -m src.run_eval --require-model   # refuse to run without a model key (CI)

Where results go:
  model run (a key is set)  -> evals/RESULTS.md       (the recorded model run)
  mock / no key             -> evals/RESULTS.mock.md  (never touches RESULTS.md)

Exit codes:
  0  model run met every PRD target, or a mock run (the gate is not enforced on
     the baseline, which is meant to score low)
  1  model run missed a target: Suite A < 90%, checker recall < 90% or
     checker precision < 80%
  2  --require-model was given but no ANTHROPIC_API_KEY / OPENAI_API_KEY is set
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

# Release gate, from PRD section 3 (defined before build).
TARGET_SUITE_A = 0.90
TARGET_RECALL = 0.90
TARGET_PRECISION = 0.80


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


def gate_failures(a_rate, recall, precision):
    """Return the PRD targets this run missed. An empty list means the gate passes."""
    checks = [
        ("Suite A pass rate", a_rate, TARGET_SUITE_A),
        ("Checker recall", recall, TARGET_RECALL),
        ("Checker precision", precision, TARGET_PRECISION),
    ]
    return [
        f"{name} {value:.0%} is below the {target:.0%} target"
        for name, value, target in checks
        if value < target - 1e-9
    ]


def results_path(mode):
    """Mock runs never overwrite the recorded model run in evals/RESULTS.md."""
    name = "RESULTS.mock.md" if mode == "mock" else "RESULTS.md"
    return ROOT / "evals" / name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="force deterministic baseline")
    ap.add_argument(
        "--require-model", action="store_true",
        help="exit 2 instead of falling back to the mock baseline when no key is set (CI)",
    )
    args = ap.parse_args(argv)
    if args.mock:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)

    mode = llm.provider()
    if mode == "mock" and args.require_model:
        print(
            "ERROR: --require-model was given but neither ANTHROPIC_API_KEY nor "
            "OPENAI_API_KEY is set (or --mock was also given). Refusing to run, so "
            "baseline numbers are never recorded as a model run.",
            file=sys.stderr,
        )
        return 2

    model = {"anthropic": llm.ANTHROPIC_MODEL, "openai": llm.OPENAI_MODEL}.get(mode, "extractive baseline (no LLM)")
    cases, traps = load("cases.json"), load("traps.json")

    a_pass, a_rows = suite_a(cases)
    recall, precision, b_rows = suite_b(traps)
    a_rate = a_pass / len(cases)
    failures = gate_failures(a_rate, recall, precision)

    if mode == "mock":
        header = [
            "# Eval results: mock baseline",
            "",
            "**Synthetic: no-LLM extractive baseline on the synthetic cases (deterministic, not a model run).**",
            "",
            f"Mode: **{mode}** · Model: **{model}** · No run date: the output is identical on every run, "
            "so `python3 -m src.run_eval --mock` reproduces this file exactly.",
            "",
            "Release gate: **not enforced**. The baseline is the comparison point and is meant to score low; "
            "the recorded model run is in [RESULTS.md](RESULTS.md).",
        ]
    else:
        today = date.today().isoformat()
        verdict = "**PASS** (every target met)" if not failures else "**FAIL**: " + "; ".join(failures)
        header = [
            "# Eval results",
            "",
            f"**Recorded model run ({model}, {today})**",
            "",
            f"Run date: {today} · Mode: **{mode}** · Model: **{model}**",
            "",
            f"Release gate: {verdict}",
        ]

    lines = header + [
        "",
        "| Suite | Metric | Result | Target |",
        "|---|---|---|---|",
        f"| A. Summariser quality | Cases passing all checks | **{a_pass}/{len(cases)} ({a_rate:.0%})** | ≥ {TARGET_SUITE_A:.0%} |",
        f"| B. Checker quality | Hallucination recall | **{recall:.0%}** | ≥ {TARGET_RECALL:.0%} |",
        f"| B. Checker quality | Supported-claim precision | **{precision:.0%}** | ≥ {TARGET_PRECISION:.0%} |",
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

    out = results_path(mode)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[: len(header) + 6]))
    print(f"\nWrote {out}")

    if mode == "mock":
        print(
            "\nNote: mock mode is the no-LLM extractive baseline, so the release gate is not enforced "
            "and evals/RESULTS.md (the recorded model run) is left untouched. "
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY for a real run."
        )
        return 0
    if failures:
        print("\nRELEASE GATE: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nRELEASE GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
