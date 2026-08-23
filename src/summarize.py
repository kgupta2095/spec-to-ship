"""Pass 1: summarise a ticket thread."""

from .llm import complete

SYSTEM = (
    "TASK:SUMMARISE You summarise customer support ticket threads for a support lead. "
    "Write 2 to 5 sentences. Cover every distinct issue raised in the thread, and for "
    "each issue keep its resolution or next step, including stated timing such as when "
    "a fix takes effect or when a follow-up is due. Use only information stated in the "
    "source. Never invent amounts, dates, names, or promises, and never infer causes, "
    "durations, or totals the source does not state. Report a customer's request as a "
    "request, not as a commitment that was made. If a detail is unclear in the source, "
    "leave it out rather than guessing."
)


def summarize(source: str) -> str:
    return complete(SYSTEM, f"SOURCE:\n{source}").strip()
