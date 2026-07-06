# MagCollection

MagCollector is a web app for browsing a personal magazine/comic collection. Magazines live as
files on disk under `collections/<collection name>/`; a Python backend indexes them into SQLite
and serves a React frontend for browsing, reading, and administering the collection.

## Features

- **Multi-format support**: PDF, EPUB, and comic archives (CBZ, CBR, ZIP).
  - PDFs open in the browser's own PDF viewer.
  - EPUBs open in an in-app reader (epub.js) with pagination and a progress indicator.
  - Comic archives open in an in-app page-by-page image reader; pages are extracted
    on demand by the backend (RAR archives via `unrar`/`bsdtar`, ZIP-based archives
    via Python's stdlib `zipfile`).
- **Automatic cover thumbnails**, rendered from the first page/image of each file and cached to disk.
- **Nested subdirectory browsing** within a collection, mirroring the on-disk folder layout.
- **Last-read tracking**: opening a magazine stamps a timestamp, shown as "Last read: DD-MM-YYYY
  HH:MM" (or "Never") on its card.
- **Access control**: per-user group membership plus optional per-magazine owner overrides (see
  [Access model](#access-model)).
- **Admin tools**: user management, a collection scanner (re-syncs `collections/` into the DB),
  and a magazine properties editor (titles, groups, owner overrides).
- **Light/dark theme**, saved per user and applied on every device.

## Project structure

```
backend/
  app/
    main.py         FastAPI routes (auth, browsing, file/thumbnail/page serving, admin)
    scanner.py       Walks collections/ and syncs the magazines + collections DB tables
    comics.py        Lists/reads pages inside CBZ/CBR/ZIP archives
    thumbnails.py    Renders + caches a cover PNG per magazine (PyMuPDF for PDF/EPUB, Pillow for comics)
    db.py            SQLite connection handling + schema/migrations
    auth.py          JWT issuing/verification and the group/owner access-control rule
    users_store.py   User accounts, stored in backend/users.json (not the SQLite DB)
    config.py        Paths, JWT settings, well-known groupIDs
    schemas.py       Pydantic request bodies
  requirements.txt
  users.json         Created on first run (gitignored)
  magcollector.db    Created on first run (gitignored)
  thumbnails/        Cached cover images (gitignored)

frontend/
  src/
    pages/            One component per route (Collections, CollectionView, EpubReader,
                       ComicReader, Login, admin/*, settings/*)
    components/        Shared UI: AppShell, Sidebar, AuthImage, route guards
    auth/               AuthContext (login state, current user, theme)
    api/client.js       Thin fetch wrapper (JSON + auth header + blob downloads)
    styles/tokens.css   Design tokens transcribed from DESIGN.md
    index.css           Global styles and per-page/component CSS

collections/          Your magazine/comic files (see Content structure below)
DESIGN.md             Token-based design spec the UI pulls colors/type/spacing from
```

## Content structure (`collections/`)

Magazines are organized as one subdirectory per title (or series) under `collections/`, containing
the issue files and optionally further subdirectories:

```
collections/<Magazine Title>/<Magazine Title> - Issue <N> - <Month-Month Year>.pdf
collections/<Magazine Title>/<Year>/<Magazine Title> - Issue <N>.pdf
```

Naming isn't perfectly consistent across magazines (e.g. `collections/Skrolli/2026.1.untsunts.pdf`
uses `<year>.<issue>.<title-slug>.pdf` instead). The scanner doesn't try to parse issue metadata
out of filenames — it uses the filename (minus extension) as the default title, which admins can
rename via the magazine properties editor. Supported file extensions: `.pdf`, `.epub`, `.cbz`,
`.cbr`, `.zip`.

## Running locally

### Backend (FastAPI + SQLite, port 8001)

```sh
cd backend
python3 -m venv venv          # first time only
./venv/bin/pip install -r requirements.txt   # first time only
./venv/bin/uvicorn app.main:app --port 8001
```

On first run this creates `backend/users.json` with a seed admin account (`admin` / `admin123` —
change this immediately) and scans `collections/` into `backend/magcollector.db`. The scan also
reruns on every backend startup, and can be triggered manually from the admin Collection Scanner
page.

Comic/document rendering dependencies (installed via `requirements.txt`):

- `pymupdf` — renders the first page of PDF and EPUB files (including laying out EPUB's
  reflowable text) into cover thumbnails.
- `pillow` — renders comic archive page images into cover thumbnails.
- CBR (RAR-based comic archives) additionally shells out to an external tool: whichever of
  `unrar` or `bsdtar` is found first on `PATH`. Install one of them (e.g. `brew install unrar`, or
  `bsdtar`/libarchive, already preinstalled on macOS) if you have `.cbr` files in your collection.

### Frontend (React + Vite, port 5173)

```sh
cd frontend
npm install      # first time only
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8001`, so the two servers must run side by side. Open
http://localhost:5173.

Other frontend scripts: `npm run build` (production build), `npm run lint` (oxlint), `npm run
preview` (serve the production build locally).

## Access model

- Every user (in `backend/users.json`) has a `groupID` and a `role` (`admin` or `user`).
- Every collection and magazine (in the SQLite DB) has a `groupID`, and a magazine can optionally
  have an owner `userID` override.
- A user can see a collection/magazine if their `groupID` matches its `groupID`, if the magazine's
  `userID` override equals their own ID, or if their role is `admin` (bypasses all checks).
- Admin-only tools (sidebar "Administration" section): user management, the collection scanner
  (re-syncs `collections/` into the DB), and the magazine properties editor (titles, groups, owner
  overrides).

## Design system

UI colors, typography, spacing, and named components are defined as tokens in
[`DESIGN.md`](DESIGN.md) and transcribed into `frontend/src/styles/tokens.css`. New UI work should
pull values from those tokens rather than hardcoding hex/px values.
