from __future__ import annotations


def compute_budget_summary(total_budget: float, planned_cost: float) -> dict:
    total_budget = float(total_budget or 0)
    planned_cost = float(planned_cost or 0)
    remaining_budget = total_budget - planned_cost
    utilization = 0.0
    if total_budget > 0:
        utilization = (planned_cost / total_budget) * 100.0
    return {
        'total_budget': total_budget,
        'planned_cost': planned_cost,
        'remaining_budget': remaining_budget,
        'budget_utilization': round(utilization, 2),
    }
