---

description: "Task list for Steam app sign-out"

---

# Tasks: Steam App Sign-Out

**Input**: Design documents from `specs/003-steam-signout/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Focused tests are included because session revocation and client/server authentication state require explicit coverage under the project constitution.

**Organization**: Tasks are grouped by user story so the sign-out increment and the subsequent different-account flow can be implemented and verified separately.

## Phase 1: Setup

**Purpose**: Confirm project scaffolding and dependencies.

No setup tasks are required; the application, database, test runners, and lint/type-check commands already exist.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites for all user stories.

No foundational changes are required. The existing `AuthSession.revoked_at` field and auth test fixtures support the feature without a migration or new dependency.

---

## Phase 3: User Story 1 - Sign out of the app (Priority: P1) 🎯 MVP

**Goal**: Let a signed-in player terminate the app session and ensure the previous profile is no longer treated as authenticated in this or another app tab.

**Independent Test**: Sign in, choose **Sign out**, confirm the signed-out experience appears, then reload, revisit through browser history, and verify the old session is rejected. Repeat with an expired or absent session and simulate a server error.

### Tests for User Story 1

- [X] T001 [P] [US1] Add backend integration tests for successful revocation, cookie clearing, current-session rejection, repeated sign-out, and expired or absent sessions in `tests/backend/integration/test_auth_routes.py`
- [X] T002 [P] [US1] Add frontend tests for sign-out success, server failure messaging, cross-tab sign-out notification, and session revalidation after page restoration in `tests/frontend/features/auth/signout.test.tsx`

### Implementation for User Story 1

- [X] T003 [US1] Add an idempotent `POST /api/v1/auth/logout` handler that derives the session from the existing cookie, sets its revocation timestamp, clears that cookie on confirmed completion, and treats missing, expired, or revoked sessions as already signed out in `src/cs_avatar/api/auth.py`; follow `data-model.md` definitions for `AuthSession.id_digest`, `AuthSession.expires_at`, and `AuthSession.revoked_at`
- [X] T004 [P] [US1] Document the optional session-cookie logout request, idempotent `204` response, and unconfirmed server-failure response in `specs/003-steam-signout/contracts/openapi.yaml`
- [X] T005 [P] [US1] Add a typed same-origin sign-out request helper that reports non-success responses instead of returning a success-shaped fallback in `src/frontend/features/auth/api.ts`
- [X] T006 [US1] Add a clearly labeled **Sign out** action to the signed-in profile and wire it to app state; show the signed-out view only after confirmed completion and retain a retryable error state when the request fails in `src/frontend/features/auth/SteamProfile.tsx`, `src/frontend/features/auth/steam-profile.css`, and `src/frontend/app/App.tsx`
- [X] T007 [US1] Synchronize confirmed sign-out with other app tabs and revalidate the session when a tab is restored or returns to the foreground, without broadcasting session tokens or profile data, in `src/frontend/app/App.tsx`

**Checkpoint**: Sign-out is independently usable, idempotent, and does not report success when the server could not confirm revocation.

---

## Phase 4: User Story 2 - Sign in with a different Steam account (Priority: P1)

**Goal**: After app sign-out, allow the existing Steam OpenID flow to establish a new app session for a different verified Steam identity without changing Steam's own browser session.

**Independent Test**: With mocked provider responses, sign in as account A, sign out, complete a new verified callback for account B, and verify the current session returns only account B. Manually confirm the Steam account chooser supports selecting account B in the browser.

### Tests for User Story 2

- [X] T008 [US2] Add a backend integration test that signs in with one verified Steam identity, signs out, completes a new login for a different verified identity, and confirms the current session contains only the second identity in `tests/backend/integration/test_auth_logout.py`

**Checkpoint**: A new verified Steam identity can establish a fresh session after the prior app session is revoked; cancelling the new login leaves the browser signed out.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete behavior against the user-facing scenarios.

- [ ] T009 Run the scenarios in `specs/003-steam-signout/quickstart.md` and fix any failures in the owning source or test files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks; project scaffolding is already present.
- **Foundational (Phase 2)**: No tasks; current session persistence and test fixtures are reusable.
- **User Story 1 (Phase 3)**: Can begin immediately after writing its tests; it provides the sign-out capability required by User Story 2.
- **User Story 2 (Phase 4)**: Depends on User Story 1 being complete because the account-switch journey starts after app sign-out.
- **Polish (Phase 5)**: Depends on both stories being implemented and tested.

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories; this is the MVP.
- **User Story 2 (P1)**: Depends on User Story 1's confirmed session revocation and client sign-out flow. It reuses the existing Steam OpenID login/callback and profile retrieval behavior.

### Within Each User Story

- Write and run the focused tests before their implementations.
- Within User Story 1, backend revocation, API contract documentation, and frontend API helper can proceed in parallel after the tests are in place.
- The signed-in UI wiring depends on the frontend API helper; tab synchronization depends on the signed-in/out state handling.
- Complete User Story 1 before validating the full account-switch cycle in User Story 2.

### Parallel Opportunities

- **User Story 1 tests**: T001 and T002 touch separate test files and can be authored in parallel.
- **User Story 1 implementation**: After T001/T002, T003, T004, and T005 touch separate files and can proceed in parallel. T006 follows T005; T007 follows T006.
- **User Story 2**: T008 is independently testable after User Story 1 is complete and can be worked on separately from final quickstart validation once its dependency is met.

---

## Parallel Example: User Story 1

```text
After T001 and T002 are written, run:
Task: "Implement session revocation and cookie clearing in src/cs_avatar/api/auth.py"
Task: "Update logout contract in specs/003-steam-signout/contracts/openapi.yaml"
Task: "Add the sign-out request helper in src/frontend/features/auth/api.ts"
```

## Parallel Example: User Story 2

```text
After User Story 1 is complete:
Task: "Add the different-identity sign-in integration test in tests/backend/integration/test_auth_logout.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Add focused backend and frontend tests for the sign-out journey and failure behavior.
2. Implement persisted session revocation and the logout API contract.
3. Add the profile action, truthful failure handling, and cross-tab/session restoration behavior.
4. Validate User Story 1 independently using its acceptance scenarios and the quickstart's sign-out cases.

### Incremental Delivery

1. Complete User Story 1 and verify the old session cannot be reused.
2. Complete User Story 2 by verifying a different Steam identity creates a fresh session after sign-out.
3. Run all quickstart scenarios, including manual Steam account selection and cancellation.

## Notes

- `[P]` marks work in different files with no dependency on unfinished tasks.
- `[US1]` and `[US2]` map to the stories in `specs/003-steam-signout/spec.md`.
- The existing session schema is reused; do not add a migration unless implementation investigation proves the documented `revoked_at` support is absent.
- Do not log, return, or broadcast raw session credentials or Steam profile data beyond the existing authenticated session response.
