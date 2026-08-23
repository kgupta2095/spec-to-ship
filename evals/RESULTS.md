# Eval results

Run date: 2026-08-23 · Mode: **anthropic** · Model: **claude-sonnet-4-5**

| Suite | Metric | Result | Target |
|---|---|---|---|
| A. Summariser quality | Cases passing all checks | **16/16 (100%)** | ≥ 90% |
| B. Checker quality | Hallucination recall | **100%** | ≥ 90% |
| B. Checker quality | Supported-claim precision | **100%** | ≥ 80% |

## Suite A detail

| Case | Title | Pass | Failure notes |
|---|---|---|---|
| S01 | Billing dispute, double charge | ✅ |  |
| S02 | Login failure after password reset | ✅ |  |
| S03 | Feature request, CSV export | ✅ |  |
| S04 | Escalation, angry tone | ✅ |  |
| S05 | Multi-issue thread | ✅ |  |
| S06 | Contradictory information | ✅ |  |
| S07 | Outage report | ✅ |  |
| S08 | Plan downgrade request | ✅ |  |
| S09 | API rate limit confusion | ✅ |  |
| S10 | Refund approved case | ✅ |  |
| S11 | Data privacy question | ✅ |  |
| S12 | Mobile app crash | ✅ |  |
| S13 | Onboarding stalled | ✅ |  |
| S14 | Security concern report | ✅ |  |
| S15 | Pricing clarification | ✅ |  |
| S16 | Integration failure | ✅ |  |

## Suite B detail

| Trap | Planted claims caught | Good claims kept |
|---|---|---|
| T01 | 1/1 | 1/1 |
| T02 | 1/1 | 1/1 |
| T03 | 1/1 | 1/1 |
| T04 | 1/1 | 1/1 |
| T05 | 2/2 | 1/1 |
| T06 | 1/1 | 1/1 |
