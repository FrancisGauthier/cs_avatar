# Research: Steam App Sign-Out

## Repository Findings

### Existing server-side revocation

- **Decision**: Revoke the current session by recording `revoked_at` on the existing `AuthSession` row.
- **Rationale**: The column already exists in the model and initial migration, and `/api/v1/auth/session` already excludes revoked rows. Updating the row makes copied or stale session cookies unusable immediately without changing the database schema.
- **Alternatives considered**: Cookie deletion alone was rejected because it only removes the current browser's copy; the persisted session token would remain valid if copied or replayed.

### Logout request semantics

- **Decision**: Add an authenticated-session sign-out operation that returns a no-content success when the cookie is valid, expired, missing, or already revoked, and clears the app session cookie.
- **Rationale**: Repeated sign-out and expired sessions should be safe and idempotent. The API can act only on the existing HttpOnly cookie; it must not accept a client-supplied Steam ID.
- **Alternatives considered**: Redirecting to Steam's logout was rejected because product behavior is explicitly scoped to the app and must preserve Steam's own session.

### Browser tab and navigation behavior

- **Decision**: On confirmed sign-out, reset the active tab and broadcast a non-sensitive sign-out notification to other app tabs. Revalidate session state when a tab is restored or returns to the foreground.
- **Rationale**: The session cookie is shared by same-origin tabs, but React state is not. A local broadcast clears stale profile UI promptly; a session recheck handles browser restoration and cases where an event was missed.
- **Alternatives considered**: Relying on each tab's next API request was rejected because a tab could keep showing a previously loaded profile indefinitely. Broadcasting the token or profile was rejected because it would needlessly expose session-related data to other tabs.

### Failure handling

- **Decision**: Keep the user in an authenticated/error state if sign-out cannot be confirmed, show a clear retryable message, and do not broadcast success.
- **Rationale**: The specification requires truthful status; network failure cannot establish that server-side revocation completed. Retry remains safe because the operation is idempotent.
- **Alternatives considered**: Optimistically clearing the profile and reporting success was rejected because the old session might still be valid.

## Technology and Integration Choices

- **Decision**: Use only existing FastAPI/SQLAlchemy session services and React/Vitest/Playwright test infrastructure.
- **Rationale**: The project already implements session issuance, cookie handling, same-origin API requests, persisted revocation state, and test fixtures.
- **Alternatives considered**: New logout storage, a session schema migration, and new cross-tab libraries were rejected as unnecessary.

## Open Questions

None. The feature specification and repository contain enough information to proceed to task generation.
