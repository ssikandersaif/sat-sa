# SAT-SA Offline Supervisory Assurance

SAT-SA is an offline critical-infrastructure security audit MVP. It ingests alert, case, asset, and entity evidence, detects operational control weaknesses, calculates a weighted six-dimension risk index, and produces evidence-backed supervisory outputs.

## Run locally

### Backend

```powershell
.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`, select **Upload four CSVs**, and choose `entities.csv`, `assets.csv`, `alerts.csv`, and `cases.csv`. The backend validates references, replaces the local SQLite dataset, runs the detectors, and refreshes the dashboard.

To regenerate the included large workload:

```powershell
C:/Users/sakata/sat-sa/.venv/Scripts/python.exe data/generate.py
```

The generator creates 12 entities, 96 assets, 25,000 alerts, and more than 13,000 cases. It intentionally includes repeated alerts, missing escalation, fast closures, disabled telemetry, shallow investigations, and copied case narratives so every detector has evidence to inspect.

Ollama is an optional evidence assistant, not the detection engine. Configure `OLLAMA_MODEL` in `.env`; the default is `mistral:7b-instruct`. From a finding's evidence panel, the examiner can request an explanation, recommendation, or show-cause draft. Every output is labeled as AI-generated and requiring human review; offline fallback text remains evidence-backed.

## Project map

- `backend/`: FastAPI, SQLite/SQLAlchemy models, routers, analytics engine, Ollama explainer
- `frontend/`: React/Vite supervisory console with Recharts evidence visualizations
- `data/`: deterministic four-CSV fixture generator
- `reports/`: PDF supervisory report builder
- `docker-compose.yml`: offline local stack

## API highlights

- `GET /api/entities` and `GET /api/entities/{id}` expose scores and findings
- `GET /api/findings` filters supervisory findings
- `GET /api/peers/summary` returns entity-versus-sector medians
- `GET /api/reports/{entity_id}.pdf` exports a report
- `POST /api/ingest/upload` validates and analyzes the four CSV uploads
- `POST /api/ingest/single` accepts one arbitrary incident/log CSV, maps common timestamp/source/status/description fields, and analyzes its rows
- `POST /api/findings/{id}/ai/explain` generates an evidence-grounded explanation
- `POST /api/findings/{id}/ai/recommend` generates a corrective-action draft
- `POST /api/findings/{id}/ai/notice` generates a labeled supervisory notice draft

## Product research applied

The console follows responsive-layout guidance from MDN and web.dev, public-sector component conventions from GOV.UK, IBM Carbon accessibility guidance, and WCAG 2.2 principles: reflow without two-dimensional scrolling, keyboard-capable controls, visible status/error states, non-color-only severity cues, and readable contrast.
