# Quickstart: Steam App Sign-Out

## Prerequisites

- Complete the existing Steam login setup in [the Steam login quickstart](../002-steam-login/quickstart.md).
- Start PostgreSQL and apply the existing migrations; sign-out is expected to reuse the current session `revoked_at` field and require no new migration.
- Start the backend and SPA as described in the existing quickstart.

## Validation

Run focused backend, frontend, lint, and type checks from the repository root:

```powershell
uv run pytest tests/backend/integration/test_auth_routes.py
uv run ruff check src tests
npm run test -- --run
npm run typecheck
```

Run the browser suite when validating navigation and tab behavior:

```powershell
npm run e2e
```

## Scenarios and expected outcomes

1. Sign in with a Steam account and verify the signed-in profile offers **Sign out**.
2. Select **Sign out** and verify the signed-out screen appears. The logout response revokes the app session and clears the session cookie.
3. Request the current session with the old cookie, reload the app, and use browser back navigation; each check remains unauthenticated and the prior profile is not displayed.
4. Open the same app in a second tab before signing out in the first. Verify the second tab stops presenting the old profile and revalidates to signed out.
5. Repeat sign-out with a missing, expired, or revoked session; verify the user remains signed out without a false failure.
6. Simulate an unavailable logout endpoint; verify the app does not claim successful sign-out and gives the user a retryable message.
7. Start Steam sign-in after sign-out and use Steam's account-switch control to authenticate a different test account. Verify only the newly authenticated account's profile is shown.
8. Cancel the new Steam sign-in and verify the user remains signed out.

For session transitions and data invariants, see [data-model.md](./data-model.md). For the logout request and response contract, see [contracts/openapi.yaml](./contracts/openapi.yaml).
