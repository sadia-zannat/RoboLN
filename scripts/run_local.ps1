$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot\..\backend"
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency install failed' }
alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
Write-Host 'Start backend in a separate terminal: cd backend; python -m uvicorn app.api:app --host 127.0.0.1 --port 8000'
Set-Location ..\frontend
if (-not (Test-Path 'package-lock.json')) { npm install; if ($LASTEXITCODE -ne 0) { throw 'npm registry/install unavailable' } }
npm ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
npm run lint
if ($LASTEXITCODE -ne 0) { throw 'lint failed' }
npm run typecheck
if ($LASTEXITCODE -ne 0) { throw 'typecheck failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'production build failed' }
npm run dev
