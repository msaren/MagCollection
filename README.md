# MagCollection

MagCollector is a web app for browsing a magazine collection. Magazines live as PDF files under
`collections/<collection name>/`; a Python backend indexes them into SQLite and serves a React frontend.

## Running locally

### Backend (FastAPI + SQLite, port 8000)

```sh
cd backend
python3 -m venv venv          # first time only
./venv/bin/pip install -r requirements.txt   # first time only
./venv/bin/uvicorn app.main:app --port 8000
```

On first run this creates `backend/users.json` with a seed admin account (`admin` / `admin123` —
change this immediately) and scans `collections/` into `backend/magcollector.db`.

### Frontend (React + Vite, port 5173)

```sh
cd frontend
npm install      # first time only
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`, so the two servers must run side by side. Open
http://localhost:5173.

## Access model

- Every user (in `backend/users.json`) has a `groupID` and a `role` (`admin` or `user`).
- Every collection and magazine (in the SQLite DB) has a `groupID`, and a magazine can optionally
  have an owner `userID` override.
- A user can see a collection/magazine if their `groupID` matches its `groupID`, if the magazine's
  `userID` override equals their own ID, or if their role is `admin` (bypasses all checks).
- Admin-only tools (sidebar "Administration" section): user management, the collection scanner
  (re-syncs `collections/` into the DB), and the magazine properties editor (titles, groups, owner
  overrides).
