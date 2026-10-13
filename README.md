# InsightAI — AI-Powered Business Intelligence & Data Analytics Copilot

Portfolio project: upload a business dataset, get automatic profiling and cleaning,
then (in later phases) ask natural-language questions that turn into validated SQL,
charts, evidence-based AI insights, anomaly detection, and forecasting.

This repo is being built **phase by phase**, matching the 6-phase spec. This drop
contains a working **Phase 1: Data Foundation**.

## Architecture

```
insightai/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── main.py          App entrypoint, CORS, startup
│   │   ├── config.py        Settings (env vars)
│   │   ├── database.py      SQLAlchemy engine/session (SQLite by default)
│   │   ├── models/          ORM models: Dataset, DatasetColumn
│   │   ├── schemas.py       Pydantic request/response models
│   │   ├── routers/         API routes (datasets: upload/preview/profile/clean)
│   │   └── services/
│   │       ├── storage.py           Persists uploaded rows into their own DB table
│   │       ├── data_profiling.py    Type inference, missing values, quality score
│   │       └── data_cleaning.py     Duplicate removal, missing-value handling
│   ├── sample_data/sales_sample.csv
│   ├── tests/                pytest suite (API + service level)
│   └── requirements.txt
└── frontend/                 React + TypeScript + Vite + Tailwind
    └── src/
        ├── pages/UploadExplore.tsx     Upload → preview → quality → clean flow
        ├── components/                 DataPreview, ColumnProfileTable, QualityScore, Sidebar
        ├── api/client.ts                Axios client for the backend
        └── types/dataset.ts
```

### Why this stack
- **FastAPI + Pydantic**: async-friendly, auto-generated OpenAPI docs at `/docs`, strong typing matches the "no hardcoded/fake results" requirement — every response is a validated schema built from real computation.
- **SQLAlchemy + SQLite (dev) / PostgreSQL (prod)**: the ORM layer is DB-agnostic. Locally this runs on SQLite with zero setup; the Phase 6 Docker Compose swaps in Postgres by changing one env var (`DATABASE_URL`), no code changes needed.
- **Each uploaded dataset gets its own physical table** (`storage_table_name`), created dynamically from the DataFrame's inferred schema. This is what lets Phase 2's NL→SQL engine run **real SQL against real tables**, instead of faking query results.
- **Pandas for profiling/cleaning**: type inference, missing-value %, duplicate detection, and a computed data-quality score (0–100, weighted from completeness + duplicate rate + type consistency) — all derived from the actual file, nothing hardcoded.
- **DuckDB** is in `requirements.txt` now and will be wired in during Phase 2 for fast analytical (OLAP-style) querying on top of the stored tables, without needing a heavier warehouse.
- **React + TypeScript + Vite + Tailwind**: fast dev loop, typed API contracts shared conceptually with the Pydantic schemas, easy to extend with Recharts in Phase 3.

## Database schema (Phase 1)

**datasets**
| column | type | notes |
|---|---|---|
| id | int PK | |
| name | string | |
| original_filename | string | |
| file_type | string | csv \| xlsx |
| storage_table_name | string unique | the dynamically-created data table |
| row_count / column_count | int | |
| quality_score | float | 0–100 |
| status | string | uploaded → profiled → cleaned (or error) |
| error_message | text nullable | |
| created_at / updated_at | datetime | |

**dataset_columns** (one row per column per dataset)
| column | type | notes |
|---|---|---|
| id | int PK | |
| dataset_id | FK → datasets | |
| name | string | |
| inferred_type | string | numeric \| categorical \| datetime \| boolean \| text |
| missing_count / missing_pct | int / float | |
| unique_count | int | |
| sample_values | JSON | |
| stats | JSON | min/max/mean/std for numeric, top values for categorical |

## API (Phase 1)

- `POST /api/datasets/upload` — multipart CSV/XLSX upload, validates file type/size, infers schema, creates the storage table, profiles it, computes quality score.
- `GET /api/datasets/` — list uploaded datasets.
- `GET /api/datasets/{id}` — dataset detail + column profiles.
- `GET /api/datasets/{id}/preview?limit=` — paginated row preview from the real stored table.
- `POST /api/datasets/{id}/clean` — applies missing-value strategy + duplicate removal, re-profiles, updates quality score and status.
- Interactive docs: `http://localhost:8000/docs`

## Running it

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
API: http://localhost:8000  •  Docs: http://localhost:8000/docs

Run tests:
```bash
pytest -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
UI: http://localhost:5173

### Try it fast
Upload `backend/sample_data/sales_sample.csv` (Date, Product, Region, Sales, Profit) through the UI or:
```bash
curl -F "file=@backend/sample_data/sales_sample.csv" http://localhost:8000/api/datasets/upload
```

## Roadmap (what's next)

| Phase | Status | Contents |
|---|---|---|
| 1. Data Foundation | ✅ this drop | Upload, profiling, cleaning, storage, quality score |
| 2. Analytics Engine | next | NL→SQL, SQL validation/sandboxing (read-only, parameterized, no destructive ops), DuckDB execution, query history |
| 3. Visualization | planned | Auto KPI cards, chart-type suggestion engine, Recharts dashboards, filters/date-range |
| 4. AI Insights & Root Cause | planned | Evidence computed first in Python (period comparisons, dimension breakdowns, correlation/contribution analysis) → only the computed evidence is sent to the LLM to explain, never to invent |
| 5. Anomaly Detection & Forecasting | planned | Statistical (z-score/IQR) + IsolationForest anomaly detection; Prophet/statsmodels/XGBoost forecasting with train/test evaluation and confidence intervals, gated behind a "does this dataset support forecasting" check |
| 6. Production Readiness | planned | JWT auth, multi-dataset management, chat history, saved queries, PDF/CSV export, Docker Compose (Postgres + backend + frontend), CI-ready tests, logging |

Each phase will land as working, tested code — not a plan — following the same pattern as Phase 1.

## Honest limitations of this Phase 1 drop
- Auth is not implemented yet (Phase 6) — there's currently no user separation between datasets.
- SQLite is the default dev DB; Postgres wiring is a one-line env change but hasn't been exercised end-to-end with Docker yet (that's Phase 6).
- The quality score is a simple, transparent weighted formula (completeness, duplication, type consistency) documented in `data_profiling.py` — not a black box.
