import pandas as pd

from backend.app.services import data_service


def test_browsing_insights_only_includes_repeated_views_without_purchase(monkeypatch):
    events_frame = pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'repeated', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 10.0},
        {'event_time': '2019-10-01T00:01:00', 'event_type': 'view', 'product_id': 'repeated', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 11.0},
        {'event_time': '2019-10-01T00:02:00', 'event_type': 'cart', 'product_id': 'repeated', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 12.0},
        {'event_time': '2019-10-01T00:03:00', 'event_type': 'remove_from_cart', 'product_id': 'repeated', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 13.0},
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'purchased', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 15.0},
        {'event_time': '2019-10-01T00:01:00', 'event_type': 'view', 'product_id': 'purchased', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 15.0},
        {'event_time': '2019-10-01T00:02:00', 'event_type': 'purchase', 'product_id': 'purchased', 'category_id': 'category-a', 'category_code': 'category.a', 'brand': 'brand-a', 'price': 15.0},
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'single-view', 'category_id': 'category-b', 'category_code': 'category.b', 'brand': None, 'price': 20.0},
    ])
    monkeypatch.setattr(data_service, '_load_processed_events', lambda: events_frame)

    results = data_service.get_browsing_insights()

    assert [item['product_id'] for item in results] == ['repeated']
    assert results[0]['views'] == 2
    assert results[0]['cart_additions'] == 1
    assert results[0]['cart_removals'] == 1
    assert results[0]['purchases'] == 0
    assert results[0]['latest_event'] == 'remove_from_cart'
    assert results[0]['latest_observed_price'] == 13.0
    assert results[0]['price_observation_count'] == 4
    assert results[0]['category'] == 'category.a'
    assert results[0]['brand'] == 'brand-a'
    assert results[0]['interest_score'] == 4.5
    assert results[0]['interest_score_formula'] == 'views + 2*cart_additions + 0.5*cart_removals'
