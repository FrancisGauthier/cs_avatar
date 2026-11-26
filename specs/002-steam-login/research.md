# Research: Steam Account Login

## Decisions

### Steam sign-in protocol

- **Decision**: Use Steam's browser-based OpenID Authentication 2.0 flow. The
  backend is the relying party and owns the fixed login, callback, and session
  boundaries defined in this feature plan.
- **Rationale**: The Steam Community developer documentation describes Steam
  as an OpenID provider and documents its claimed identifier as
  `https://steamcommunity.com/openid/id/<steamid>`. The OpenID Authentication
  2.0 namespace is also explicit in the Steam login URL supplied with the
  feature request. OpenID Connect is a different protocol; certification for
  OIDC alone does not establish compatibility with Steam's sign-in protocol.
- **Alternatives considered**: OpenID Connect libraries and the linked OIDC
  certification list do not match Steam's documented web sign-in protocol.

### OpenID assertion verification

- **Decision**: The backend is the relying party. It validates the
  provider, assertion signature, return URL, nonce, and claimed Steam identity
  before using the Steam ID for any profile lookup. Use a relying-party library
  only after a security and maintenance review; do not implement assertion
  checks by hand or accept a client-supplied Steam ID.
- **Rationale**: Steam identity is the authority for the account ID. OpenID
  assertions include provider-controlled data that must be validated before
  creating a session or making an API request.
- **Alternatives considered**: Trusting an ID returned by the browser or
  bypassing the server callback would not prove account control.

### Steam profile lookup

- **Decision**: After OpenID verification, call the Steam Web API player
  summaries operation (`ISteamUser/GetPlayerSummaries/v2/`) for exactly that
  verified Steam ID. Use the returned `personaname` and `avatarfull` fields to
  populate the new authenticated session's minimal profile snapshot.
- **Rationale**: OpenID authenticates the Steam identity; the Web API provides
  the display profile data required by this feature. Keeping the API call on
  the backend prevents disclosure of the Web API key and avoids accepting a
  different Steam ID from the client.
- **Alternatives considered**: Fetching profile data from the browser would
  expose the API key. Persisting a separate, long-lived profile record would
  retain more data than needed; the snapshot instead expires with the
  authenticated session.

### Profile-data and API-key handling

- **Decision**: Keep the Steam Web API key in server-side secret configuration.
  Valve requires a key for Steam Web API calls. Validate the response shape
  and returned Steam ID, treat missing or unavailable profile fields as
  unavailable rather than authentication proof, and accept a profile image
  only from HTTPS Steam CDN hosts. Store only the nickname and image URL on
  the short-lived session; do not log API keys or credential-bearing outbound
  URLs.
- **Rationale**: The key is a privileged server credential, while profile
  fields are display data rather than evidence of identity. Session-scoped
  retention supports the signed-in UI without creating a permanent profile
  database.
- **Alternatives considered**: Calling Steam directly from the SPA, storing the
  full API response, and retaining profile data beyond the auth session.

### OpenID package selection

- **Decision**: Use `python3-openid`, pinned to upstream commit
  `7e8614c20fe6fea5312866365102d94aa4bf1e92`, for relying-party assertion
  validation. The exact commit is pinned in `pyproject.toml`; do not replace it
  with the older PyPI release or a moving branch without repeating this review.
- **Rationale**: The project implements the required OpenID 2.0 consumer flow,
  is licensed Apache-2.0, and its repository received active maintenance in
  November 2026. The pinned revision includes upstream changes restoring the
  operating-system CSPRNG for Diffie-Hellman/nonces and constant-time signature
  comparison. PyPI's latest release, 3.2.0, was uploaded in 2020 and does not
  include those changes. Because the fixed revision is not a signed release,
  pinning the immutable commit and running its upstream and application tests
  are required; dependency upgrades require a fresh security review.
- **Alternatives considered**: The `python-openid` PyPI release is older and
  targets the legacy Python 2 implementation; OIDC libraries do not verify
  Steam's OpenID 2.0 protocol; implementing assertion verification by hand
  would be unsafe.

### Profile lookup failure behavior

- **Decision**: A profile lookup failure does not invalidate a successfully
  verified Steam identity. Return the authenticated session with profile
  fields marked unavailable; show a neutral account label and fallback image
  with a clear status message.
- **Rationale**: The Steam Web API and OpenID sign-in are separate services.
  Temporary profile-data unavailability should not silently turn a valid
  authentication into an unauthenticated state.
- **Alternatives considered**: Rejecting sign-in whenever the profile service
  is unavailable would unnecessarily couple authentication to a secondary
  display-data dependency.

## Focused implementation security review

- The callback accepts only bounded, non-duplicate query parameters, binds the
  state to an HttpOnly browser cookie, verifies a fixed Steam provider endpoint
  and Steam identity URL, and creates a session only after successful OpenID
  verification.
- Login attempts expire and are atomically consumed. A unique persisted digest
  of the OpenID response nonce prevents reuse across separate attempts; the
  session cookie is opaque, HttpOnly, Secure, SameSite=Lax, and only its
  keyed digest is persisted.
- Steam profile requests remain server-side, disable redirects, use a timeout,
  bound streamed response size, and verify that the returned Steam ID matches.
  Avatar URLs are limited to HTTPS Steam CDN hosts, including malformed-port
rejection. Profile/API failures do not expose credentials; only the verified
OpenID assertion establishes identity.
- Uvicorn access logging is disabled in the documented local command because
  OpenID callback query strings contain assertion data. Production proxies
  must also omit or redact query strings.
- Automated validation passed for assertion handling, callback/session routes,
  profile parsing and URL validation, frontend states, and a mocked browser
  flow. A live PostgreSQL migration and real Steam sign-in remain unverified
  because the Docker daemon was unavailable and no live Steam credentials or
  public callback origin were configured.

## Research Sources

- Valve, Steam Community Developer documentation: <https://steamcommunity.com/dev/>
- Valve, Steam Web API key registration and terms, linked from the Steam
  Community developer documentation: <https://steamcommunity.com/dev/apikey>
- Valve, `ISteamUser/GetPlayerSummaries` method documentation:
  <https://partner.steamgames.com/doc/webapi/ISteamUser#GetPlayerSummaries>
- OpenID Authentication 2.0 specification:
  <https://openid.net/specs/openid-authentication-2_0.html>
- OpenID Foundation, Certified OpenID Connect Implementations (the user-provided
  link; relevant to OIDC, not Steam OpenID 2.0):
  <https://openid.net/certification/certified-openid-connect-implementations/>
- PyPI, `python3-openid` release metadata:
  <https://pypi.org/project/python3-openid/>
- `python3-openid` source repository:
  <https://github.com/necaris/python3-openid>
- `python3-openid` reviewed immutable upstream revision:
  <https://github.com/necaris/python3-openid/commit/7e8614c20fe6fea5312866365102d94aa4bf1e92>
- `python3-openid` security-related upstream changes and rationale:
  <https://github.com/necaris/python3-openid/commit/e367a2a5688d69cf67e01850ba37109c433ada73>
