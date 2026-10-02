"""Intervalli di date (occupazioni dei luoghi, RF-01/RF-05)."""

from datetime import date


def ranges_overlap(
    a_from: date, a_to: date | None, b_from: date, b_to: date | None
) -> bool:
    """Date incluse; `None` come fine = intervallo aperto."""
    a_starts_before_b_ends = b_to is None or a_from <= b_to
    b_starts_before_a_ends = a_to is None or b_from <= a_to
    return a_starts_before_b_ends and b_starts_before_a_ends
