# Data Model: Lobby Theme Sync

The database is authoritative for roster and membership state. Steam IDs are
stored and exchanged as decimal strings to preserve all 64 bits across Python,
JSON, and TypeScript.

## Entities

### Steam Identity

Represents an authenticated Steam account; it is not a separate cs_avatar
username/password account.

| Field | Type | Rules |
|-------|------|-------|
| `steam_id` | string | Steam's decimal 64-bit identifier; validated server-side and never parsed as a JavaScript number |

Only the identifier needed for ownership and membership is retained. Steam
profile details are not requested or copied.

### Steam OpenID Attempt

Represents a short-lived sign-in attempt and prevents callback replay or
cross-browser completion.

| Field | Type | Rules |
|-------|------|-------|
| `state_digest` | bytes/string | Digest of a high-entropy one-time state value |
| `browser_binding_digest` | bytes/string | Binds the callback to the browser that initiated sign-in |
| `return_to` | URL | Exact configured callback URL; never derived from an untrusted request |
| `created_at` | timestamp | Set by the service |
| `expires_at` | timestamp | Short-lived; expired attempts are rejected |
| `consumed_at` | nullable timestamp | Set atomically on successful use; prevents replay |

The backend validates the OpenID 2.0 provider endpoint, return URL, nonce, signed
fields, and assertion with the configured Steam provider before issuing a
session. Client-supplied Steam IDs are never accepted as authentication.

### Auth Session

Represents a browser session created only after the backend validates a Steam
OpenID 2.0 assertion.

| Field | Type | Rules |
|-------|------|-------|
| `id_digest` | bytes/string | Digest of a high-entropy opaque session cookie; unique |
| `steam_id` | string | Authenticated Steam identity |
| `created_at` | timestamp | Set by the service |
| `expires_at` | timestamp | 12 hours after sign-in; enforced on every HTTP request and WebSocket connection |
| `revoked_at` | nullable timestamp | Set on logout or administrative invalidation |

The browser cookie is `Secure`, `HttpOnly`, and `SameSite=Lax`; raw session
values are not logged or stored. Expired or revoked sessions cannot mutate
rosters or retain open WebSocket access.

### Roster

Represents one temporary private group plan.

| Field | Type | Rules |
|-------|------|-------|
| `id` | UUID | Opaque, non-sequential identifier |
| `host_steam_id` | string | Authenticated creator |
| `theme_id` | string | Must exist in the curated theme catalog |
| `status` | enum | `OPEN`, `CLOSED`, or `EXPIRED` |
| `created_at` | timestamp | Set by the service |
| `updated_at` | timestamp | Updated on successful join, membership, assignment, readiness, invitation, or host action |
| `expires_at` | timestamp | `updated_at` plus 24 hours |
| `version` | integer | Incremented on each committed visible roster change |

An open roster has one to ten approved members, including its host. The host
must be an approved member. Closing a roster deletes its roster data; inactivity
cleanup removes rosters after 24 hours without a successful roster action.
Read-only views and WebSocket heartbeats do not extend the expiry.

### Membership / Join Request

Represents a Steam identity's request or membership in a roster.

| Field | Type | Rules |
|-------|------|-------|
| `member_id` | UUID | Opaque, roster-scoped identifier used by client contracts |
| `roster_id` | UUID | Foreign key to roster |
| `steam_id` | string | Foreign key/identity; one row per identity and roster |
| `role` | enum | `HOST` or `PARTICIPANT` |
| `status` | enum | `PENDING`, `APPROVED`, `REJECTED`, or `REMOVED` |
| `requested_at` | timestamp | Set when the invite is accepted as a join request |
| `decided_at` | nullable timestamp | Set by host decision |

The unique keys are `member_id` and `(roster_id, steam_id)`. A pending
membership's `member_id` is also its join-request ID. Client roster snapshots
use `member_id`; Steam IDs are not broadcast to roster participants. Only the
host can approve, reject, remove another member, revoke the invitation, or close
the roster. A participant can change only their own assignment and readiness.
Approval checks membership count while locking the roster row, so concurrent
approvals cannot exceed ten.

### Assignment

Represents the identity a member intends to use.

| Field | Type | Rules |
|-------|------|-------|
| `roster_id`, `member_id` | composite key | References an approved membership |
| `display_name` | string | Trimmed, Unicode-normalized, 1-32 grapheme clusters, no control characters |
| `normalized_name` | string | Server-computed Unicode case-folded value; unique per roster |
| `avatar_asset_id` | string | Must belong to the roster's selected curated theme |
| `ready` | boolean | Defaults false; any assignment edit resets it to false |
| `updated_at` | timestamp | Set by the service |

The unique constraint on `(roster_id, normalized_name)` is the final authority
for simultaneous name claims. The server validates and normalizes before saving;
client validation is for feedback only.

### Theme Catalog

Read-only, version-controlled content shipped with the application.

| Field | Type | Rules |
|-------|------|-------|
| `theme_id` | string | Stable identifier |
| `label` | string | User-facing theme name |
| `name_options` | list | At least ten distinct suggested names |
| `avatar_assets` | list | At least ten curated, theme-matched asset IDs |

Assets must be original or properly authorized, and the product must not imply
official Counter-Strike 2 affiliation. User uploads and external image URLs are
out of scope. Roster assignments store asset IDs, not user-supplied image data.

### Invitation

Represents the host's revocable access link.

| Field | Type | Rules |
|-------|------|-------|
| `roster_id` | UUID | Foreign key to roster |
| `token_digest` | bytes/string | Digest of a high-entropy random token; never store the raw token |
| `created_at` | timestamp | Set by service |
| `revoked_at` | nullable timestamp | Set by host |

The raw token is returned once in an invitation URL fragment, not a query
parameter or path. The SPA submits it in an authenticated request body; logs
must redact request bodies containing invitation tokens.

## State Transitions

- **Roster**: `OPEN -> CLOSED` by host; `OPEN -> EXPIRED` after 24 hours of
  inactivity. Either terminal state removes roster data.
- **Membership**: `PENDING -> APPROVED | REJECTED` by host;
  `APPROVED -> REMOVED` by host or voluntary leave.
- **Assignment readiness**: `NOT_READY -> READY` by the participant;
  any name/avatar change resets the state to `NOT_READY`.
- **Invitation**: `ACTIVE -> REVOKED` by host; expiry follows roster expiry.
- **Auth session**: `ACTIVE -> REVOKED` on logout or `EXPIRED` at `expires_at`.

## Relationships

- One Steam identity may participate in many rosters.
- A roster has one host and up to nine other approved participants.
- A roster has one selected theme and one active invitation at a time.
- Each approved membership has one assignment.
- Each assignment references one avatar in the selected theme.
- Join requests are memberships in `PENDING` state.
