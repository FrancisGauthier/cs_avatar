# Quickstart: Steam Account Login

This guide validates the Steam sign-in and profile-display increment after the
application scaffold is available. The repository currently has no application
source or dependency manifests.

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

2. Configure untracked local environment values for the database URL, public
   application origin, Steam OpenID realm/return URL, session secret, and
   backend-only Steam Web API key. Never put Steam credentials, session
   secrets, or the API key in source control.
3. Install and start the backend:

   ```powershell
   Set-Location backend
   uv sync --extra dev
   uv run alembic upgrade head
   uv run uvicorn cs_avatar.main:app --reload
   ```

4. In a second terminal, install and start the SPA:

   ```powershell
   Set-Location frontend
   npm ci
   npm run dev
   ```

   The local proxy must expose the backend on the SPA's same origin.

## Validation commands

```powershell
Set-Location backend
uv run pytest tests/auth
uv run pytest tests/integration

Set-Location ..\frontend
npm run test -- --run
npm run typecheck
npm run e2e
```

Expected outcomes: valid OpenID assertions create a session for the verified
Steam ID; mismatched, malformed, or rejected assertions do not. Valid profile
summaries display the correct nickname and image. Missing or invalid profile
data keeps the verified session active and displays the documented neutral
fallback with an unavailable status. The API key is absent from browser
requests, client bundles, and application logs.

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
