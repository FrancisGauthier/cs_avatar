# WebSocket Contract

## Endpoint and access

- **Endpoint**: `wss://<same-origin>/api/v1/ws/rosters/{roster_id}`
- **Authentication**: The browser supplies the same-origin secure, HttpOnly
  session cookie established by Steam sign-in. Query-string credentials are
  forbidden.
- **Handshake checks**: Require a valid allowlisted `Origin`, active session,
  open roster, and approved membership before accepting. Reject unauthorized
  handshakes without disclosing whether a private roster exists.
- **Authorization**: Only approved members receive roster events. The server
  rechecks the session and membership when delivering updates and closes the
  connection on logout, session expiry, removal, or roster closure.
- **Transport**: WSS in production. Enforce connection, frame-size, and
  per-identity message-rate limits. Do not log session cookies, invitation
  tokens, or complete private roster payloads.

## Client messages

The socket is for updates, not privileged mutations. Roster mutations use the
HTTP contract.

| Type | Payload | Meaning |
|------|---------|---------|
| `resync` | `{ "type": "resync" }` | Ask for a fresh authorized roster snapshot after reconnect or a detected version gap |

All client frames are size-bounded and schema-validated. Unknown message types
are rejected; repeated invalid frames close the connection.

## Server messages

Every message is JSON with a `type` discriminator.

### `roster.snapshot`

Sent after successful subscription and in response to `resync`.

```json
{
  "type": "roster.snapshot",
  "version": 12,
  "roster": {
    "id": "uuid",
    "themeId": "theme-id",
    "status": "OPEN",
    "members": [
      {
        "memberId": "73e928be-17e8-47c7-9481-6baae9018d30",
        "role": "HOST",
        "status": "APPROVED",
        "displayName": "Example",
        "avatarAssetId": "asset-id",
        "ready": false
      }
    ]
  }
}
```

Steam IDs, invitation tokens, authentication/session data, pending join-request
details, and private data from other rosters are never included.

### `roster.updated`

Sent to currently authorized roster members after a committed visible change.
It contains the new `version` and an authorization-filtered roster snapshot.
Clients ignore duplicate/older versions and request `resync` when a version gap
is detected.

### `error`

```json
{
  "type": "error",
  "code": "SESSION_EXPIRED",
  "message": "Your session has expired. Sign in again."
}
```

Error codes are non-sensitive. The server closes the socket after terminal
authorization failures.

## Delivery semantics

- PostgreSQL is the source of truth. A transaction commits state before
  publishing a `NOTIFY` containing only the roster ID.
- Each ASGI worker listens for notifications, reloads the authorized roster
  snapshot, then broadcasts it only to its local sockets for that roster.
- Notifications are change signals, not durable events. Clients get a database
  snapshot on connect/reconnect and use `resync` after a version gap.
- Delivery is best-effort while connected; the HTTP read endpoint is the
  recovery path.
