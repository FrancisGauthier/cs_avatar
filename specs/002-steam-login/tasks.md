---
description: "Implementation tasks for Steam Account Login"
---

# Tasks: Steam Account Login

**Input**: Design documents from `/specs/002-steam-login/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and
`contracts/`

**Tests**: Focused backend and frontend tests are included because the
constitution requires tests for new security-sensitive boundaries, contracts,
and persistence behavior.

**Organization**: Tasks are grouped by user story so the P1 sign-in journey can
be implemented and validated as an independent increment.

## Phase 1: Setup

**Purpose**: Align the implementation paths with the constitution and establish
the greenfield application workspaces.

- [X] T001 [P] Update the source-code and test directory trees in `specs/002-steam-login/plan.md` to use root `src/`, `tests/`, and `infra/`, keeping Spec Kit artifacts under `specs/`.
- [X] T002 [P] Create the root `pyproject.toml` for Python 3.12+, backend packaging from `src/`, FastAPI, SQLAlchemy, Alembic, and pytest tooling; leave the OpenID dependency for the security review task.
- [X] T003 [P] Create the root `package.json`, `vite.config.ts`, and `tsconfig.json` for the React/TypeScript SPA in `src/frontend/`, including Vitest, Playwright, build, and typecheck scripts.
- [X] T004 [P] Add a local PostgreSQL 17 service and persistent development volume in `infra/compose.yaml`.

## Phase 2: Foundational

**Purpose**: Establish secure configuration, persistence, and application entry
points required by the sign-in story.

- [X] T005 Review OpenID 2.0 relying-party candidates for Steam compatibility, maintenance, security history, and license; record the approved choice or blocking concern in `specs/002-steam-login/research.md` and update `pyproject.toml`.
- [X] T006 Add validated application settings and secret loading in `src/cs_avatar/config.py` and document required non-secret setting names in `.env.example`, including the fixed OpenID callback, session secret, and backend-only Steam Web API key.
- [X] T007 Initialize the FastAPI application, database connection, and migration environment in `src/cs_avatar/main.py`, `src/cs_avatar/persistence/database.py`, `src/cs_avatar/migrations/env.py`, and `alembic.ini`; ensure error logging excludes secrets and credential-bearing URLs.
- [X] T008 [P] Create the React entry point and base application shell in `src/frontend/main.tsx` and `src/frontend/app/App.tsx`.

## Phase 3: User Story 1 - Sign in with Steam and view player profile (Priority: P1) MVP

**Goal**: A signed-out player can securely authenticate through Steam and return
to the app with their Steam nickname and profile picture, or see a clear
fallback/status when profile data is unavailable.

**Independent Test**: In an isolated browser context using mocked Steam
OpenID and Web API responses, start signed out, complete the redirect/callback,
and verify the authenticated session and profile display. Verify separately
that cancellation, invalid assertions, and unavailable profile data never show
an unauthenticated player as signed in.

### Tests for User Story 1

- [X] T009 [P] [US1] Add OpenID initiation and callback tests in `tests/backend/auth/test_steam_openid.py` for valid assertions, cancellation, invalid signatures, mismatched return URLs/identities, expired attempts, and replay rejection.
- [X] T010 [P] [US1] Add Steam profile client tests in `tests/backend/auth/test_steam_profile.py` for matching and mismatched Steam IDs, malformed/missing profile fields, invalid image URLs, timeouts, and secret-safe logging.
- [X] T011 [P] [US1] Add auth route contract tests in `tests/backend/integration/test_auth_routes.py` for login/callback redirects, session cookie flags, authenticated profile responses, and signed-out responses.
- [X] T012 [P] [US1] Add sign-in and profile component tests in `tests/frontend/features/auth/steam-login.test.tsx` for the provider notice, successful profile, missing-avatar fallback, and retryable failure/cancellation status.
- [X] T013 [P] [US1] Add a browser flow using mocked Steam endpoints in `tests/frontend/e2e/steam-login.spec.ts` to verify redirect, return, nickname/avatar display, and no Steam password entry on app pages.

### Implementation for User Story 1

- [X] T014 [US1] Implement persistence models and an Alembic migration in `src/cs_avatar/persistence/models.py` and `src/cs_avatar/migrations/versions/0001_steam_auth.py`; resolve each constraint from [data-model.md](data-model.md): `Steam Identity.steam_id`, `Steam OpenID Attempt.state_digest`, `Steam OpenID Attempt.browser_binding_digest`, `Steam OpenID Attempt.return_to`, `Steam OpenID Attempt.provider_nonce_digest`, `Steam OpenID Attempt.created_at`, `Steam OpenID Attempt.expires_at`, `Steam OpenID Attempt.consumed_at`, `Auth Session.id_digest`, `Auth Session.steam_id`, `Auth Session.persona_name`, `Auth Session.avatar_url`, `Auth Session.profile_status`, `Auth Session.created_at`, `Auth Session.expires_at`, and `Auth Session.revoked_at`.
- [X] T015 [P] [US1] Implement Steam OpenID initiation and verified callback handling in `src/cs_avatar/auth/steam_openid.py`; follow [data-model.md](data-model.md) for `Steam Identity.steam_id`, `Steam OpenID Attempt.state_digest`, `Steam OpenID Attempt.browser_binding_digest`, `Steam OpenID Attempt.return_to`, `Steam OpenID Attempt.provider_nonce_digest`, and `Steam OpenID Attempt.consumed_at`, and create no session for an invalid or cancelled assertion.
- [X] T016 [P] [US1] Implement the server-side `GetPlayerSummaries` client and response validation in `src/cs_avatar/auth/steam_profile.py`; follow [data-model.md](data-model.md) for `Steam Profile API Result.steamid`, `Steam Profile API Result.personaname`, `Steam Profile API Result.avatarfull`, `Auth Session.persona_name`, `Auth Session.avatar_url`, and `Auth Session.profile_status`, keeping the API key out of client code and logs.
- [X] T017 [US1] Implement `/api/v1/auth/steam/login`, `/api/v1/auth/steam/callback`, and `/api/v1/auth/session` in `src/cs_avatar/api/auth.py` to match `contracts/openapi.yaml`, set the secure session cookie only after verified authentication, and return the validated profile snapshot or unavailable status.
- [X] T018 [P] [US1] Implement the same-origin sign-in and session client in `src/frontend/features/auth/api.ts` and response types in `src/frontend/features/auth/types.ts`, matching `contracts/openapi.yaml` without exposing Steam API credentials.
- [X] T019 [P] [US1] Build the prominent Steam sign-in control and pre-redirect affiliation/data-use notice in `src/frontend/features/auth/SteamLogin.tsx` and `src/frontend/features/auth/steam-login.css`, using an authorized Steam sign-in mark and keyboard-accessible behavior.
- [X] T020 [P] [US1] Build the signed-in profile view in `src/frontend/features/auth/SteamProfile.tsx` to render the nickname as text, show the Steam avatar when valid, and use a neutral fallback image when it is unavailable.
- [X] T021 [US1] Connect session restoration, sign-in, profile, cancellation, and retryable error states in `src/frontend/app/App.tsx` using the auth client and components from `src/frontend/features/auth/`.

**Checkpoint**: With the focused tests passing, a player can complete the
Steam sign-in journey independently of any later account-linking or game-data
features.

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Verify operational instructions, provider security, and end-to-end
behavior for the complete increment.

- [X] T022 [P] Update setup commands, required server-only Steam API configuration, and expected results in `specs/002-steam-login/quickstart.md` to match the root `src/`, `tests/`, and `infra/` layout.
- [X] T023 Record the focused OpenID, API-key, logging, callback, and profile-image validation review in `specs/002-steam-login/research.md`.
- [X] T024 Run the commands and end-to-end scenarios in `specs/002-steam-login/quickstart.md` and record verified outcomes and any remaining blockers there.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001-T004 have no prerequisites and can run in parallel.
- **Foundational (Phase 2)**: Starts after Setup. T005 depends on the Python
  manifest in T002; T006 depends on the backend workspace; T007 depends on
  T005-T006; T008 depends on the frontend workspace in T003.
- **User Story 1 (Phase 3)**: Starts after the Foundational phase. Write tests
  T009-T013 first; then implement persistence, OpenID, Steam profile lookup,
  routes, and SPA integration.
- **Polish (Phase 4)**: T022-T024 follow story implementation; T024 depends on
  the completed quickstart instructions and security review.

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Setup and Foundational phases. It is
  the sole story and is independently testable with mocked provider responses.

### Within User Story 1

- Tests T009-T013 are written before implementation and initially fail.
- T014 provides persistence required by T015-T017.
- T015 and T016 can proceed in parallel after T014; T017 integrates them.
- T018 can proceed alongside backend work after T008. T019 and T020 can proceed
  in parallel after T018; T021 integrates the UI and backend session flow.

### Parallel Opportunities

- Setup tasks T001-T004 use separate files and can run concurrently.
- Foundational T005/T006 and T008 can proceed concurrently after their
  respective setup prerequisites; T007 follows T005 and T006.
- Story tests T009-T013 use separate test files and can be authored in parallel.
- Story implementation T015/T016 and T018 can proceed concurrently after T014
  and frontend setup, respectively.
- UI components T019/T020 can be built in parallel after the auth client T018.
- Polish documentation tasks T022/T023 touch separate feature documents.

## Parallel Example: User Story 1

```text
After foundational setup, author the isolated tests in parallel:
Task: T009 OpenID callback tests in tests/backend/auth/test_steam_openid.py
Task: T010 Steam profile client tests in tests/backend/auth/test_steam_profile.py
Task: T011 Auth route contract tests in tests/backend/integration/test_auth_routes.py
Task: T012 Auth component tests in tests/frontend/features/auth/steam-login.test.tsx
Task: T013 Browser flow in tests/frontend/e2e/steam-login.spec.ts

After T014 creates the shared persistence model, parallelize service/client work:
Task: T015 Steam OpenID service in src/cs_avatar/auth/steam_openid.py
Task: T016 Steam profile API client in src/cs_avatar/auth/steam_profile.py
Task: T018 SPA auth client in src/frontend/features/auth/api.ts
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases, including the OpenID library review.
2. Write and run the focused User Story 1 tests; keep them failing until the
   corresponding behavior is implemented.
3. Implement the Steam identity/session persistence, OpenID callback, Steam
   profile lookup, API contract, and SPA sign-in/profile display.
4. Validate User Story 1 independently using mocked provider responses and the
   manual Steam-account quickstart flow.
5. Complete the focused security review and record the result.

### Incremental Delivery

The feature contains one P1 story. Deliver the sign-in button, verified Steam
authentication, and nickname/avatar display together as the MVP; account
linking, sign-out, other providers, and additional Steam data remain out of
scope.

## Notes

- `[P]` means tasks use separate files and have no dependency on unfinished work.
- `[US1]` maps each story-phase task to the P1 journey in `spec.md`.
- Every task includes a concrete repository path; data-model constraints are
  cited by entity and field in their implementing tasks.
- Spec Kit artifacts remain under `specs/`; application source, tests, and
  infrastructure use `src/`, `tests/`, and `infra/` per Principle VII.
