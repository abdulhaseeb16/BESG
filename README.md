# Breathe ESG Ingestion Review Prototype

A compact Django REST + React prototype for ingesting messy enterprise activity data, normalizing it into an auditable ESG activity model, and letting analysts review rows before audit lock.

## What It Handles

- SAP material-document style CSV exports for fuel and procurement.
- Green Button-style flattened electricity CSV exports.
- Mock SAP Concur itinerary API import for flights, hotels, and ground transport.
- Suspicious-row flagging, source provenance, review events, approval locking, and simple demo multi-tenancy.

## Local Setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 8000
```

Demo user:

- Username: `analyst@breathe.demo`
- Password: `breathe-demo`

### Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Set `VITE_API_BASE_URL` if the backend is not running at `http://127.0.0.1:8000`.

## Render Deployment

The included `render.yaml` deploys the Django app and builds the React static bundle into `backend/static/frontend`. The Django app serves the API and the built frontend from one Render web service.

