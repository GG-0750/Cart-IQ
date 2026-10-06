import pandas as pd

from backend.app.services import data_service
from backend.app.services.recommendation_service import rank_recommendations


def test_recommendation_ranking_is_deterministic():
    records = [
        {'product_id': 'p2', 'score': 0.8, 'reason_codes': ['viewed_recently']},
        {'product_id': 'p1', 'score': 0.9, 'reason_codes': ['carted']},
    ]
    result = rank_recommendations(records)
    assert result[0]['product_id'] == 'p1'
    assert result[1]['product_id'] == 'p2'


def test_user_lookup_and_recommendations_use_observed_events(monkeypatch):
    events_frame = pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'seen-1', 'category_id': 'category-a', 'price': 10.0, 'user_id': 'real-user'},
        {'event_time': '2019-10-01T00:01:00', 'event_type': 'cart', 'product_id': 'seen-2', 'category_id': 'category-a', 'price': 20.0, 'user_id': 'real-user'},
        {'event_time': '2019-10-01T00:02:00', 'event_type': 'view', 'product_id': 'candidate-1', 'category_id': 'category-a', 'price': 40.0, 'user_id': 'other-user'},
        {'event_time': '2019-10-01T00:03:00', 'event_type': 'view', 'product_id': 'candidate-1', 'category_id': 'category-a', 'price': 50.0, 'user_id': 'other-user'},
        {'event_time': '2019-10-01T00:04:00', 'event_type': 'purchase', 'product_id': 'candidate-1', 'category_id': 'category-a', 'price': 60.0, 'user_id': 'other-user'},
    ])
    monkeypatch.setattr(data_service, '_load_processed_events', lambda: events_frame)

    users = data_service.get_users(query='real-user')
    recommendations = data_service.get_recommendations_for_user('real-user')

    assert [user['user_id'] for user in users] == ['real-user']
    assert users[0]['event_count'] == 2
    assert [item['product_id'] for item in recommendations] == ['candidate-1']
    assert recommendations[0]['observed_price'] == 50.0
    assert recommendations[0]['timestamp'] == '2019-10-01T00:04:00'
    assert recommendations[0]['evidence']['user_event_count_in_category'] == 2
    assert recommendations[0]['evidence']['product_event_count'] == 3
    assert recommendations[0]['reason_codes'] == ['cart_interest', 'view_interest', 'observed_category_activity']


def test_unknown_recommendation_user_is_not_treated_as_an_empty_profile(monkeypatch):
    events_frame = pd.DataFrame([
        {'event_time': '2019-10-01T00:00:00', 'event_type': 'view', 'product_id': 'seen-1', 'category_id': 'category-a', 'price': 10.0, 'user_id': 'real-user'},
    ])
    monkeypatch.setattr(data_service, '_load_processed_events', lambda: events_frame)

    assert data_service.get_recommendations_for_user('missing-user') is None
