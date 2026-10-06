from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COLUMNS = ['event_time', 'event_type', 'product_id', 'price', 'user_id']
OPTIONAL_COLUMNS = ['category_id', 'category_code', 'brand', 'user_session']


def detect_dataset(raw_dir: str | Path | None = None) -> str | None:
    target = Path(raw_dir) if raw_dir is not None else Path('data/raw')
    if not target.exists():
        return None

    candidates = []
    for child in sorted(target.iterdir()):
        if child.is_file():
            name = child.name.lower()
            if name.endswith('.csv') or name.endswith('.csv.gz') or name.endswith('.parquet') or name.endswith('.tsv'):
                candidates.append(str(child))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: ('.csv.gz' not in p, p))[-1]


def validate_schema(columns: Iterable[str]) -> list[str]:
    column_names = {str(item).strip() for item in columns if str(item).strip()}
    return [col for col in REQUIRED_COLUMNS if col not in column_names]


def normalize_event_type(value: Any) -> str:
    if value is None:
        return ''
    normalized = str(value).strip().lower()
    mapping = {
        'add_to_cart': 'cart',
        'remove_from_cart': 'remove_from_cart',
        'purchase': 'purchase',
        'view': 'view',
        'cart': 'cart',
        'remove': 'remove_from_cart',
    }
    return mapping.get(normalized, normalized)


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(',', '')
    if text in ('', 'nan', 'NaN', 'null', 'None'):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(' UTC'):
        text = text.replace(' UTC', '')
    return text


def read_csv_header(path: str | Path) -> list[str]:
    file_path = Path(path)
    opener = gzip.open if str(file_path).lower().endswith('.gz') else open
    with opener(file_path, 'rt', encoding='utf-8', newline='') as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration:
            return []


def inspect_dataset(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    file_size = file_path.stat().st_size if file_path.exists() else 0
    schema = read_csv_header(file_path)
    required_missing = validate_schema(schema)
    return {
        'file_name': file_path.name,
        'file_path': str(file_path),
        'file_type': 'csv.gz' if file_path.name.lower().endswith('.csv.gz') else 'csv' if file_path.name.lower().endswith('.csv') else 'other',
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'schema': schema,
        'required_columns_present': len(required_missing) == 0,
        'missing_required_columns': required_missing,
        'optional_columns': [col for col in OPTIONAL_COLUMNS if col in schema],
    }


def validate_dataset_file(path: str | Path, max_rows: int | None = None) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {'valid': False, 'error': 'Dataset file was not found.', 'missing_columns': REQUIRED_COLUMNS}

    info = inspect_dataset(file_path)
    if not info['schema']:
        return {'valid': False, 'error': 'Dataset header could not be read.', 'missing_columns': REQUIRED_COLUMNS}

    missing = validate_schema(info['schema'])
    opener = gzip.open if str(file_path).lower().endswith('.gz') else open
    # Large Kaggle exports can be very large; validate a bounded sample by default so the app remains responsive
    # while still checking the real dataset structure and field integrity.
    file_size = file_path.stat().st_size if file_path.exists() else 0
    if max_rows is None:
        max_rows = None if file_size < 100 * 1024 * 1024 else 200000

    total_rows = 0
    valid_rows = 0
    invalid_rows = 0
    duplicate_rows = 0
    seen_rows: set[tuple[tuple[str, str], ...]] = set()
    invalid_timestamps: list[str] = []
    invalid_prices: list[str] = []
    event_type_distribution: Counter[str] = Counter()
    unique_users: set[str] = set()
    unique_products: set[str] = set()
    date_values: list[datetime] = []
    sample_limit_reached = False

    try:
        with opener(file_path, 'rt', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if max_rows is not None and total_rows >= max_rows:
                    sample_limit_reached = True
                    break
                total_rows += 1
                row_key = tuple((key, str(value).strip()) for key, value in sorted(row.items()) if value is not None)
                if row_key in seen_rows:
                    duplicate_rows += 1
                    invalid_rows += 1
                    continue
                seen_rows.add(row_key)

                event_type = normalize_event_type(row.get('event_type')) if 'event_type' in (row or {}) else ''
                user_id = str(row.get('user_id', '')).strip() if row is not None else ''
                product_id = str(row.get('product_id', '')).strip() if row is not None else ''
                price = parse_float(row.get('price')) if row is not None else None
                timestamp = parse_timestamp(row.get('event_time')) if row is not None else None

                if missing:
                    if 'user_id' not in row or 'event_type' not in row or 'product_id' not in row or 'price' not in row or 'event_time' not in row:
                        invalid_rows += 1
                        continue

                if not user_id or not product_id or not event_type:
                    invalid_rows += 1
                    continue
                if timestamp is None or not _is_valid_timestamp(timestamp):
                    invalid_rows += 1
                    invalid_timestamps.append(str(row.get('event_time')))
                    continue
                if price is None:
                    invalid_rows += 1
                    invalid_prices.append(str(row.get('price')))
                    continue

                valid_rows += 1
                event_type_distribution[event_type] += 1
                unique_users.add(user_id)
                unique_products.add(product_id)
                try:
                    date_values.append(datetime.fromisoformat(timestamp.replace('Z', '+00:00')))
                except ValueError:
                    pass
    except Exception:
        return {'valid': False, 'error': 'Dataset could not be parsed for validation.', 'missing_columns': missing, 'schema': info['schema']}

    if missing:
        return {
            'valid': False,
            'error': 'Required columns missing: ' + ', '.join(missing),
            'missing_columns': missing,
            'missing_optional_columns': [col for col in OPTIONAL_COLUMNS if col not in info['schema']],
            'schema': info['schema'],
            'summary': {
                'total_rows': total_rows,
                'valid_rows': valid_rows,
                'invalid_rows': invalid_rows,
                'duplicate_rows': duplicate_rows,
                'missing_optional_columns': [col for col in OPTIONAL_COLUMNS if col not in info['schema']],
                'invalid_timestamps': invalid_timestamps[:10],
                'invalid_prices': invalid_prices[:10],
                'event_type_distribution': dict(sorted(event_type_distribution.items())),
                'unique_users': len(unique_users),
                'unique_products': len(unique_products),
                'date_range': {
                    'start': min(date_values).isoformat() if date_values else None,
                    'end': max(date_values).isoformat() if date_values else None,
                },
                'files_processed': [str(file_path)],
                'sampled': sample_limit_reached,
            },
        }

    missing_optional = [col for col in OPTIONAL_COLUMNS if col not in info['schema']]
    summary = {
        'total_rows': total_rows,
        'valid_rows': valid_rows,
        'invalid_rows': invalid_rows,
        'duplicate_rows': duplicate_rows,
        'missing_optional_columns': missing_optional,
        'invalid_timestamps': invalid_timestamps[:10],
        'invalid_prices': invalid_prices[:10],
        'event_type_distribution': dict(sorted(event_type_distribution.items())),
        'unique_users': len(unique_users),
        'unique_products': len(unique_products),
        'date_range': {
            'start': min(date_values).isoformat() if date_values else None,
            'end': max(date_values).isoformat() if date_values else None,
        },
        'files_processed': [str(file_path)],
        'sampled': sample_limit_reached,
    }

    return {
        'valid': invalid_rows == 0,
        'schema': info['schema'],
        'file_name': info['file_name'],
        'missing_columns': missing,
        'missing_optional_columns': missing_optional,
        'summary': summary,
        'error': None if invalid_rows == 0 else 'Dataset validation found invalid rows.',
    }


def _is_valid_timestamp(value: str) -> bool:
    text = str(value).strip().replace(' UTC', '').replace('Z', '+00:00')
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        try:
            datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False


def main() -> None:
    dataset_path = detect_dataset('data/raw')
    print(json.dumps(inspect_dataset(dataset_path) if dataset_path else {'error': 'Dataset not detected'}, indent=2))


if __name__ == '__main__':
    main()
