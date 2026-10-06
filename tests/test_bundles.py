import pandas as pd

from backend.app.services import data_service
from backend.app.services.bundle_service import build_bundle_summary


def test_bundle_summary():
    bundle = build_bundle_summary(main_product='p1', related_products=['p2', 'p3'], prices={'p2': 20.0, 'p3': 25.0})
    assert bundle['main_product'] == 'p1'
    assert bundle['total_observed_price'] == 45.0
    assert bundle['related_products'] == ['p2', 'p3']


def test_bundle_recommendations_use_session_co_purchase_evidence(monkeypatch):
    events_frame = pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'purchase', 'product_id': 'p1', 'user_id': 'u1', 'user_session': 'session-1', 'price': 100.0, 'category_id': 'cat-1', 'brand': 'brand-a'},
        {'event_time': '2019-10-01T00:01:00', 'event_type': 'purchase', 'product_id': 'p2', 'user_id': 'u1', 'user_session': 'session-1', 'price': 50.0, 'category_id': 'cat-1', 'brand': 'brand-b'},
        {'event_time': '2019-10-01T00:02:00', 'event_type': 'purchase', 'product_id': 'p2', 'user_id': 'u2', 'user_session': 'session-2', 'price': 42.0, 'category_id': 'cat-1', 'brand': 'brand-b'},
        {'event_time': '2019-10-01T00:03:00', 'event_type': 'purchase', 'product_id': 'p3', 'user_id': 'u1', 'user_session': 'session-1', 'price': 30.0, 'category_id': 'cat-1', 'brand': 'brand-c'},
        {'event_time': '2019-10-01T00:04:00', 'event_type': 'purchase', 'product_id': 'p3', 'user_id': 'u3', 'user_session': 'session-3', 'price': 28.0, 'category_id': 'cat-1', 'brand': 'brand-c'},
        {'event_time': '2019-10-01T00:05:00', 'event_type': 'purchase', 'product_id': 'p4', 'user_id': 'u4', 'user_session': 'session-4', 'price': 20.0, 'category_id': 'cat-1', 'brand': 'brand-d'},
    ])
    monkeypatch.setattr(data_service, '_load_processed_events', lambda: events_frame)

    bundles = data_service.get_bundle_recommendations('p1')
    assert bundles[0]['main_product'] == 'p1'
    assert bundles[0]['related_product'] == 'p2'
    assert bundles[0]['support'] == 1
    assert bundles[0]['total_observed_bundle_cost'] == 150.0
    assert bundles[0]['budget_compatible'] in (True, False)
    assert bundles[0]['explanation']
