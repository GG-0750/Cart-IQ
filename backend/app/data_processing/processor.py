from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from backend.app.config import DATA_DIR, DEFAULT_SAMPLE_ROWS, RAW_DATA_DIR
from backend.app.data_processing.dataset_inspector import detect_dataset, validate_dataset_file

PROCESSED_DIR = DATA_DIR / 'processed'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def safe_write_parquet(df, output_dir: str | Path) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    try:
        df.write.mode('overwrite').parquet(str(path))
    except Exception:
        pandas_df = df.toPandas()
        if pandas_df.empty:
            return
        file_path = path / 'part-00000.parquet'
        table = pa.Table.from_pandas(pandas_df)
        pq.write_table(table, str(file_path))


def get_spark() -> SparkSession:
    return SparkSession.builder \
        .appName('CartIQ-processor') \
        .master('local[*]') \
        .config('spark.sql.shuffle.partitions', '4') \
        .config('spark.sql.execution.arrow.pyspark.enabled', 'false') \
        .config('spark.hadoop.fs.file.impl', 'org.apache.hadoop.fs.LocalFileSystem') \
        .config('spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version', '2') \
        .getOrCreate()


def process_real_dataset(
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
    dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    dataset_path = str(dataset_path) if dataset_path else detect_dataset(RAW_DATA_DIR)
    if not dataset_path:
        return {'success': False, 'error': 'Dataset not detected in data/raw/.', 'real_data_used': False}

    validation = validate_dataset_file(dataset_path)
    if not validation.get('valid'):
        return {'success': False, 'error': validation.get('error'), 'real_data_used': False}

    spark = get_spark()
    df = spark.read.option('header', 'true').option('inferSchema', 'false').csv(dataset_path)
    required = ['event_time', 'event_type', 'product_id', 'price', 'user_id']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return {'success': False, 'error': f'Required column missing: {missing[0]}', 'real_data_used': False}

    df = df.na.drop(subset=['event_time', 'event_type', 'product_id', 'price', 'user_id'])
    df = df.withColumn('event_time', F.to_timestamp(F.col('event_time').cast('string'), 'yyyy-MM-dd HH:mm:ss z'))
    df = df.withColumn('event_type', F.lower(F.col('event_type').cast('string')))
    df = df.withColumn('product_id', F.col('product_id').cast('string'))
    df = df.withColumn('user_id', F.col('user_id').cast('string'))
    df = df.withColumn('price', F.col('price').cast('double'))
    df = df.filter(F.col('price').isNotNull())
    if sample_rows and sample_rows > 0:
        df = df.limit(sample_rows)

    cleaned_path = PROCESSED_DIR / 'cleaned_events'
    safe_write_parquet(df, cleaned_path)

    processed_rows = int(df.count())
    summary = {
        'success': True,
        'processing_mode': 'sample' if sample_rows and sample_rows > 0 else 'full',
        'real_data_used': True,
        'source_file': dataset_path,
        'processed_rows': processed_rows,
        'sample_size': processed_rows,
        'output_path': str(cleaned_path),
        'event_distribution': json.loads(df.groupBy('event_type').count().orderBy(F.col('count').desc()).toPandas().to_json(orient='records')),
        'schema': df.columns,
    }
    return summary
