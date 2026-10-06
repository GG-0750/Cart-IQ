from pathlib import Path

import pandas as pd

from backend.app.data_processing.dataset_inspector import detect_dataset, validate_dataset_file, validate_schema


def test_detect_dataset():
    dataset = detect_dataset('d:/BDA-mini project/CartIQ/data/raw')
    assert dataset is not None
    assert dataset.endswith('.csv.gz')


def test_validate_schema():
    schema = {
        'event_time': 'string',
        'event_type': 'string',
        'product_id': 'string',
        'price': 'double',
        'user_id': 'string',
        'category_id': 'string',
    }
    missing = validate_schema(schema)
    assert 'event_time' not in missing
    assert 'price' not in missing


def test_validate_dataset_file_reports_missing_required_and_invalid_rows(tmp_path):
    header_csv = tmp_path / 'invalid.csv'
    header_csv.write_text('event_time,event_type,product_id,price\n2024-01-01 00:00:00,view,p1,10\nnot-a-ts,view,p2,abc\n', encoding='utf-8')

    result = validate_dataset_file(header_csv)

    assert result['valid'] is False
    assert 'user_id' in result['missing_columns']
    assert result['summary']['invalid_rows'] >= 1


def test_validate_dataset_file_handles_missing_path():
    result = validate_dataset_file(Path('data/raw/definitely_missing.csv'))
    assert result['valid'] is False
    assert 'error' in result
