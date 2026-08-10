"""Conservative annual salary parsing shared by ATS adapters."""

import math
import re
from typing import Any

_SALARY_LABEL = (
    r"(?:base\s+salary(?:\s+range)?|salary\s+range|salary|"
    r"base\s+pay|pay\s+range|compensation\s+range)"
)
_SALARY_HINT = re.compile(rf"\b{_SALARY_LABEL}\b", re.IGNORECASE)
_UNMARKED_SALARY_PREFIX = re.compile(
    rf"\b{_SALARY_LABEL}\b" r"\s*(?:(?:is|of|from|between)\s*)?[:=]?\s*$",
    re.IGNORECASE,
)
_NON_YEARLY_PAY = re.compile(
    r"\b(?:hourly|per\s+hour|an?\s+hour|daily|per\s+day|weekly|per\s+week|monthly|per\s+month)\b|/hr\b",
    re.IGNORECASE,
)
_CURRENCY = r"(?:USD|CAD|GBP|EUR|AUD|NZD|CHF|INR|PKR|[$£€₹])"
_SALARY_AMOUNT = r"(?:\d{1,3}(?:(?:\s*,\s*|\s+)\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_SALARY_RANGE = re.compile(
    rf"(?<![\w,.])(?P<currency_before_min>{_CURRENCY})?\s*"
    rf"(?P<minimum>{_SALARY_AMOUNT})\s*"
    r"(?P<minimum_suffix>[kKmM])?\s*"
    rf"(?P<currency_after_min>{_CURRENCY})?\s*"
    r"(?:-|–|—|to)\s*"
    rf"(?P<currency_before_max>{_CURRENCY})?\s*"
    rf"(?P<maximum>{_SALARY_AMOUNT})\s*"
    r"(?P<maximum_suffix>[kKmM])?\s*"
    rf"(?P<currency_after_max>{_CURRENCY})?(?![\w,])",
    re.IGNORECASE,
)


def parse_salary_amount(value: Any) -> int | None:
    """Normalize a structured ATS value for the annual integer columns."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 1_000:
        return None
    return round(value)


def _expanded_salary_amount(raw: str, suffix: str | None) -> int:
    amount = float(re.sub(r"[,\s]", "", raw))
    multiplier = {"k": 1_000, "m": 1_000_000}.get((suffix or "").lower(), 1)
    return round(amount * multiplier)


def extract_salary_range(
    text: str | None,
    *,
    require_salary_context: bool = True,
) -> tuple[int | None, int | None]:
    """Extract an explicit annual salary range without guessing unrelated numbers.

    Description parsing requires a nearby salary/pay phrase so years,
    experience ranges, discounts, and job IDs do not become compensation.
    ATS fields whose entire meaning is already salary can disable that check.
    """
    if not isinstance(text, str) or not text:
        return None, None

    for match in _SALARY_RANGE.finditer(text):
        context = text[max(0, match.start() - 100) : min(len(text), match.end() + 100)]
        if require_salary_context and _SALARY_HINT.search(context) is None:
            continue
        if _NON_YEARLY_PAY.search(context) is not None:
            continue

        minimum = _expanded_salary_amount(match.group("minimum"), match.group("minimum_suffix"))
        maximum = _expanded_salary_amount(match.group("maximum"), match.group("maximum_suffix"))
        has_money_marker = any(
            match.group(group)
            for group in (
                "currency_before_min",
                "currency_after_min",
                "currency_before_max",
                "currency_after_max",
                "minimum_suffix",
                "maximum_suffix",
            )
        )
        if not has_money_marker:
            prefix = text[max(0, match.start() - 80) : match.start()]
            if _UNMARKED_SALARY_PREFIX.search(prefix) is None:
                continue
        # The current schema treats stored values as annual amounts. Reject
        # hourly values and shorthand such as "₹3-₹6 LPA" rather than storing
        # numerically misleading annual ranges.
        if minimum < 1_000 or maximum < 1_000:
            continue
        return min(minimum, maximum), max(minimum, maximum)

    return None, None
