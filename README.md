# RoboLN — Engineering workspace

**RoboLN — Robotics Logic Navigator.** Your AI Engineering Copilot for Building Real Machines.

**Honest state:** A recovered October 24 backend + Next.js App Router source tree, with subsequent Phase 01 security and UI repairs and 8 passing backend integration tests and an Alembic upgrade/downgrade/upgrade check. Frontend production build and Chromium E2E **have not passed** because the runtime could not fetch npm dependencies. Do not use this checkpoint as a production deployment. Existing source is preserved and modified incrementally. Pre-October-26 development is baseline, not new hackathon work.

## Structure
- `backend/app`: FastAPI, SQLAlchemy 2 models, Argon2id, database sessions, CSRF, project RBAC, user preferences, consent and privacy.
- `backend/alembic`: versioned SQLite development migration; production PostgreSQL is **NOT** verified.
- `frontend/app`: Next App Router page files, responsive shells, themes, CRUD forms, navigation. Source exists, but browser rendering unverified.
- `frontend/components`: security guarded project context, nav history, theme and app shell, reusable UI.
- `packages/contracts`: original V2 JSON schemas, held unchanged from user kit. `project_context` schema validated in pytest.
- `tests/e2e`: authored Playwright cases, **unexecuted**.
- `logs`: evidence of actual tests and blocked attempts.

## Local installation (Windows 11 / PowerShell)
1. Install Python 3.13 (3.12 also expected but **not independently tested**) and Node 22.
2. Unzip, open PowerShell inside `RoboLN-v2`.
3. Terminal A:
   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   alembic upgrade head
   python -m pytest -q
   python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
   ```
4. Terminal B:
   ```powershell
   cd frontend
   npm install    # generates real package-lock.json (missing in this PARTIAL checkpoint)
   npm ci
   npm run lint
   npm run typecheck
   npm run build
   npm run dev
   ```
5. Open `http://127.0.0.1:3000/register`; create your own account. No preinstalled password or fake project appears.
6. With both local servers running, in Terminal C run `cd frontend; npm run test:e2e`. Browser binary is required; install via `npx playwright install chromium` if absent.

API uses a Next rewrite `/api/*` to backend `http://127.0.0.1:8000`. HTTP cookies remain scoped to the frontend origin. Never expose this development server directly to the public Internet. Read `KNOWN_LIMITATIONS.md` and `WORK_HANDOFF.md` before progressing.

## Trust boundaries
The user-provided V2 product specification is in the planning kit (not copied into implementation here except JSON schemas). The future assistant, 3D lab, camera, voice, telemetry, simulation and evaluation are **NOT** available in Phase 01. Project hardware fields are **unapproved drafts**, not electrical approval. No cloud API calls, device controls or external deployment were performed.
