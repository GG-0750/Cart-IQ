from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from backend.app.config import DATA_DIR, DEFAULT_SAMPLE_ROWS, RAW_DATA_DIR
from backend.app.data_processing.dataset_inspector import detect_dataset, validate_dataset_file
from backend.app.data_processing.processor import process_real_dataset

PROCESSED_DIR = DATA_DIR / 'processed'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _load_processed_events():
    cleaned_path = PROCESSED_DIR / 'cleaned_events'
    if not cleaned_path.exists() or not any(cleaned_path.glob('*.parquet')):
        return None
    return pq.read_table(cleaned_path).to_pandas()


def _json_records(frame) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient='records', date_format='iso'))


def dataset_status() -> dict[str, Any]:
    dataset_path = detect_dataset(RAW_DATA_DIR)
    if not dataset_path:
        return {'detected': False, 'message': 'Dataset not detected in data/raw/.', 'dataset_path': None}
    validation = validate_dataset_file(dataset_path, max_rows=200000)
    return {
        'detected': True,
        'dataset_path': dataset_path,
        'file_name': Path(dataset_path).name,
        'validation': validation,
        'validation_mode': 'sampled' if validation.get('summary', {}).get('sampled') else 'full',
    }


def validate_dataset(dataset_path: str | None = None) -> dict[str, Any]:
    source = dataset_path or detect_dataset(RAW_DATA_DIR)
    if not source:
        return {'valid': False, 'error': 'Dataset not detected in data/raw/.'}
    return validate_dataset_file(source, max_rows=200000)


def process_dataset(dataset_path: str | None = None, sample_rows: int = DEFAULT_SAMPLE_ROWS) -> dict[str, Any]:
    return process_real_dataset(sample_rows=sample_rows, dataset_path=dataset_path)


def get_summary() -> dict[str, Any]:
    df = _load_processed_events()
    if df is None:
        return {'processed': False, 'message': 'Processed data is not available. Run data processing first.'}

    event_counts = df['event_type'].value_counts(dropna=False)
    return {
        'processed': True,
        'total_events': len(df),
        'unique_users': int(df['user_id'].nunique()),
        'unique_products': int(df['product_id'].nunique()),
        'views': int(event_counts.get('view', 0)),
        'cart_additions': int(event_counts.get('cart', 0)),
        'purchases': int(event_counts.get('purchase', 0)),
        'event_type_counts': [
            {'event_type': event_type, 'count': int(count)}
            for event_type, count in event_counts.items()
        ],
        'file_name': 'cleaned_events.parquet',
    }


def get_all_products(limit: int = 25, category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    if category:
        category_query = str(category).strip().lower()
        df = df[
            df['category_id'].astype(str).str.lower().str.contains(category_query, na=False)
            | df['category_code'].astype(str).str.lower().str.contains(category_query, na=False)
        ]
    if query:
        query_text = str(query).strip().lower()
        if query_text:
            df = df[
                df['product_id'].astype(str).str.lower().str.contains(query_text, na=False)
                | df['brand'].astype(str).str.lower().str.contains(query_text, na=False)
                | df['category_id'].astype(str).str.lower().str.contains(query_text, na=False)
                | df['category_code'].astype(str).str.lower().str.contains(query_text, na=False)
            ]

    if df.empty:
        return []

    latest_rows = df.sort_values('event_time').groupby('product_id', as_index=False).tail(1)
    latest_prices = latest_rows[['product_id', 'price', 'event_time', 'brand', 'category_id', 'category_code']].rename(columns={'event_time': 'latest_event_time', 'price': 'latest_observed_price'})
    product_summary = (
        df.groupby('product_id', as_index=False)
        .agg(
            event_count=('product_id', 'size'),
            avg_price=('price', 'mean'),
            latest_event_time=('event_time', 'max'),
        )
    )
    merged = product_summary.merge(latest_prices[['product_id', 'latest_observed_price', 'brand', 'category_id', 'category_code']], on='product_id', how='left')
    merged = merged.sort_values(['event_count', 'product_id'], ascending=[False, True]).head(max(1, min(limit, 200))).reset_index(drop=True)
    return _json_records(merged)


def search_products(query: str, limit: int = 12) -> list[dict[str, Any]]:
    if not str(query or '').strip():
        return []
    query_text = str(query).strip().lower()
    return get_all_products(limit=limit, query=query_text)


def get_product_detail(product_id: str) -> dict[str, Any]:
    df = _load_processed_events()
    if df is None:
        return {'error': 'Processed data is not available. Run data processing first.'}
    rows = _json_records(
        df[df['product_id'] == product_id].sort_values('event_time', ascending=False).head(20)
    )
    if not rows:
        return {'product_id': product_id, 'events': []}
    return {'product_id': product_id, 'events': rows}


def get_price_history(product_id: str) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    history = df.loc[df['product_id'] == product_id, ['product_id', 'event_time', 'price']]
    return _json_records(history.sort_values('event_time'))


def get_user_activity(user_id: str) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    return _json_records(df[df['user_id'] == user_id].sort_values('event_time'))


def get_users(limit: int = 25, query: str | None = None) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    users = df.groupby('user_id').agg(
        event_count=('event_type', 'size'),
        latest_event_time=('event_time', 'max'),
    ).reset_index()
    if query:
        users = users[users['user_id'].astype(str).str.contains(query, regex=False)]
    users = users.sort_values(['event_count', 'user_id'], ascending=[False, True]).head(max(1, min(limit, 100)))
    return _json_records(users)


def get_recommendations_for_user(user_id: str) -> list[dict[str, Any]] | None:
    df = _load_processed_events()
    if df is None:
        return None
    user_events = df[df['user_id'].astype(str) == str(user_id)]
    if user_events.empty:
        return None

    event_weights = {'view': 1.0, 'cart': 2.0, 'purchase': 3.0, 'remove_from_cart': 0.5}
    user_events = user_events.assign(
        _weight=user_events['event_type'].map(event_weights).fillna(0.0)
    )
    category_interest = user_events.dropna(subset=['category_id']).groupby('category_id').agg(
        interest_weight=('_weight', 'sum'),
        user_event_count=('event_type', 'size'),
        user_event_types=('event_type', lambda values: sorted(set(values))),
    ).sort_values('interest_weight', ascending=False).head(3)
    if category_interest.empty:
        return []

    seen_products = set(user_events['product_id'].dropna().astype(str))
    candidates = df[
        df['category_id'].isin(category_interest.index)
        & ~df['product_id'].astype(str).isin(seen_products)
    ]
    recommendations = []
    for product_id, events in candidates.groupby('product_id'):
        category_id = events['category_id'].mode().iloc[0]
        interest = category_interest.loc[category_id]
        product_event_count = len(events)
        observed_price = events['price'].dropna().mean()
        latest_time = events['event_time'].max()
        user_event_types = interest['user_event_types']
        reason_codes = [f'{event_type}_interest' for event_type in user_event_types if event_type in event_weights]
        reason_codes.append('observed_category_activity')
        recommendations.append({
            'product_id': str(product_id),
            'score': float(interest['interest_weight']) * product_event_count,
            'explanation': (
                f"Based on {int(interest['user_event_count'])} observed user interactions "
                f"in category {category_id} and {product_event_count} observed events for this product."
            ),
            'reason_codes': reason_codes,
            'observed_price': float(observed_price) if observed_price == observed_price else None,
            'timestamp': latest_time.isoformat() if hasattr(latest_time, 'isoformat') else str(latest_time),
            'evidence': {
                'category_id': str(category_id),
                'user_event_count_in_category': int(interest['user_event_count']),
                'user_event_types': user_event_types,
                'product_event_count': product_event_count,
                'product_event_types': sorted(set(events['event_type'].dropna().astype(str))),
            },
        })

    return sorted(recommendations, key=lambda item: (-item['score'], item['product_id']))[:10]


def get_browsing_insights(limit: int = 50) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None or df.empty:
        return []

    event_weights = {'view': 1.0, 'cart': 2.0, 'remove_from_cart': 0.5}
    window_start = df['event_time'].min()
    window_end = df['event_time'].max()
    insights = []
    for product_id, product_events in df.groupby('product_id'):
        counts = product_events['event_type'].value_counts()
        view_count = int(counts.get('view', 0))
        cart_additions = int(counts.get('cart', 0))
        cart_removals = int(counts.get('remove_from_cart', 0))
        purchase_count = int(counts.get('purchase', 0))
        if view_count < 2 or purchase_count > 0:
            continue

        ordered_events = product_events.sort_values('event_time')
        latest_event = ordered_events.iloc[-1]
        price_events = ordered_events.dropna(subset=['price'])
        latest_price = price_events.iloc[-1]['price'] if not price_events.empty else None
        category_codes = product_events['category_code'].dropna().astype(str).mode() if 'category_code' in product_events else []
        category_ids = product_events['category_id'].dropna().astype(str).mode() if 'category_id' in product_events else []
        brands = product_events['brand'].dropna().astype(str).mode() if 'brand' in product_events else []
        category_code = category_codes.iloc[0] if len(category_codes) else None
        category_id = category_ids.iloc[0] if len(category_ids) else None
        brand = brands.iloc[0] if len(brands) else None
        interest_score = view_count * event_weights['view'] + cart_additions * event_weights['cart'] + cart_removals * event_weights['remove_from_cart']

        insights.append({
            'product_id': str(product_id),
            'views': view_count,
            'cart_additions': cart_additions,
            'cart_removals': cart_removals,
            'purchases': purchase_count,
            'latest_event': str(latest_event['event_type']),
            'latest_event_time': latest_event['event_time'].isoformat() if hasattr(latest_event['event_time'], 'isoformat') else str(latest_event['event_time']),
            'latest_observed_price': float(latest_price) if latest_price is not None else None,
            'price_observation_count': len(price_events),
            'price_history_available': not price_events.empty,
            'category': category_code or category_id,
            'category_id': category_id,
            'brand': brand,
            'interest_score': round(interest_score, 2),
            'interest_score_formula': 'views + 2*cart_additions + 0.5*cart_removals',
            'observation_window': {
                'start': window_start.isoformat() if hasattr(window_start, 'isoformat') else str(window_start),
                'end': window_end.isoformat() if hasattr(window_end, 'isoformat') else str(window_end),
            },
        })

    return sorted(insights, key=lambda item: (-item['interest_score'], item['product_id']))[:max(1, min(limit, 100))]


def get_affordable_alternatives(product_id: str, budget: float | None = None, limit: int = 10) -> dict[str, Any] | None:
    df = _load_processed_events()
    if df is None:
        return None

    events = df.copy()
    category_codes = events['category_code'].astype('string').str.strip()
    events['_category_key'] = category_codes.mask(category_codes.eq('')).fillna(events['category_id'].astype('string'))
    selected_events = events[events['product_id'].astype(str) == str(product_id)]
    if selected_events.empty:
        return None

    selected_categories = selected_events['_category_key'].dropna().mode()
    selected_category_ids = selected_events['category_id'].dropna().astype(str).mode()
    selected_prices = selected_events.dropna(subset=['price']).sort_values('event_time')
    if selected_categories.empty or selected_prices.empty:
        return {
            'selected_product': {'product_id': product_id, 'latest_observed_price': None},
            'budget_limit': budget,
            'alternatives': [],
        }

    selected_category = str(selected_categories.iloc[0])
    selected_category_id = selected_category_ids.iloc[0] if len(selected_category_ids) else None
    latest_selected_event = selected_prices.iloc[-1]
    selected_price = float(latest_selected_event['price'])
    selected_brands = selected_events['brand'].dropna().astype(str).str.strip()
    selected_brands = selected_brands[selected_brands.ne('')].mode()
    selected_brand = selected_brands.iloc[0] if len(selected_brands) else None
    effective_budget = budget
    if effective_budget is None:
        configured_budget = get_budget_store().get('total_budget')
        effective_budget = float(configured_budget) if configured_budget is not None else 0.0
    effective_budget = max(0.0, float(effective_budget or 0.0))

    selected_views = set(selected_events.loc[selected_events['event_type'] == 'view', 'user_session'].dropna().astype(str)) if 'user_session' in events else set()
    selected_purchases = set(selected_events.loc[selected_events['event_type'] == 'purchase', 'user_session'].dropna().astype(str)) if 'user_session' in events else set()
    same_category = events[
        (events['_category_key'] == selected_category)
        & (events['product_id'].astype(str) != str(product_id))
    ]
    alternatives = []
    for candidate_id, candidate_events in same_category.groupby('product_id'):
        observed_prices = candidate_events.dropna(subset=['price']).sort_values('event_time')
        if observed_prices.empty:
            continue
        latest_candidate_event = observed_prices.iloc[-1]
        candidate_price = float(latest_candidate_event['price'])
        if selected_price <= 0 or candidate_price < 0 or candidate_price >= selected_price:
            continue
        if effective_budget > 0 and candidate_price > effective_budget:
            continue

        candidate_brands = candidate_events['brand'].dropna().astype(str).str.strip()
        candidate_brands = candidate_brands[candidate_brands.ne('')].mode()
        candidate_brand = candidate_brands.iloc[0] if len(candidate_brands) else None
        candidate_views = set(candidate_events.loc[candidate_events['event_type'] == 'view', 'user_session'].dropna().astype(str)) if 'user_session' in events else set()
        candidate_purchases = set(candidate_events.loc[candidate_events['event_type'] == 'purchase', 'user_session'].dropna().astype(str)) if 'user_session' in events else set()
        co_view_sessions = len(selected_views & candidate_views)
        co_purchase_sessions = len(selected_purchases & candidate_purchases)
        same_brand = bool(selected_brand and candidate_brand and selected_brand == candidate_brand)
        price_difference = selected_price - candidate_price
        percentage_cheaper = (price_difference / selected_price) * 100.0
        score = co_purchase_sessions * 3 + co_view_sessions + int(same_brand)
        candidate_category_code = candidate_events['category_code'].dropna().astype(str).str.strip()
        candidate_category_code = candidate_category_code[candidate_category_code.ne('')].mode()
        candidate_category = candidate_category_code.iloc[0] if len(candidate_category_code) else selected_category
        reason_codes = ['same_category', 'lower_observed_price']
        if same_brand:
            reason_codes.append('same_brand')
        if co_view_sessions:
            reason_codes.append('co_view_sessions')
        if co_purchase_sessions:
            reason_codes.append('co_purchase_sessions')
        explanation = (
            f"Same observed category; latest observed price is {percentage_cheaper:.1f}% lower. "
            f"Shared view sessions: {co_view_sessions}; shared purchase sessions: {co_purchase_sessions}."
        )
        if same_brand:
            explanation += f' Same observed brand: {candidate_brand}.'

        alternatives.append({
            'product_id': str(candidate_id),
            'category': candidate_category,
            'category_id': selected_category_id,
            'brand': candidate_brand,
            'latest_observed_price': candidate_price,
            'price_difference': round(price_difference, 2),
            'percentage_cheaper': round(percentage_cheaper, 2),
            'observation_timestamp': latest_candidate_event['event_time'].isoformat() if hasattr(latest_candidate_event['event_time'], 'isoformat') else str(latest_candidate_event['event_time']),
            'observed_event_count': len(candidate_events),
            'co_view_sessions': co_view_sessions,
            'co_purchase_sessions': co_purchase_sessions,
            'same_brand': same_brand,
            'score': score,
            'score_formula': '3*co_purchase_sessions + co_view_sessions + same_brand',
            'reason_codes': reason_codes,
            'similarity_explanation': explanation,
        })

    alternatives.sort(key=lambda item: (-item['score'], -item['percentage_cheaper'], item['product_id']))
    return {
        'selected_product': {'product_id': str(product_id), 'latest_observed_price': selected_price},
        'budget_limit': effective_budget if effective_budget > 0 else None,
        'alternatives': alternatives[:max(1, min(limit, 50))],
    }


def get_bundle_recommendations(main_product: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None or df.empty:
        return []
    purchase_events = df.loc[df['event_type'].astype(str).str.lower().eq('purchase'), ['user_session', 'user_id', 'product_id', 'event_time', 'price']].dropna(subset=['user_session', 'product_id'])
    if purchase_events.empty:
        return []

    co_purchase_counts: dict[tuple[str, str], dict[str, Any]] = {}
    session_pair_totals: dict[tuple[str, str], list[float]] = {}
    pair_observed_prices: dict[tuple[str, str], dict[str, float]] = {}
    latest_prices = (
        df.dropna(subset=['product_id', 'price'])
        .sort_values('event_time')
        .groupby('product_id', as_index=False)
        .tail(1)[['product_id', 'price', 'event_time']]
        .rename(columns={'price': 'latest_observed_price', 'event_time': 'latest_observed_time'})
    )
    price_lookup = {str(row['product_id']): float(row['latest_observed_price']) for _, row in latest_prices.iterrows() if row['latest_observed_price'] is not None}
    session_products = purchase_events.groupby('user_session', dropna=False)
    for _, session_group in session_products:
        products = list(dict.fromkeys(session_group['product_id'].dropna().astype(str)))
        if len(products) < 2:
            continue
        session_price_lookup = {}
        for product_id, product_rows in session_group.groupby('product_id', dropna=False):
            prices = product_rows['price'].dropna().astype(float)
            if not prices.empty:
                session_price_lookup[str(product_id)] = float(prices.iloc[-1])

        if main_product:
            main_value = str(main_product)
            if main_value not in products:
                continue
            related_products = [product for product in products if product != main_value]
            if not related_products:
                continue
            for related_product in related_products:
                key = tuple(sorted((main_value, str(related_product))))
                item = co_purchase_counts.setdefault(key, {'support': 0, 'sessions': set()})
                item['sessions'].add(str(session_group['user_session'].iloc[0]))
                item['support'] += 1
                pair_total = session_price_lookup.get(main_value, 0.0) + session_price_lookup.get(str(related_product), 0.0)
                if pair_total > 0:
                    session_pair_totals.setdefault(key, []).append(pair_total)
                pair_observed_prices[key] = {
                    main_value: float(session_price_lookup.get(main_value, price_lookup.get(main_value, 0.0)) or 0.0),
                    str(related_product): float(session_price_lookup.get(str(related_product), price_lookup.get(str(related_product), 0.0)) or 0.0),
                }
        else:
            for idx, left in enumerate(products):
                for right in products[idx + 1:]:
                    key = tuple(sorted((str(left), str(right))))
                    item = co_purchase_counts.setdefault(key, {'support': 0, 'sessions': set()})
                    item['sessions'].add(str(session_group['user_session'].iloc[0]))
                    item['support'] += 1
                    pair_total = session_price_lookup.get(str(left), 0.0) + session_price_lookup.get(str(right), 0.0)
                    if pair_total > 0:
                        session_pair_totals.setdefault(key, []).append(pair_total)
                    pair_observed_prices[key] = {
                        str(left): float(session_price_lookup.get(str(left), price_lookup.get(str(left), 0.0)) or 0.0),
                        str(right): float(session_price_lookup.get(str(right), price_lookup.get(str(right), 0.0)) or 0.0),
                    }

    if not co_purchase_counts:
        return []

    budget_limit = get_budget_store().get('total_budget') if get_budget_store() else None
    budget_limit = float(budget_limit) if budget_limit is not None else None
    bundle_rows = []
    for (left_product, right_product), payload in co_purchase_counts.items():
        pair_total_values = session_pair_totals.get((left_product, right_product), [])
        pair_total = (sum(pair_total_values) / len(pair_total_values)) if pair_total_values else (float(price_lookup.get(left_product, 0.0) or 0.0) + float(price_lookup.get(right_product, 0.0) or 0.0))
        pair_price_map = pair_observed_prices.get((left_product, right_product), {
            left_product: float(price_lookup.get(left_product, 0.0) or 0.0),
            right_product: float(price_lookup.get(right_product, 0.0) or 0.0),
        })
        if main_product:
            main_value = str(main_product)
            related_value = right_product if left_product == main_value else left_product
            bundle_rows.append({
                'main_product': main_value,
                'related_product': related_value,
                'related_products': [related_value],
                'support': int(payload['support']),
                'co_purchase_count': int(payload['support']),
                'sessions': sorted(payload['sessions']),
                'observed_prices': {
                    main_value: float(pair_price_map.get(main_value, price_lookup.get(main_value, 0.0)) or 0.0),
                    related_value: float(pair_price_map.get(related_value, price_lookup.get(related_value, 0.0)) or 0.0),
                },
                'main_product_price': float(pair_price_map.get(main_value, price_lookup.get(main_value, 0.0)) or 0.0),
                'related_product_price': float(pair_price_map.get(related_value, price_lookup.get(related_value, 0.0)) or 0.0),
                'total_observed_bundle_cost': round(pair_total, 2),
                'budget_compatible': (budget_limit is None) or (pair_total <= budget_limit),
                'explanation': f'Co-purchased in {int(payload["support"])} session(s) with observed total bundle cost {round(pair_total, 2)}.'
            })
        else:
            bundle_rows.append({
                'main_product': left_product,
                'related_product': right_product,
                'related_products': [right_product],
                'support': int(payload['support']),
                'co_purchase_count': int(payload['support']),
                'sessions': sorted(payload['sessions']),
                'observed_prices': {
                    left_product: float(pair_price_map.get(left_product, price_lookup.get(left_product, 0.0)) or 0.0),
                    right_product: float(pair_price_map.get(right_product, price_lookup.get(right_product, 0.0)) or 0.0),
                },
                'main_product_price': float(pair_price_map.get(left_product, price_lookup.get(left_product, 0.0)) or 0.0),
                'related_product_price': float(pair_price_map.get(right_product, price_lookup.get(right_product, 0.0)) or 0.0),
                'total_observed_bundle_cost': round(pair_total, 2),
                'budget_compatible': (budget_limit is None) or (pair_total <= budget_limit),
                'explanation': f'Co-purchased in {int(payload["support"])} session(s) with observed total bundle cost {round(pair_total, 2)}.'
            })

    bundle_rows.sort(key=lambda item: (-item['support'], item['main_product'], item['related_product']))
    return bundle_rows[:max(1, min(limit, 50))]


def get_event_analytics() -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    counts = df.groupby('event_type', dropna=False).size().sort_values(ascending=False).rename('count').reset_index()
    return _json_records(counts)


def get_category_analytics() -> list[dict[str, Any]]:
    df = _load_processed_events()
    if df is None:
        return []
    counts = df.groupby('category_id', dropna=False).size().sort_values(ascending=False).head(20).rename('count').reset_index()
    return _json_records(counts)


def get_funnel() -> dict[str, Any]:
    df = _load_processed_events()
    if df is None:
        return {'steps': [], 'values': []}
    counts = df['event_type'].value_counts()
    return {'steps': ['view', 'cart', 'purchase'], 'values': [int(counts.get('view', 0)), int(counts.get('cart', 0)), int(counts.get('purchase', 0))]}


def get_purchase_insights() -> dict[str, Any]:
    df = _load_processed_events()
    if df is None or df.empty:
        return {'sessions': [], 'total_sessions': 0}

    event_columns = ['view', 'cart', 'remove_from_cart', 'purchase']
    if 'user_session' not in df.columns:
        df = df.copy()
        df['user_session'] = df['user_id'].fillna('unknown').astype(str) + '-session'

    session_rows = []
    for (_, session_group) in df.groupby(['user_id', 'user_session'], dropna=False):
        ordered_events = session_group.sort_values('event_time')
        counts = ordered_events['event_type'].fillna('').astype(str).str.lower().value_counts()
        view_count = int(counts.get('view', 0))
        cart_count = int(counts.get('cart', 0))
        remove_count = int(counts.get('remove_from_cart', 0))
        purchase_count = int(counts.get('purchase', 0))
        view_to_cart_conversion = (cart_count / view_count) if view_count else None
        cart_to_purchase_conversion = (purchase_count / cart_count) if cart_count else None
        total_interactions = view_count + cart_count + remove_count + purchase_count
        readiness_score = 0.0
        if total_interactions:
            readiness_score = ((purchase_count * 2.0) + (cart_count * 1.5) - (remove_count * 0.5)) / total_interactions * 100.0
        readiness_score = max(0.0, min(100.0, round(readiness_score, 2)))
        summary_note = 'No purchase was recorded in the loaded observation window.' if purchase_count == 0 else 'Observed purchase activity was recorded in the loaded observation window.'
        session_rows.append({
            'user_id': str(session_group['user_id'].dropna().astype(str).iloc[0]) if 'user_id' in session_group.columns and not session_group['user_id'].dropna().empty else 'unknown',
            'user_session': str(session_group['user_session'].dropna().astype(str).iloc[0]) if 'user_session' in session_group.columns and not session_group['user_session'].dropna().empty else 'unknown',
            'event_types': ordered_events['event_type'].fillna('').astype(str).str.lower().tolist(),
            'view_count': view_count,
            'cart_additions': cart_count,
            'cart_removals': remove_count,
            'purchase_count': purchase_count,
            'view_to_cart_conversion': round(view_to_cart_conversion, 4) if view_to_cart_conversion is not None else None,
            'cart_to_purchase_conversion': round(cart_to_purchase_conversion, 4) if cart_to_purchase_conversion is not None else None,
            'readiness_score': readiness_score,
            'readiness_formula': '((purchase_count * 2.0) + (cart_count * 1.5) - (remove_count * 0.5)) / total_interactions * 100',
            'readiness_label': 'heuristic',
            'summary_note': summary_note,
            'product_ids': list(dict.fromkeys(session_group['product_id'].dropna().astype(str).tolist())),
            'start_time': ordered_events['event_time'].min() if 'event_time' in session_group.columns else None,
            'end_time': ordered_events['event_time'].max() if 'event_time' in session_group.columns else None,
        })

    session_rows.sort(key=lambda item: (-item['readiness_score'], item['user_id'], item['user_session']))
    return {
        'sessions': session_rows,
        'total_sessions': len(session_rows),
        'event_type_counts': {key: int(df['event_type'].fillna('').astype(str).str.lower().value_counts().get(key, 0)) for key in event_columns},
    }


def get_watchlist_store() -> list[str]:
    path = DATA_DIR / 'watchlist.json'
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_watchlist_store(items: list[str]) -> None:
    path = DATA_DIR / 'watchlist.json'
    path.write_text(json.dumps(items), encoding='utf-8')


def get_budget_store() -> dict[str, Any]:
    path = DATA_DIR / 'budget.json'
    if not path.exists():
        return {'total_budget': 0.0, 'target_price': None, 'preferred_category': None, 'minimum_price': None, 'maximum_price': None}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'total_budget': 0.0, 'target_price': None, 'preferred_category': None, 'minimum_price': None, 'maximum_price': None}


def save_budget_store(payload: dict[str, Any]) -> None:
    path = DATA_DIR / 'budget.json'
    path.write_text(json.dumps(payload), encoding='utf-8')


def get_shopping_plan_store() -> list[dict[str, Any]]:
    path = DATA_DIR / 'shopping_plan.json'
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_shopping_plan_store(items: list[dict[str, Any]]) -> None:
    path = DATA_DIR / 'shopping_plan.json'
    path.write_text(json.dumps(items), encoding='utf-8')
