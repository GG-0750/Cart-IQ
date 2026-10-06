from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import APP_HOST, APP_PORT, DATA_DIR, RAW_DATA_DIR
from backend.app.schemas.models import BudgetRequest, ProcessRequest, ShoppingPlanRequest, ValidationRequest
from backend.app.services.analytics_service import calculate_price_change
from backend.app.services.budget_service import compute_budget_summary
from backend.app.services.bundle_service import build_bundle_summary
from backend.app.services.data_service import (
    dataset_status,
    get_all_products,
    get_affordable_alternatives,
    get_browsing_insights,
    get_bundle_recommendations,
    get_budget_store,
    get_category_analytics,
    get_event_analytics,
    get_funnel,
    get_price_history,
    get_product_detail,
    get_purchase_insights,
    get_recommendations_for_user,
    get_shopping_plan_store,
    get_summary,
    get_user_activity,
    get_users,
    get_watchlist_store,
    process_dataset,
    save_budget_store,
    save_shopping_plan_store,
    save_watchlist_store,
    validate_dataset,
)
from backend.app.services.recommendation_service import rank_recommendations

app = FastAPI(title='CartIQ', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health() -> dict[str, Any]:
    return {'status': 'ok', 'service': 'CartIQ', 'dataset_detected': RAW_DATA_DIR.exists() and any(RAW_DATA_DIR.iterdir())}


@app.get('/api/datasets/status')
def datasets_status() -> dict[str, Any]:
    return dataset_status()


@app.get('/api/datasets/files')
def datasets_files() -> dict[str, Any]:
    raw_dir = DATA_DIR / 'raw'
    files = []
    if raw_dir.exists():
        for child in sorted(raw_dir.iterdir()):
            if child.is_file():
                files.append({'name': child.name, 'size_bytes': child.stat().st_size, 'path': str(child)})
    return {'files': files}


@app.post('/api/data/validate')
def data_validate(payload: ValidationRequest) -> dict[str, Any]:
    return validate_dataset(payload.dataset_path)


@app.post('/api/data/process')
def data_process(payload: ProcessRequest) -> dict[str, Any]:
    return process_dataset(payload.dataset_path, payload.sample_rows)


@app.get('/api/data/summary')
def data_summary() -> dict[str, Any]:
    return get_summary()


@app.get('/api/overview')
def overview() -> dict[str, Any]:
    summary = get_summary()
    if not summary.get('processed'):
        return {'error': 'Processed data is not available. Run data processing first.'}
    return {
        'metrics': summary,
        'event_distribution': get_event_analytics(),
        'category_activity': get_category_analytics(),
        'funnel': get_funnel(),
    }


@app.get('/api/products')
def products(limit: int = 25, category: str | None = None, q: str | None = None) -> dict[str, Any]:
    return {'products': get_all_products(limit=limit, category=category, query=q)}


@app.get('/api/products/search')
def search_products(q: str | None = None, limit: int = 12) -> dict[str, Any]:
    if not q or not q.strip():
        return {'products': []}
    return {'products': get_all_products(limit=limit, query=q)}


@app.get('/api/products/{product_id}')
def product_detail(product_id: str) -> dict[str, Any]:
    return get_product_detail(product_id)


@app.get('/api/products/{product_id}/price-history')
def product_price_history(product_id: str) -> dict[str, Any]:
    return {'product_id': product_id, 'history': get_price_history(product_id)}


@app.get('/api/users')
def users(q: str | None = None, limit: int = 25) -> dict[str, Any]:
    return {'users': get_users(limit=limit, query=q)}


@app.get('/api/users/{user_id}/activity')
def user_activity(user_id: str) -> dict[str, Any]:
    return {'user_id': user_id, 'events': get_user_activity(user_id)}


@app.get('/api/users/{user_id}/recommendations')
def user_recommendations(user_id: str) -> dict[str, Any]:
    recommendations = get_recommendations_for_user(user_id)
    if recommendations is None:
        raise HTTPException(status_code=404, detail='User ID was not found in processed data.')
    return {'user_id': user_id, 'recommendations': recommendations}


@app.get('/api/analytics/browsing-insights')
def browsing_insights(limit: int = 50) -> dict[str, Any]:
    return {'items': get_browsing_insights(limit=limit)}


@app.get('/api/recommendations/alternatives')
def alternatives(product_id: str, budget: float | None = None, limit: int = 10) -> dict[str, Any]:
    result = get_affordable_alternatives(product_id, budget=budget, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail='Product ID was not found in processed data.')
    return result


@app.get('/api/recommendations/bundles')
def bundles() -> dict[str, Any]:
    return {'bundles': get_bundle_recommendations()}


@app.get('/api/analytics/events')
def analytics_events() -> dict[str, Any]:
    return {'event_counts': get_event_analytics()}


@app.get('/api/analytics/categories')
def analytics_categories() -> dict[str, Any]:
    return {'categories': get_category_analytics()}


@app.get('/api/analytics/funnel')
def analytics_funnel() -> dict[str, Any]:
    return get_funnel()


@app.get('/api/analytics/purchase-insights')
def purchase_insights() -> dict[str, Any]:
    return get_purchase_insights()


@app.get('/api/watchlist')
def watchlist() -> dict[str, Any]:
    return {'items': get_watchlist_store()}


@app.post('/api/watchlist')
def add_watchlist(product_id: str) -> dict[str, Any]:
    items = get_watchlist_store()
    if product_id not in items:
        items.append(product_id)
    save_watchlist_store(items)
    return {'items': items}


@app.delete('/api/watchlist/{product_id}')
def remove_watchlist(product_id: str) -> dict[str, Any]:
    items = get_watchlist_store()
    items = [item for item in items if item != product_id]
    save_watchlist_store(items)
    return {'items': items}


@app.get('/api/budget')
def budget() -> dict[str, Any]:
    return get_budget_store()


@app.put('/api/budget')
def set_budget(payload: BudgetRequest) -> dict[str, Any]:
    save_budget_store(payload.model_dump())
    return {'success': True, 'budget': payload.model_dump()}


@app.get('/api/shopping-plan')
def shopping_plan() -> dict[str, Any]:
    return {'items': get_shopping_plan_store()}


@app.post('/api/shopping-plan')
def add_shopping_plan(payload: ShoppingPlanRequest) -> dict[str, Any]:
    items = get_shopping_plan_store()
    items.append({
        'product_id': payload.product_id,
        'quantity': payload.quantity,
        'observed_price': payload.observed_price,
    })
    save_shopping_plan_store(items)
    return {'items': items}


@app.delete('/api/shopping-plan/{product_id}')
def delete_shopping_plan(product_id: str) -> dict[str, Any]:
    items = get_shopping_plan_store()
    items = [item for item in items if item.get('product_id') != product_id]
    save_shopping_plan_store(items)
    return {'items': items}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('backend.app.main:app', host=APP_HOST, port=APP_PORT, reload=False)
