# Implementation Plan: Steam App Sign-Out

**Branch**: `003-steam-signout` (planned; current workspace branch: `master`) | **Date**: 2026-11-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-steam-signout/spec.md`

## Summary

Add a sign-out action to the authenticated Steam profile. Revoke the current app session using its existing persisted revocation field, clear the browser session cookie, and return the user to the signed-out experience. Notify other open app tabs and revalidate on browser restoration so they do not continue displaying an authenticated profile. Steam's own browser session remains unchanged; a subsequent sign-in uses Steam's account-switch experience.

## Technical Context

**Language/Version**: TypeScript 5.9 / React 19 for the SPA; Python 3.12+ / FastAPI for the backend

**Primary Dependencies**: Existing React/Vite frontend, FastAPI, SQLAlchemy async, PostgreSQL, pytest, Vitest, Playwright

**Storage**: Existing PostgreSQL `auth_session` records; `revoked_at` already exists and is queried by the current-session endpoint. No new persistent data is expected.

**Testing**: Focused pytest integration tests for logout and session revocation; Vitest component/app tests; Playwright for browser navigation and multi-tab behavior; Ruff and TypeScript checks.

**Target Platform**: Same-origin browser SPA and Python web service on the existing local/production deployment targets

**Project Type**: Web application with SPA frontend and backend API

**Performance Goals**: Sign-out should complete and update the current tab within the specification's five-second success criterion under normal service availability.

**Constraints**: Never claim success if the server cannot confirm completion; do not expose session tokens; preserve the existing Steam session and login flow; return a successful outcome when already signed out; keep user-visible profile state synchronized across app tabs.

**Scale/Scope**: One authenticated profile surface, one app-session revocation operation, and browser tabs sharing the same app origin.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Security First**: Pass. Revoke the persisted session server-side, clear the HttpOnly cookie, and do not log or return the raw token. Do not clear the cookie or show signed-out success after an unconfirmed server error.
- **II. Complete Input Validation**: Pass. Logout accepts no user-supplied identity or session token in its request body; the server acts only on the existing session cookie and treats its absence as already signed out.
- **III. SPA-First Architecture**: Pass with necessary backend work. The server must revoke shared durable session state; tab synchronization and UI reset stay in the SPA.
- **IV. Testable Contracts**: Pass. Define the logout response and idempotent unauthenticated behavior; cover valid, expired/missing, repeated, and failed requests and client tab updates.
- **V. Simplicity and Maintainability**: Pass. Reuse existing session persistence, cookie configuration, session lookup conventions, and test harness. No new dependency or migration.
- **VI. Brand and Theme Consistency**: Pass. Add the action to the existing profile surface using its existing design; preserve independent-Steam messaging.
- **VII. Repository Structure**: Pass. Keep implementation in `src/`, tests in `tests/`, and planning/design artifacts under this Spec Kit feature directory.

**Gate result**: PASS. No constitution exception is required.

### Post-Design Gate

- **Security and validation**: PASS. The endpoint trusts only the optional existing HttpOnly session cookie; it never accepts client-supplied identity data. Failed server confirmation is not presented as success.
- **Architecture and simplicity**: PASS. Persisted revocation is necessary to invalidate a session beyond the current browser tab. Cross-tab notifications and UI state remain client-side; no migration or dependency is introduced.
- **Testability and structure**: PASS. The API behavior and authenticated, repeated, expired, failed, navigation, and multi-tab scenarios are documented for focused tests in canonical source/test/spec locations.

## Project Structure

### Documentation (this feature)

```text
specs/003-steam-signout/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md
```

### Source Code

```text
src/
├── cs_avatar/
│   ├── api/auth.py                         # session revocation and cookie clearing
│   └── persistence/models.py               # existing AuthSession.revoked_at
└── frontend/
    ├── app/App.tsx                         # signed-in/out and cross-tab session state
    └── features/auth/
        ├── api.ts                          # sign-out request
        ├── SteamProfile.tsx                # sign-out action
        └── steam-profile.css               # action styling

tests/
├── backend/integration/test_auth_routes.py # endpoint/session lifecycle
├── frontend/features/auth/                 # focused UI/API behavior tests
└── frontend/e2e/steam-login.spec.ts         # browser flow coverage if suitable
```

**Structure Decision**: Extend the existing Python backend and React SPA auth feature in place. Put tests beside their existing backend/frontend test suites and use the feature directory for planning artifacts. No additional application package or migration is warranted.

## Complexity Tracking

No constitution violations or additional complexity require justification.
