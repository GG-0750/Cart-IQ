import pandas as pd

from backend.app.services import data_service


def alternatives_events():
    return pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'selected', 'category_id': 'category-a', 'category_code': 'electronics.phone', 'brand': 'brand-a', 'price': 100.0, 'user_session': 'session-1'},
        {'event_time': '2019-10-01T00:01:00', 'event_type': 'purchase', 'product_id': 'selected', 'category_id': 'category-a', 'category_code': 'electronics.phone', 'brand': 'brand-a', 'price': 90.0, 'user_session': 'session-2'},
        {'event_time': '2019-10-01T00:02:00', 'event_type': 'view', 'product_id': 'cheaper', 'category_id': 'category-a', 'category_code': 'electronics.phone', 'brand': 'brand-a', 'price': 60.0, 'user_session': 'session-1'},
        {'event_time': '2019-10-01T00:03:00', 'event_type': 'purchase', 'product_id': 'cheaper', 'category_id': 'category-a', 'category_code': 'electronics.phone', 'brand': 'brand-a', 'price': 60.0, 'user_session': 'session-2'},
        {'event_time': '2019-10-01T00:04:00', 'event_type': 'view', 'product_id': 'expensive', 'category_id': 'category-a', 'category_code': 'electronics.phone', 'brand': 'brand-b', 'price': 95.0, 'user_session': 'session-3'},
        {'event_time': '2019-10-01T00:05:00', 'event_type': 'view', 'product_id': 'other-category', 'category_id': 'category-b', 'category_code': 'electronics.tablet', 'brand': 'brand-c', 'price': 40.0, 'user_session': 'session-4'},
    ])


def test_alternatives_filter_and_rank_with_observed_evidence(monkeypatch):
    monkeypatch.setattr(data_service, '_load_processed_events', alternatives_events)

    result = data_service.get_affordable_alternatives('selected')

    assert result['selected_product']['latest_observed_price'] == 90.0
    assert [item['product_id'] for item in result['alternatives']] == ['cheaper']
    alternative = result['alternatives'][0]
    assert alternative['category'] == 'electronics.phone'
    assert alternative['category_id'] == 'category-a'
    assert alternative['brand'] == 'brand-a'
    assert alternative['price_difference'] == 30.0
    assert alternative['percentage_cheaper'] == 33.33
    assert alternative['co_view_sessions'] == 1
    assert alternative['co_purchase_sessions'] == 1
    assert alternative['same_brand'] is True
    assert alternative['score'] == 5
    assert 'unknown' not in alternative.values()


def test_alternatives_respect_budget_and_missing_selected_product(monkeypatch):
    monkeypatch.setattr(data_service, '_load_processed_events', alternatives_events)

    result = data_service.get_affordable_alternatives('selected', budget=50.0)

    assert result['alternatives'] == []
    assert data_service.get_affordable_alternatives('not-in-data') is None
