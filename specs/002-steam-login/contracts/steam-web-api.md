# Steam Web API Integration Contract

This is a server-to-server dependency. The SPA never calls Steam Web API and
never receives its API key.

## Request

- **Operation**: `ISteamUser/GetPlayerSummaries/v2/`
- **Endpoint**: `https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/`
- **Method**: HTTPS `GET`
- **Input**: The Steam Web API key from server-side secret configuration and
  exactly the Steam ID returned by the verified OpenID assertion.
- **Frequency**: Once after a successful OpenID verification; persist only the
  minimal profile snapshot for the 12-hour authenticated-session lifetime.

The Steam ID is not accepted from browser input. The API key and any
credential-bearing request parameters must be redacted from application and
HTTP-client logs.

## Response handling

- Require a valid JSON response with a player summary for the requested ID.
- Require the returned `steamid` to equal the verified identity.
- Read the `personaname` and `avatarfull` fields for display.
- Accept a profile image URL only when it uses HTTPS and its hostname matches
  the configured Steam profile-image host allowlist (including the Steam CDN
  host documented by Valve).
- Missing, mismatched, malformed, or unavailable profile data produces an
  authenticated session with `profileStatus: UNAVAILABLE`; it does not
  authenticate a user or change the verified Steam ID.
- Apply a bounded request timeout. Do not retry unboundedly or expose upstream
  error details or credentials to the browser.
