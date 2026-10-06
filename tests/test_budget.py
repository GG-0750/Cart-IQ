from backend.app.services.budget_service import compute_budget_summary


def test_budget_summary():
    summary = compute_budget_summary(total_budget=500.0, planned_cost=175.0)
    assert summary['remaining_budget'] == 325.0
    assert summary['budget_utilization'] == 35.0
