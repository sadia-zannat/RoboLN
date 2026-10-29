# RoboLN — known limitations

**Not a completed product.** Frontend modules and npm lockfile are absent from the container; Next build and browser/UI testing blocked. GitHub write integration returned HTTP 403 and public `sadia-zannat/RoboLN` remained empty when checked.

API, SQLite and password/session/project isolation tests are development-only, not production security certification. No emailed verification/password reset, production Postgres/HTTPS, durable file/media storage, authenticated IoT gateway, real device, Meta model, 3D WebGL assembly, video camera or speech recognition has been field-tested. Unauthorized project responses are client-rendered with guarded API access; proper server-rendered HTTP 403/404 route statuses remain to verify/repair with Next running.

Camera, AI, CAD, telemetry and actuation features are intentionally NOT available rather than manufactured. Mobile layout, WCAG contrast, theme visual quality, route history, session refresh and browser screenshot assertions are still unverified. The new Playwright tests remain authored but unexecuted.

For security: run npm/pip dependency scanning and deeper IDOR/CSRF tests in a deployed HTTPS environment before release. Current demo data and simulation must never be called physical evidence. Geographic/license checks apply per Meta model/host. No payments or external provider calls were made.
