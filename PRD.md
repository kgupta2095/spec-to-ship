# PRD: Grounded Ticket Summariser

**Author:** Karan Gupta · **Status:** Shipped (v1) · **Doc type:** Product spec with eval plan

## 1. Problem

Support leads and product managers triage long, messy ticket threads every day. Manual reading does not scale, but naive LLM summaries have a failure mode that is worse than no summary: they invent details (amounts, dates, promises) that were never in the thread. In a support context, an invented "refund was approved" is a customer-facing incident, not a typo.

The product question is not "can we summarise?" (solved) but "can we summarise with a near-zero rate of unsupported claims, and prove it?"

## 2. Users and jobs

- **Support lead:** wants a 3-line summary per thread to route and prioritise without reading 40 messages.
- **PM:** wants aggregated, trustworthy summaries as an input to roadmap decisions.
- **Non-goal:** replying to customers automatically. This tool summarises; it does not act.

## 3. Success metrics (defined before build)

| Metric | Target | How measured |
|---|---|---|
| Summariser eval pass rate | ≥ 90% | Eval suite A, all checks pass per case |
| Unsupported claims in shipped summaries | 0 | Groundedness gate blocks release of any summary with an unsupported claim |
| Checker recall on planted hallucinations | ≥ 90% | Eval suite B (fixture summaries with known-bad claims) |
| Checker precision on known-good claims | ≥ 80% | Eval suite B (known-good claims not falsely flagged) |

## 4. Solution overview

Two-pass architecture:

1. **Summarise:** the model produces a 2–4 sentence summary of the source thread.
2. **Ground-check (the guardrail):** a second pass extracts each claim from the summary and verifies it against the source. Any claim that cannot be supported by the source text marks the summary as blocked. Blocked summaries are never shown; the system falls back to "summary unavailable, read thread" rather than showing unverified content.

The check is the product. A summary that cannot pass its own audit does not ship.

## 5. Eval plan

Two suites, both runnable with one command, results written to `evals/RESULTS.md`.

- **Suite A, summariser quality (16 cases):** synthetic ticket threads covering billing disputes, login failures, feature requests, escalations, multi-issue threads, and contradictory information. Each case defines: facts the summary must include (with accepted alternatives), and bait, plausible details deliberately absent from the source (amounts, dates, promises). A case passes when all required facts are present, no bait appears, and the ground-check finds zero unsupported claims.
- **Suite B, checker quality (6 trap cases):** fixture summaries with labelled unsupported claims planted next to labelled supported ones. Measures whether the guardrail actually catches hallucinations (recall) without flagging good claims (precision).

Suite B exists because an unmeasured guardrail is a decorative one.

## 6. Guardrails and failure behaviour

- Ground-check gate: if any unsupported claim is found, the summary is blocked and never shown.
- Fallback: on model error or low-confidence verification, degrade to "no summary" rather than best-guess.
- Human in the loop: blocked summaries are queued for human review, not silently discarded.

## 7. Rollout

1. Mock mode (no API): deterministic extractive baseline, validates pipeline and evals in CI.
2. Model mode behind the eval gate: release only when Suite A ≥ 90% and Suite B recall ≥ 90%.
3. Shadow period: summaries generated but only shown to reviewers, comparing block rate against targets.

## 8. Out of scope for v1

Multi-language threads, streaming summarisation, auto-actions from summaries, UI.
