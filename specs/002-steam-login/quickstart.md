# Quickstart: Steam Account Login

This guide validates the Steam sign-in and profile-display increment after the
application scaffold is available.

## Prerequisites

- Python 3.12 or newer and `uv`
- Node.js 22.12 or newer and npm
- Docker with Compose, or a PostgreSQL 17+ instance
- A Steam account and a registered Steam OpenID return URL for manual sign-in
  testing
- A Steam Web API key configured only for the backend; do not commit it or
  expose it to the SPA

Automated tests use mocked OpenID assertions and Steam Web API responses; they
do not require Steam credentials or a live Steam API key.

## Local setup

1. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   ```

2. Create the local environment file and set the session secret and Steam Web
   API key. Configure `STEAM_OPENID_REALM` and `STEAM_OPENID_RETURN_TO` to the
   same public origin as the SPA. Never put Steam credentials, session secrets,
   or the API key in source control.

   ```powershell
   Copy-Item .env.example .env
   ```

3. Install dependencies, apply the database migration, and start the backend:

   ```powershell
   uv sync --extra dev
   uv run alembic upgrade head
   uv run uvicorn cs_avatar.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
   ```

   Uvicorn access logging is disabled because callback query strings contain
   OpenID response data. Configure any reverse proxy to omit or redact query
   strings from access logs as well.

4. In a second terminal, install and start the SPA:

   ```powershell
   npm ci
   npm run dev
   ```

   The Vite development server proxies `/api` requests to the backend on port
   8000, keeping the browser's API and callback origin same-origin.

## Validation commands

```powershell
uv run pytest tests/backend
uv run ruff check src tests

npm run test -- --run
npm run typecheck
npm run build
npm run e2e
```

Install the Playwright browser once before running the browser test:

```powershell
npx playwright install chromium
```

Expected outcomes: valid OpenID assertions create a session for the verified
Steam ID; mismatched, malformed, or rejected assertions do not. Valid profile
summaries display the correct nickname and image. Missing or invalid profile
data keeps the verified session active and displays the documented neutral
fallback with an unavailable status. The API key is absent from browser requests and client bundles; callback query
strings are not written by the configured Uvicorn access logger.

## End-to-end scenarios

1. Sign in with a Steam account and verify that the browser returns to the app
   showing the account nickname and profile picture.
2. Use a test response with no image URL and verify that the app shows the
   nickname and neutral fallback image.
3. Simulate an unavailable Steam Web API and verify that the verified session
   remains active, the fallback and status message appear, and no secret is
   exposed.
4. Return a profile summary for a different Steam ID or with a malformed image
   URL; verify that the data is rejected and never displayed as the
   authenticated player's profile.

For the session response see [contracts/openapi.yaml](./contracts/openapi.yaml);
for the outbound Steam request and validation see
[contracts/steam-web-api.md](./contracts/steam-web-api.md).

## Validation status

The mocked validation run passed: 25 backend tests, Ruff, 4 frontend component
tests, the TypeScript/Vite production build, and the Playwright browser flow.
Alembic generated the PostgreSQL migration SQL successfully in offline mode.
Applying the migration to a live PostgreSQL instance remains unverified because
the Docker Desktop Linux Engine was unavailable. A live Steam sign-in also
remains unverified until a valid server-side API key and a reachable callback
origin are configured.
