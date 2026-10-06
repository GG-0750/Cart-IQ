import pandas as pd

from backend.app.services import data_service


def test_search_products_matches_real_dataset_fields(monkeypatch):
    events_frame = pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'p-101', 'brand': 'BrandA', 'category_id': 'cat-1', 'category_code': 'electronics.phone', 'price': 100.0, 'user_id': 'u-1', 'user_session': 's-1'},
        {'event_time': '2019-10-01T00:05:00', 'event_type': 'purchase', 'product_id': 'p-101', 'brand': 'BrandA', 'category_id': 'cat-1', 'category_code': 'electronics.phone', 'price': 95.0, 'user_id': 'u-1', 'user_session': 's-1'},
        {'event_time': '2019-10-01T00:10:00', 'event_type': 'view', 'product_id': 'p-202', 'brand': 'BrandB', 'category_id': 'cat-2', 'category_code': 'electronics.tablet', 'price': 150.0, 'user_id': 'u-2', 'user_session': 's-2'},
    ])
    monkeypatch.setattr(data_service, '_load_processed_events', lambda: events_frame)

    results = data_service.search_products('phone', limit=20)

    assert [item['product_id'] for item in results] == ['p-101']
    assert results[0]['latest_observed_price'] == 95.0
    assert results[0]['brand'] == 'BrandA'
    assert results[0]['category_code'] == 'electronics.phone'
