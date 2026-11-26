# Data Model: Steam Account Login

The authenticated session remains authoritative. The feature adds a
session-scoped profile snapshot; it does not create a durable Steam profile
store.

## Entities

### Steam Identity

Represents the Steam account authenticated through Steam OpenID 2.0.

| Field | Type | Rules |
|-------|------|-------|
| `steam_id` | string | Verified decimal Steam identifier; never parse as a JavaScript number or accept from the client as proof of identity |

### Auth Session

Represents a browser session created only after the backend validates the
Steam OpenID assertion. The session record holds the minimal display profile
snapshot and expires 12 hours after sign-in.

| Field | Type | Rules |
|-------|------|-------|
| `id_digest` | bytes/string | Digest of a high-entropy opaque session cookie |
| `steam_id` | string | Verified Steam identity |
| `persona_name` | nullable string | Steam nickname returned for this exact identity; treated as display text, never HTML |
| `avatar_url` | nullable URL | HTTPS URL from an allowlisted Steam profile-image host; null when missing or invalid |
| `profile_status` | enum | `AVAILABLE` for a valid matching summary with a nickname, otherwise `UNAVAILABLE`; does not affect whether the Steam identity is authenticated |
| `created_at` | timestamp | Set by the service |
| `expires_at` | timestamp | Set to 12 hours after sign-in; profile snapshot is deleted or becomes inaccessible with the session |
| `revoked_at` | nullable timestamp | Set on session revocation |

The browser cookie is `Secure`, `HttpOnly`, and `SameSite=Lax`; raw session
values are not logged or stored. No profile URL, game data, raw Steam API
response, API key, or Steam password is stored. The profile is exposed through
the authenticated session response.

### Steam OpenID Attempt

Represents a short-lived sign-in attempt and binds the provider callback to the
browser that initiated it.

| Field | Type | Rules |
|-------|------|-------|
| `state_digest` | bytes/string | Digest of a high-entropy one-time state value |
| `browser_binding_digest` | bytes/string | Binds the callback to the initiating browser |
| `return_to` | URL | Exact configured callback URL; never derived from an untrusted request |
| `provider_nonce_digest` | nullable bytes/string | Digest of the verified provider nonce; unique within its validity window to reject replay |
| `created_at` | timestamp | Set by the service |
| `expires_at` | timestamp | Short-lived; expired attempts are rejected |
| `consumed_at` | nullable timestamp | Set atomically on successful use; prevents replay |

### Steam Profile API Result

An untrusted, transient response from the Steam Web API. It is not stored as a
separate entity.

| Field | Type | Validation |
|-------|------|------------|
| `steamid` | string | Must exactly match the Steam ID from the verified OpenID assertion |
| `personaname` | string | Validate type and bounded length; render as escaped text |
| `avatarfull` | nullable URL | Validate HTTPS scheme and Steam image-host allowlist before returning to the SPA |

The backend maps missing or invalid display fields to `profile_status =
UNAVAILABLE`; it never treats profile data as identity proof.

## State Transitions

- **Sign-in attempt**: `STARTED -> PROVIDER_REDIRECT -> ASSERTION_VERIFIED ->
  PROFILE_AVAILABLE | PROFILE_UNAVAILABLE -> SESSION_ACTIVE`.
- **Failed sign-in**: Any invalid, mismatched, cancelled, or unverifiable
  OpenID attempt ends without creating an authenticated session.
- **Session**: `ACTIVE -> EXPIRED` at its 12-hour deadline; sign-out is out of
  scope for this increment.

## Relationships

- One authenticated session belongs to exactly one verified Steam identity.
- Each session holds at most one profile snapshot for that identity.
- The snapshot is scoped to the session lifetime and is not shared with other
  players.
