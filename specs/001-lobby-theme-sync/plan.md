# Implementation Plan: Lobby Theme Sync

**Branch**: `001-lobby-theme-sync` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-lobby-theme-sync/spec.md`

## Summary

Build a TypeScript single-page application backed by one Python ASGI service.
Players authenticate with Steam through its OpenID 2.0 web sign-in, then create
or join private themed rosters. The Python service owns authorization and
validated roster mutations; WebSockets deliver live roster updates. PostgreSQL
stores short-lived authoritative state and provides lightweight cross-worker
notifications, avoiding a separate message broker. Names and avatar assignments
remain manually applied by players in CS2/Steam.

## Technical Context

**Language/Version**: Python 3.12+; current stable TypeScript with strict compiler options

**Primary Dependencies**: FastAPI/Starlette ASGI; React and Vite; SQLAlchemy 2
async, asyncpg, and Alembic; a vetted Python OpenID 2.0 relying-party library
(must pass the security/dependency gate in [research.md](./research.md)).

**Storage**: PostgreSQL 17+ for Steam-backed sessions, rosters, memberships,
assignments, and invitation digests; read-only curated theme catalog and
authorized avatar assets packaged with the application.

**Testing**: pytest for backend unit/integration tests; Vitest for TypeScript
unit/component tests; Playwright for browser-level multi-player flows; PostgreSQL
integration tests for transactional uniqueness and notifications.

**Target Platform**: Modern desktop/mobile browsers; Python ASGI service on a
Linux host behind an HTTPS reverse proxy. Serve the SPA and API under one site
origin; use WSS in production.

**Project Type**: Greenfield web application in a single repository, split into
`frontend/` and `backend/`.

**Performance Goals**: Support ten participants per roster. At least 95% of
committed roster updates must reach connected participants within five seconds,
per SC-003.

**Constraints**: Steam web sign-in is OpenID 2.0, not OAuth 2.0 or OpenID
Connect. Every player action requires an authenticated Steam identity; no
cs_avatar password account is created. Validate all HTTP and WebSocket input at
the server boundary. Use transactional, case-insensitive unique names per
roster. Roster data is deleted on close or after 24 hours of inactivity.
Participants select curated theme assets only; no user uploads or direct
CS2/Steam profile changes. No Steam Web API key or profile lookup is required.

**Scale/Scope**: Ten members maximum per roster; total concurrent rosters are
not specified. Use PostgreSQL notifications so the ASGI service can fan out
updates across workers without adding Redis. PostgreSQL remains the source of
truth; reconnecting clients obtain a fresh authorized snapshot.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Design response | Gate |
|-----------|-----------------|------|
| I. Security First | Verify Steam assertions server-side; use protected sessions, least privilege, private roster access, and authorized theme assets. | PASS |
| II. Complete Input Validation | Validate schemas, lengths, Unicode names, theme/avatar IDs, invitation tokens, and every state-changing request on the server. | PASS |
| III. SPA-First Architecture | Keep screens and interactions in the SPA. The backend is limited to Steam identity verification, authorization, shared state, and real-time delivery required by this feature. | PASS |
| IV. Testable Contracts | Specify HTTP and WebSocket message contracts and test validation, transitions, concurrency, and security boundaries. | PASS |
| V. Simplicity and Maintainability | Use one Python service and PostgreSQL for state and notifications; do not add Redis, an image-upload service, or direct game integration. | PASS |
| VI. Counter-Strike 2 Brand and Theme Consistency | Use a coherent CS2-inspired visual language with original or authorized assets; do not imply official affiliation. | PASS |

No constitution violations require an exception.

**Post-design gate**: PASS. The selected authentication, data, and real-time
boundaries minimize backend scope while keeping identity checks, input
validation, and private roster authorization server-enforced.

## Project Structure

### Documentation (this feature)

```text
specs/001-lobby-theme-sync/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── websocket.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic/
├── src/cs_avatar/
│   ├── api/
│   ├── auth/
│   ├── persistence/
│   ├── realtime/
│   ├── rosters/
│   └── themes/
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

frontend/
├── package.json
├── index.html
├── public/themes/
└── src/
    ├── app/
    ├── components/
    ├── features/auth/
    ├── features/rosters/
    └── lib/
```

**Structure Decision**: Use a two-part web application in one repository. The
React/Vite frontend is a static SPA. The FastAPI service owns Steam OpenID
callbacks, HTTP mutations, session checks, persistence, and WebSocket delivery.
Theme metadata and curated avatar assets are static, versioned application
content. Shared database notifications let each ASGI worker broadcast committed
roster changes to only its own authorized sockets without a second broker.

## Complexity Tracking

No constitution violations.
