"""Minimal LLM client. Uses Anthropic or OpenAI depending on which key is set.

Modes:
  - real: ANTHROPIC_API_KEY or OPENAI_API_KEY present
  - mock: no key or --mock flag; deterministic extractive baseline so the
    pipeline and evals run without network access (also used in CI)
"""

import json
import os
import re
import urllib.request

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_MODEL = os.environ.get("MODEL", "claude-sonnet-4-5")
OPENAI_MODEL = os.environ.get("MODEL", "gpt-4o-mini")


def provider():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "mock"


def _post(url, headers, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def complete(system, user, max_tokens=700):
    """Return model text for a system+user prompt, or a mock completion."""
    p = provider()
    if p == "anthropic":
        out = _post(
            ANTHROPIC_URL,
            {
                "content-type": "application/json",
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
            },
            {
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        return out["content"][0]["text"]
    if p == "openai":
        out = _post(
            OPENAI_URL,
            {
                "content-type": "application/json",
                "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            },
            {
                "model": OPENAI_MODEL,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        return out["choices"][0]["message"]["content"]
    return _mock(system, user)


# ---------------- mock baseline (no network) ----------------

def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _mock(system, user):
    """Deterministic extractive behaviour keyed off the task marker in the prompt."""
    if "TASK:SUMMARISE" in system:
        src = user.split("SOURCE:\n", 1)[-1]
        sents = sentences(src)
        return " ".join(sents[:3])
    if "TASK:EXTRACT_CLAIMS" in system:
        summ = user.split("SUMMARY:\n", 1)[-1]
        return json.dumps(sentences(summ))
    if "TASK:VERIFY" in system:
        src = user.split("SOURCE:\n", 1)[-1].split("\nCLAIM:", 1)[0].lower()
        claim = user.split("CLAIM:\n", 1)[-1].lower()
        toks = [t for t in re.findall(r"[a-z0-9$%]+", claim) if len(t) > 3]
        if not toks:
            return "SUPPORTED"
        hit = sum(1 for t in toks if t in src)
        return "SUPPORTED" if hit / len(toks) >= 0.6 else "UNSUPPORTED"
    return ""
