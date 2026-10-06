from backend.app.services.analytics_service import calculate_price_change


def test_price_change_basic():
    diff, percent = calculate_price_change(100.0, 80.0)
    assert diff == 20.0
    assert percent == 20.0


def test_zero_price_handling():
    diff, percent = calculate_price_change(0.0, 10.0)
    assert diff == 10.0
    assert percent == 0.0
