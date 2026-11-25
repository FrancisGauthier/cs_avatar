# Research: Lobby Theme Sync

## Decisions

### Steam web authentication

- **Decision**: Use Steam as the identity provider through Steam's OpenID
  Authentication 2.0 web flow. The backend is the relying party and validates
  the assertion before establishing a cs_avatar session. Store Steam IDs as
  decimal strings, never JavaScript numbers.
- **Rationale**: Valve documents Steam as an OpenID provider and states that its
  claimed identifier contains the user's 64-bit SteamID. The OpenID 2.0
  specification requires the relying party to verify the return URL, discovered
  provider data, nonce, and assertion signature. Steam sign-in does not require
  users to give their Steam password to this application.
- **Alternatives considered**: OAuth 2.0/OpenID Connect are not the web sign-in
  protocol documented by Steam. Steam session tickets are intended for game
  clients and backend game authentication, not this browser-only web sign-in.
- **Dependency gate**: Do not assume an OAuth/OIDC-only library supports Steam's
  OpenID 2.0 protocol, and do not implement assertion verification by hand.
  `python3-openid` is a possible consumer library, but PyPI lists its 3.2.0
  release as uploaded in June 2020. Before implementation locks dependencies,
  maintainers MUST review maintenance, security history, license, and protocol
  compatibility for a suitable OpenID 2.0 relying-party implementation. Keep
  protocol handling behind a small adapter and block release if no candidate
  passes review.

### Python service and SPA

- **Decision**: Use FastAPI/Starlette as the Python ASGI service and React +
  TypeScript + Vite for the SPA.
- **Rationale**: FastAPI documents support for WebSocket endpoints and
  dependency-based cookie/header/path validation. React's component model suits
  the interactive roster and live status updates. Vite builds TypeScript SPA
  assets without introducing a second application server or server-side
  rendering layer.
- **Alternatives considered**: A server-rendered web framework or a separate
  Node.js backend would add backend surface and duplicate the user-selected
  Python/TypeScript stack without improving the specified user flows.

### WebSocket security and message flow

- **Decision**: Use authenticated WSS connections for roster updates. Use
  same-origin, secure HttpOnly session cookies; allowlist the expected `Origin`
  on every handshake; verify roster membership before subscribing and before
  delivering private updates. Use HTTP endpoints for mutations; WebSockets
  publish committed snapshots/change notices only.
- **Rationale**: OWASP recommends WSS, explicit origin allowlists, session and
  authorization checks, message validation, size/rate limits, and avoiding
  credentials in query strings. Keeping mutations on HTTP reduces the number of
  privileged socket commands. FastAPI's in-memory connection-manager example is
  process-local, so it is insufficient alone when multiple workers are used.
- **Alternatives considered**: Query-string bearer tokens can leak into logs and
  referrers. A process-local broadcast list does not reach sockets connected to
  other workers. Redis would work but adds a service; PostgreSQL notifications
  are sufficient for this feature's bounded room size.

### Shared storage and fan-out

- **Decision**: Use PostgreSQL as the authoritative store and `LISTEN`/`NOTIFY`
  for cross-worker change signals. Notifications carry only a roster ID and are
  sent in the mutation transaction. Workers re-read the committed,
  authorization-filtered roster snapshot before broadcasting. On connect or
  reconnect, clients fetch a fresh snapshot.
- **Rationale**: PostgreSQL constraints and transactions can enforce
  assignment uniqueness and simultaneous membership limits. Its documented
  notifications are delivered after transaction commit and can signal multiple
  listening sessions. Notifications are not the source of truth; the database
  snapshot handles missed events and reconnects.
- **Alternatives considered**: In-memory state loses changes on process restart
  and does not coordinate workers. Redis pub/sub is an additional service and
  is not required for the specified ten-member roster.

### Testing and validation

- **Decision**: Use pytest for backend tests, Vitest for frontend unit and
  component tests, and Playwright for browser-based end-to-end flows. Use
  PostgreSQL in integration tests for constraints, transactions, and
  notifications.
- **Rationale**: These tools have first-party documentation for automated test
  discovery, Vite-integrated TypeScript tests, and isolated end-to-end browser
  scenarios. A real PostgreSQL integration target is needed to validate
  transaction and notification behavior that in-memory substitutes cannot
  prove.
- **Alternatives considered**: Mock-only persistence tests cannot validate
  database uniqueness races or `LISTEN`/`NOTIFY`; manual browser testing cannot
  reliably verify independent participants or update timing.

## Research Sources

- Valve, Steam Community Developer documentation (Steam OpenID provider and
  claimed SteamID): <https://steamcommunity.com/dev>
- Valve, Steamworks Authentication (browser OpenID and Steam identity methods):
  <https://partner.steamgames.com/doc/features/auth>
- OpenID Authentication 2.0 specification (relying-party assertion checks):
  <https://openid.net/specs/openid-authentication-2_0.html>
- Python `python3-openid` package metadata and release history:
  <https://pypi.org/project/python3-openid/>
- FastAPI WebSockets documentation (dependencies, disconnects, in-memory
  broadcast limitation): <https://fastapi.tiangolo.com/advanced/websockets/>
- OWASP WebSocket Security Cheat Sheet (WSS, Origin, authentication,
  authorization, validation, limits, logging):
  <https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html>
- PostgreSQL `NOTIFY` documentation (transaction delivery, payload use):
  <https://www.postgresql.org/docs/current/sql-notify.html>
- PostgreSQL `LISTEN` documentation (worker subscriptions and startup race):
  <https://www.postgresql.org/docs/current/sql-listen.html>
- React Quick Start: <https://react.dev/learn>
- Vite Guide (TypeScript templates and static production builds):
  <https://vite.dev/guide/>
- TypeScript documentation: <https://www.typescriptlang.org/docs/>
- SQLAlchemy asyncio documentation: <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>
- pytest documentation: <https://docs.pytest.org/en/stable/>
- Vitest Guide: <https://vitest.dev/guide/>
- Playwright Test documentation: <https://playwright.dev/docs/intro>
