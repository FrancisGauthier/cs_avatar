# Feature Specification: Steam Account Login

**Feature Branch**: `002-steam-login`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "As a first increment, add a prominent Log in with Steam button. Let players authenticate on Steam using the requested OpenID sign-in flow, then show their Steam nickname and profile picture in the app."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in with Steam and view player profile (Priority: P1)

A player who is not signed in chooses **Log in with Steam**, reviews what account information the app will use, and continues to Steam to authenticate. After successful authentication, the player returns to the app and sees their Steam nickname and profile picture.

**Why this priority**: Steam sign-in and a recognizable player profile are the complete value of this first increment.

**Independent Test**: Starting from a signed-out state, complete Steam sign-in with a test account and verify that the app shows that account's nickname and profile picture without the player entering Steam credentials into the app.

**Acceptance Scenarios**:

1. **Given** a player is signed out, **When** they view the sign-in experience, **Then** they see a prominent, clearly labeled **Log in with Steam** button and a notice that the app is independent from Steam and will use their Steam account identifier and publicly visible profile information.
2. **Given** a player chooses **Log in with Steam**, **When** they continue to Steam and successfully authenticate, **Then** they return to the app in a signed-in state and see their Steam nickname and profile picture.
3. **Given** a player is on Steam's authentication page, **When** they review the sign-in request, **Then** their Steam password is not requested or entered on the app's pages.
4. **Given** the player's public profile picture cannot be displayed, **When** sign-in succeeds, **Then** the app still shows the player's nickname and a neutral fallback image.
5. **Given** the player cancels sign-in or authentication fails, **When** they return to the app, **Then** they remain signed out, see a clear status message, and can retry.

### Edge Cases

- The player cancels or declines Steam authentication; no signed-in state or profile from that attempt is shown.
- Steam's sign-in service is unavailable, or the return from Steam cannot be verified; the app reports that sign-in did not complete and offers a retry without treating the player as signed in.
- The Steam nickname or public profile picture is unavailable; the app displays available profile information and uses a neutral fallback for a missing picture.
- The player has already signed in during the current app session; the signed-in profile is shown instead of prompting them to start the same sign-in again.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The signed-out experience MUST present a prominent **Log in with Steam** button that identifies Steam as the sign-in provider.
- **FR-002**: Choosing the button MUST take the player to Steam's authentication experience and return them to the app after the attempt.
- **FR-003**: Before the player continues to Steam, the app MUST explain that it is not affiliated with Steam or Valve and that it will use the Steam account identifier and publicly visible profile information to identify and display the player's profile.
- **FR-004**: The app MUST NOT ask players to enter their Steam password on an app-controlled page.
- **FR-005**: The app MUST treat a player as signed in only after a successful, verified Steam authentication.
- **FR-006**: After successful sign-in, the app MUST show the player's Steam nickname and profile picture in the signed-in account area.
- **FR-007**: If the profile picture is unavailable, the app MUST show the nickname and a neutral fallback image.
- **FR-008**: If the player cancels sign-in or authentication fails, the app MUST leave them signed out, explain that sign-in did not complete, and allow them to retry.
- **FR-009**: During the current app session, the signed-in account area MUST continue to identify the authenticated player without requiring them to repeat sign-in on every view.

### Key Entities *(include if feature involves data)*

- **Steam account identity**: The verified Steam account identifier used to recognize the player.
- **Player profile**: The Steam nickname and publicly visible profile picture associated with the signed-in account; the picture may be unavailable.
- **Sign-in attempt**: A player's initiated Steam sign-in and its outcome: completed, cancelled, or failed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 9 out of 10 first-time test participants can identify the Steam sign-in button and start sign-in within 30 seconds.
- **SC-002**: In all successful sign-in test cases, the player sees the correct Steam nickname and either the correct profile picture or the documented fallback.
- **SC-003**: In all cancelled, failed, or unverifiable sign-in test cases, the player remains signed out and receives a clear status message.
- **SC-004**: At least 9 out of 10 test participants correctly understand that Steam credentials are entered on Steam, not in this app.

## Assumptions

- This increment uses the Steam OpenID sign-in flow requested by the user; players authenticate on Steam and are returned to the app.
- The app uses the signed-in session's account area for the nickname and profile picture; a neutral fallback image is used if the picture cannot be shown.
- The first increment covers Steam sign-in and profile display only. Sign-out, linking multiple accounts, other identity providers, and additional Steam profile or game data are out of scope.
- The app may use the Steam account identifier and publicly visible nickname and profile picture only as needed to recognize and display the signed-in player.
