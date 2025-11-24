# Safety Helmet Monitor

Lightweight Flask app that captures webcam frames in the browser, sends them to a backend for helmet detection, stores results in SQLite, and exposes a dashboard with KPIs and recent snapshots. Uses a pluggable `ModelService` placeholder you can swap with your pretrained model.

## Stack
- Flask + Flask-SQLAlchemy
- SQLite (no external services)
- Vanilla JS frontend (camera capture, dashboard data fetch)

## Project Structure
- `app.py` — Flask app factory and routes
- `services/` — `ModelService` (stub) and `SnapshotService` (persistence/stats)
- `models.py`, `database.py` — ORM model and shared DB instance
- `migrations/001_init.sql` — schema
- `scripts/init_db.py` — run migration into `helmet_monitor.db`
- `templates/`, `static/js/` — minimal pages and JS for camera + dashboard
- `uploads/` — saved snapshots (gitignored)

## Setup
1) Clone and enter the repo.
2) Create env: `python -m venv .venv && source .venv/bin/activate`
3) Install deps: `pip install -r requirements.txt`
4) Initialize DB: `python scripts/init_db.py` (creates `helmet_monitor.db`)
5) Run dev server: `python app.py` then open `http://localhost:8000/`

## Usage
- Camera page (`/`): allow webcam, set interval/site, click Start. Frames are posted to `/api/predict`.
- Dashboard (`/dashboard`): shows KPIs, trend data, composition, and recent events with links to saved images.
- Swap in your model: implement real logic in `services/model_service.py::predict`.

## Contributing
1) Create a branch: `git checkout -b feature/name`
2) Make changes and keep services/tests small and focused.
3) Run checks locally (server start, optional lint/tests).
4) Commit with clear messages: `git commit -m "Add X"`
5) Push and open a PR describing changes and testing done.
