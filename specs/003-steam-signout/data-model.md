# Data Model: Steam App Sign-Out

## Existing Entity: AuthSession

Represents one app session created after a Steam identity has been verified.

| Field | Existing meaning | Sign-out behavior |
|---|---|---|
| `id_digest` | Digest of the opaque session cookie token; primary key | Used to locate the active row without storing or querying on the raw token |
| `steam_id` | Verified Steam identity associated with the session | Unchanged |
| `persona_name` | Nickname captured for display | Unchanged; no longer returned after revocation |
| `avatar_url` | Validated profile image URL captured for display | Unchanged; no longer returned after revocation |
| `profile_status` | Availability of captured profile details | Unchanged |
| `created_at` | Session creation time | Unchanged |
| `expires_at` | Session expiration time | Unchanged |
| `revoked_at` | Time the app session was revoked, or null while active | Set once when sign-out revokes the matching session |

No new entity, field, or migration is expected.

## State and Transitions

```text
Active (revoked_at is null, expires_at is in the future)
  ├─ confirmed sign-out -> Revoked (revoked_at is set)
  └─ time passes        -> Expired (expires_at is not in the future)

Revoked or Expired
  └─ repeated sign-out -> remains unavailable; response is idempotent
```

An absent session cookie has no associated record transition and is treated as already signed out. A new Steam authentication creates a new independent session associated with the identity Steam verifies; it does not reactivate the old session.

## Validation and Security Invariants

- Never accept a Steam ID or raw session token from the request body for sign-out.
- Derive the target session only from the existing HttpOnly cookie using the application's session-token digest function.
- Revoked and expired records MUST remain unusable for the current-session lookup.
- Do not log, return, or broadcast the raw cookie, its digest, or profile data.
- Clear the browser cookie using the same name, path, secure, HttpOnly, and SameSite attributes as session issuance.
- The Steam provider's browser authentication session is separate and is not changed.
