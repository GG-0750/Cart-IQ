from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
PROJECT_ROOT = ROOT_DIR

if os.name == 'nt' and 'HADOOP_HOME' not in os.environ:
    os.environ['HADOOP_HOME'] = r'C:\hadoop'

DEFAULT_SAMPLE_ROWS = int(os.getenv('SAMPLE_ROWS', '200000'))
APP_PORT = int(os.getenv('FASTAPI_PORT', '8001'))
APP_HOST = os.getenv('FASTAPI_HOST', '127.0.0.1')
