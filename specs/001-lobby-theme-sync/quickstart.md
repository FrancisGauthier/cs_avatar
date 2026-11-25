# Quickstart: Lobby Theme Sync

This guide describes the intended local validation flow after the implementation
scaffold and its package manifests are created. The repository currently has no
application code or dependency manifests.

## Prerequisites

- Python 3.12 or newer and `uv`
- Node.js 22.12 or newer and npm
- Docker with Compose, or a PostgreSQL 17+ instance
- A Steam account and a registered Steam OpenID return URL for manual sign-in
  testing; local automated tests use a test-only identity fixture and never
  require Steam credentials

## Local setup

1. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   ```

2. Configure untracked local environment values for the database URL, the
   public application origin, the Steam OpenID realm/return URL, and a
   high-entropy session secret. Never put Steam credentials or session secrets
   in source control. No Steam Web API key is required.

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

   The local proxy must expose the backend and WebSocket endpoint on the SPA's
   same origin and allow only the configured development origin.

## Validation commands

Run focused backend, frontend, type-check, and browser tests:

```powershell
Set-Location backend
uv run pytest

Set-Location ..\frontend
npm run test -- --run
npm run typecheck
npm run e2e
```

Expected outcomes: all suites pass; HTTP and WebSocket requests without a valid
Steam-backed session are rejected; simultaneous duplicate-name submissions
leave exactly one assignment; a roster cannot exceed ten approved players;
committed changes reach all authorized connected clients within five seconds;
unauthorized origins and non-members receive no private roster data.

## End-to-end scenarios

1. Sign in with Steam in two isolated browser contexts. Create a themed roster
   in the first context and request entry from the second. Approve the request,
   select distinct names and theme avatars, and verify both clients show the
   same roster and readiness state.
2. Submit the same normalized name concurrently from two participants. One
   update succeeds and the other receives a conflict without changing the
   existing assignment.
3. Attempt to connect from an unapproved origin, use an expired session, and
   subscribe as a removed/non-member Steam identity. Each attempt is rejected
   without exposing private roster content.
4. Revoke the invitation and verify new requests are rejected. Close the roster
   and verify all participant sessions lose access and the roster data is
   deleted. In a database-backed integration test, advance the clock past 24
   hours of inactivity and verify expiry cleanup.

For HTTP paths and schemas see [contracts/openapi.yaml](./contracts/openapi.yaml);
for the socket handshake and events see [contracts/websocket.md](./contracts/websocket.md).
