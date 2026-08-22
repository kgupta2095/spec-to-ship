# Eval results

Run date: 2026-08-22 · Mode: **mock** · Model: **extractive baseline (no LLM)**

| Suite | Metric | Result | Target |
|---|---|---|---|
| A. Summariser quality | Cases passing all checks | **5/16 (31%)** | ≥ 90% |
| B. Checker quality | Hallucination recall | **86%** | ≥ 90% |
| B. Checker quality | Supported-claim precision | **100%** | ≥ 80% |

## Suite A detail

| Case | Title | Pass | Failure notes |
|---|---|---|---|
| S01 | Billing dispute, double charge | ❌ | missing: payments team |
| S02 | Login failure after password reset | ❌ | missing: identity team |
| S03 | Feature request, CSV export | ❌ | missing: no commit |
| S04 | Escalation, angry tone | ❌ | missing: update by end of day |
| S05 | Multi-issue thread | ✅ |  |
| S06 | Contradictory information | ✅ |  |
| S07 | Outage report | ❌ | missing: root cause |
| S08 | Plan downgrade request | ❌ | missing: 30 June; confirmation |
| S09 | API rate limit confusion | ❌ | missing: batching |
| S10 | Refund approved case | ❌ | missing: 5 to 7 business days |
| S11 | Data privacy question | ✅ |  |
| S12 | Mobile app crash | ❌ | missing: 5.2.1; App Store; web app |
| S13 | Onboarding stalled | ❌ | missing: July |
| S14 | Security concern report | ✅ |  |
| S15 | Pricing clarification | ✅ |  |
| S16 | Integration failure | ❌ | missing: waiting |

## Suite B detail

| Trap | Planted claims caught | Good claims kept |
|---|---|---|
| T01 | 1/1 | 1/1 |
| T02 | 1/1 | 1/1 |
| T03 | 0/1 | 1/1 |
| T04 | 1/1 | 1/1 |
| T05 | 2/2 | 1/1 |
| T06 | 1/1 | 1/1 |
