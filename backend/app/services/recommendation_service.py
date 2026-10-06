from __future__ import annotations


def rank_recommendations(records: list[dict]) -> list[dict]:
    cleaned = []
    for record in records:
        score = float(record.get('score', 0.0) or 0.0)
        item = dict(record)
        item['score'] = score
        cleaned.append(item)
    return sorted(cleaned, key=lambda item: (-float(item['score']), str(item.get('product_id', ''))))
