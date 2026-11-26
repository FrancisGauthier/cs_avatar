# Implementation Plan: Steam Account Login

**Branch**: `002-steam-login` | **Date**: 2026-11-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-steam-login/spec.md`

## Summary

Build Steam OpenID 2.0 sign-in and Steam Web API profile display. After verifying
the Steam assertion, the backend looks up the verified Steam ID, retains only
the nickname and profile image URL for the session lifetime, and exposes those
fields through the authenticated-session contract. The SPA renders the profile
and a neutral fallback when public profile data is unavailable. The Steam Web
API key remains server-side.

## Technical Context

**Language/Version**: Python 3.12+; TypeScript with strict compiler options

**Primary Dependencies**: FastAPI/Starlette; React and Vite; SQLAlchemy 2 async,
asyncpg, and Alembic; a Python OpenID 2.0 relying-party library selected only
after a security and maintenance review; an asynchronous HTTP client for Steam
Web API calls.

**Storage**: PostgreSQL 17+; an authenticated-session record stores a minimal
Steam profile snapshot and expires 12 hours after sign-in.

**Testing**: pytest for backend unit/integration tests; Vitest for frontend
unit/component tests; Playwright for browser-level sign-in and profile flows.
Automated tests use mocked Steam OpenID and Web API responses.

**Target Platform**: Modern desktop/mobile browsers; Python ASGI service on a
Linux host behind an HTTPS reverse proxy. Serve the SPA and API under one site
origin.

**Project Type**: Greenfield web application in one repository, with the
Python ASGI backend and TypeScript SPA under the root `src/` directory.
Application source and dependency manifests have not yet been scaffolded.

**Performance Goals**: Profile lookup is bounded by an explicit request timeout;
Steam-controlled response time is outside the application's latency guarantee.
The profile snapshot avoids repeat lookups during the active session.

**Constraints**: Steam browser sign-in uses OpenID 2.0, not OpenID Connect. Only
the server may call Steam Web API with its secret key. Accept profile data only
for the Steam ID returned by verified OpenID sign-in. Validate provider
responses, allow only HTTPS Steam profile-image hosts, and never log API keys or
credential-bearing request URLs. Retain profile data only for the 12-hour
session lifetime. Do not select an OpenID package solely because it is
OpenID-Connect-certified.

**Scale/Scope**: One player profile lookup per successful sign-in; no separate
profile service, permanent profile table, account linking, or additional Steam
game/profile data.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Design response | Gate |
|-----------|-----------------|------|
| I. Security First | Verify Steam OpenID server-side; keep the Steam Web API key out of the SPA and logs; validate profile results against the verified Steam ID. | PASS |
| II. Complete Input Validation | Validate the Steam ID, Web API response shape, nickname, and image URL at the backend boundary; treat missing or invalid profile data as unavailable. | PASS |
| III. SPA-First Architecture | Keep profile presentation in the SPA; use the backend only for trusted OpenID verification and the secret-bearing Steam Web API call. | PASS |
| IV. Testable Contracts | Define login, callback, and session response contracts; test valid, mismatched, malformed, missing, and unavailable profile responses. | PASS |
| V. Simplicity and Maintainability | Use one authenticated-session model and one Steam profile lookup boundary; do not add a separate profile store or service. | PASS |
| VI. Counter-Strike 2 Brand and Theme Consistency | Match the sign-in control and profile presentation to the product's CS2-inspired design; clearly state that the app is not affiliated with Steam or Valve. | PASS |
| VII. Repository Structure | Keep application source under root `src/`, tests under `tests/`, infrastructure under `infra/`, and Spec Kit artifacts under `specs/`. | PASS |

No constitution violations require an exception.

**Post-design gate**: PASS. The backend work is limited to secure identity
verification and a server-only profile lookup; profile data is minimized and
expires with the authenticated session. The SPA remains responsible for
presentation.

## Project Structure

### Documentation (this feature)

```text
specs/002-steam-login/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── steam-web-api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── cs_avatar/
│   ├── api/                     # session response includes profile fields
│   ├── auth/                    # Steam OpenID, profile lookup, session logic
│   ├── migrations/versions/     # session-profile schema change
│   └── persistence/             # SQLAlchemy models and database access
└── frontend/
    ├── app/                     # authenticated account area
    └── features/auth/           # Steam button, status, and profile view

tests/
├── backend/
│   ├── auth/                    # OpenID and Steam API adapter tests
│   └── integration/             # session and callback contracts
└── frontend/
    ├── e2e/                     # browser-level sign-in and profile flows
    └── features/auth/           # component tests

infra/
└── compose.yaml                 # local PostgreSQL service
```

**Structure Decision**: Treat this as a greenfield two-part web application.
The React/Vite SPA under `src/frontend/` initiates Steam sign-in and displays
the session profile. The FastAPI service under `src/cs_avatar/` validates the
Steam OpenID 2.0 callback, calls Steam Web API with a server-only key, and
returns a minimal profile snapshot from the same-origin session endpoint.

## Complexity Tracking

No constitution violations.
