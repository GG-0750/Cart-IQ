# CartIQ

CartIQ is a real-data e-commerce analytics dashboard built around the Kaggle multi-category e-commerce behavior dataset. It combines a Spark-based pipeline, a FastAPI backend, and a React dashboard to surface browsing, price, recommendation, budget, and purchase insights derived from the actual events in `data/raw/`.

## Real data policy

- The authoritative source is the raw dataset in `data/raw/`.
- The app does not synthesize users, products, purchases, prices, or sessions.
- Recommendation, alternative, and bundle logic are calculated from observed events and user behavior within the loaded dataset.
- If the dataset does not contain enough evidence for a feature, the UI shows an empty or insufficient-data state instead of inventing values.

## Dataset source

- Kaggle e-commerce events dataset
- Local file detected in this workspace: `data/raw/2019-Oct.csv.gz`
- Required columns checked by validation: `event_time`, `event_type`, `product_id`, `price`, `user_id`
- Optional columns also used when present: `category_id`, `category_code`, `brand`, `user_session`

## Architecture

- `backend/app`: FastAPI backend, service layer, validation, analytics, and recommendation logic
- `backend/app/data_processing`: Spark-based processing and dataset validation
- `frontend/src`: React + TypeScript dashboard and page components
- `data/raw`: source Kaggle export
- `data/processed/cleaned_events`: processed Parquet output created from the raw events
- `scripts`: dataset inspection and preparation helpers
- `tests`: regression tests for recommendations, budget, bundles, search, and dataset validation

## Local setup

### Windows

```powershell
cd "d:/BDA-mini project/CartIQ"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

## Data processing

```powershell
cd "d:/BDA-mini project/CartIQ"
.\.venv\Scripts\Activate.ps1
python scripts/inspect_dataset.py
python scripts/prepare_data.py
```

The project uses a bounded Spark sample for the processed analytics output. The full raw file is large, so the app validates and processes a manageable sample (`DEFAULT_SAMPLE_ROWS`), which is still based on real Kaggle records.

## Backend startup

```powershell
cd "d:/BDA-mini project/CartIQ"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

## Frontend startup

```powershell
cd "d:/BDA-mini project/CartIQ/frontend"
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Application features

- Overview and funnel metrics from processed data
- Real-user recommendation engine using observed product/category interest
- Browsing insights based on repeated views without purchases in the loaded observation window
- Product search and product detail views
- Price-history tracking from observed event prices
- Affordable alternative ranking by category and budget constraints
- Budget planner persisted in local backend state
- Smart bundles built from actual co-purchase sessions
- Purchase-insight summaries based on session behavior
- Data Explorer with bounded previews and validation summaries
- Settings and watchlist/shopping plan controls backed by persisted state

## Recommendation and bundle logic

- Recommendations are scored from actual user behavior: view, cart, and purchase activity plus category affinity.
- Bundle logic groups actual purchase events by `user_session` and counts pair co-occurrence only within each session.
- The app avoids synthetic or hardcoded product IDs and does not fabricate price discounts.

## Dataset validation and limitations

- Validation checks required columns, duplicate rows, invalid timestamps, invalid prices, and event distribution.
- For the large Kaggle export, validation is intentionally bounded to a real sample of rows to keep the app responsive.
- Full dataset processing is not claimed unless the full run is explicitly executed in the environment.
- Spark processing is still the primary pipeline, but the app is designed to operate safely on a large real dataset without loading all rows into the browser.

## Testing

```powershell
cd "d:/BDA-mini project/CartIQ"
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## Frontend build

```powershell
cd "d:/BDA-mini project/CartIQ/frontend"
npm run build
```

## Notes

- The system operates on local data and does not claim live marketplace pricing.
- Budget, watchlist, and shopping-plan state is user configuration and is kept separate from raw Kaggle records.
- The app intentionally shows honest empty states when a metric or relationship is absent from the loaded dataset.
