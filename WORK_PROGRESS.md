# RoboLN — development history and current Phase 01 progress

## Source precedence
The October 29 Final Master Continuation Prompt supersedes historical restart instructions. The verified October 24 Phase 01 source ZIP is the baseline. Its old ZIP hash is `695909696bd9b300c147ca9981521d1f59d508f885fb15ed9bbd2923df28c0cf` (verified here with Python zipfile and sha256). No V1 source was imported as active source. The baseline source was pre-hackathon; modifications in this checkpoint are new October 29 work, not claimed physical/Meta features.

## Changes executed now
- Strengthened Registration/ProfileEdit/ProjectEdit whitespace validation, bounded hardware pin-map payload and inventory size; rejected writes to archived projects; audited project archive/restore.
- Added two new pytest regression tests, passing with old six.
- Prevented late per-project draft response from overwriting the current project's draft while navigating between projects.
- Added project-context reload event after editing; removed internal phase/version labels from customer-facing views; renamed public Workspace Build navigation to Live Build while preserving the existing /workspace/build URL.
- Added page-specific document titles, navigation dialog Escape handler and search-result close.
- Added authored Playwright tests for project draft isolation and dialog/title flow (not run because npm unavailable).
- Re-ran Python tests, real TCP/Uvicorn HTTP smoke, Alembic roundtrip, TypeScript syntax parser.
- Added a GitHub Actions dependency-lockfile resolver workflow (not run because GitHub write integration rejected, and repository is still empty).
- Prepared a genuine local Git commit history with a distinct imported historical baseline commit and current work commit. No GitHub push/commit succeeded.

## Release state
Phase 01 remains **PARTIAL**. The original dependency lockfile is absent; npm registry DNS returned EAI_AGAIN, and local package cache has no dependencies. npm ci, ESLint, full TypeScript check, Next build, browser Playwright screenshot and accessibility gates cannot pass here. Genuine Meta inference, live hardware and deployment are NOT part of Phase 01 and have not been tested.
