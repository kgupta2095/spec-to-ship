"""Pass 1: summarise a ticket thread."""

from .llm import complete

SYSTEM = (
    "TASK:SUMMARISE You summarise customer support ticket threads for a support lead. "
    "Write 2 to 4 sentences. Use only information stated in the source. "
    "Never invent amounts, dates, names, or promises. If a detail is unclear in the "
    "source, leave it out rather than guessing."
)


def summarize(source: str) -> str:
    return complete(SYSTEM, f"SOURCE:\n{source}").strip()
