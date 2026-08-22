"""Pass 2: the guardrail. Extract claims from a summary and verify each against the source.

A summary with any UNSUPPORTED claim is blocked (never shown to a user).
"""

import json

from .llm import complete, sentences

EXTRACT_SYSTEM = (
    "TASK:EXTRACT_CLAIMS Split the summary into individual factual claims. "
    "Return a JSON array of strings, one claim per element, nothing else."
)

VERIFY_SYSTEM = (
    "TASK:VERIFY You are a strict fact checker. Decide whether the CLAIM is directly "
    "supported by the SOURCE text. Paraphrase counts as supported; any detail not "
    "present in the source (amounts, dates, promises, causes) makes it unsupported. "
    "Answer with exactly one word: SUPPORTED or UNSUPPORTED."
)


def extract_claims(summary: str):
    raw = complete(EXTRACT_SYSTEM, f"SUMMARY:\n{summary}")
    try:
        start, end = raw.index("["), raw.rindex("]") + 1
        claims = json.loads(raw[start:end])
        claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]
        return claims if claims else sentences(summary)
    except (ValueError, json.JSONDecodeError):
        return sentences(summary)  # fallback: sentence-level claims


def verify_claim(source: str, claim: str) -> bool:
    verdict = complete(VERIFY_SYSTEM, f"SOURCE:\n{source}\nCLAIM:\n{claim}", max_tokens=10)
    return "UNSUPPORTED" not in verdict.upper()


def ground_check(source: str, summary: str):
    """Return (passed, results) where results is a list of (claim, supported)."""
    results = [(c, verify_claim(source, c)) for c in extract_claims(summary)]
    passed = all(ok for _, ok in results)
    return passed, results
