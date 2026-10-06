from __future__ import annotations


def build_bundle_summary(main_product: str, related_products: list[str], prices: dict[str, float]) -> dict:
    observed = []
    for product_id in related_products:
        observed.append(float(prices.get(product_id, 0.0) or 0.0))
    total = sum(observed)
    return {
        'main_product': main_product,
        'related_products': list(related_products),
        'total_observed_price': round(total, 2),
        'prices': {pid: float(prices.get(pid, 0.0) or 0.0) for pid in related_products},
    }
