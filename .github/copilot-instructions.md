# SAT-SA Workspace

- Use SQLite for local persistence; do not introduce PostgreSQL for the MVP.
- Keep analytics evidence-backed and deterministic so uploaded CSV analysis remains reliable offline.
- Preserve the separation between FastAPI routers, SQLAlchemy models, analytics engine, React pages/components, and report generation.
- Prefer focused validation: backend compile/API smoke checks and `npm run build`.
