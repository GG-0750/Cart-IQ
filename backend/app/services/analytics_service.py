from __future__ import annotations

from typing import Any


def calculate_price_change(previous_price: float | None, current_price: float | None) -> tuple[float, float]:
    previous = float(previous_price or 0.0)
    current = float(current_price or 0.0)

    delta = abs(current - previous)
    percent = 0.0
    if previous > 0 and current < previous:
        percent = ((previous - current) / previous) * 100.0
    return delta, percent
