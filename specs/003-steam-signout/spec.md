# Feature Specification: Steam App Sign-Out

**Feature Branch**: `not created`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "As a logged in user using steam openid i want to sign off the app. So that i can log back in using another account"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign out of the app (Priority: P1)

A signed-in player chooses to sign out. The app ends that player's app session, removes their profile from the signed-in experience, and returns them to the sign-in screen.

**Why this priority**: Ending the current app session is necessary before another Steam identity can be used on the same browser.

**Independent Test**: Sign in with a Steam account, choose sign out, and verify that the signed-out screen appears and the previous account is no longer available in the app.

**Acceptance Scenarios**:

1. **Given** a player is signed in, **When** they choose **Sign out**, **Then** the app ends the current app session and displays the signed-out experience.
2. **Given** a player has signed out, **When** they reload the app or use browser navigation to return to the signed-in view, **Then** the app does not show the previous profile or treat the player as signed in.
3. **Given** a player is already signed out or their session has expired, **When** they choose or repeat the sign-out action, **Then** the app remains signed out and reports no false sign-out failure.

### User Story 2 - Sign in with a different Steam account (Priority: P1)

After signing out, a player starts Steam sign-in again and uses Steam's account-switch option when the browser is already signed into a different Steam account. After successful authentication, the app shows only the newly selected account's profile.

**Why this priority**: Switching accounts in the same browser is the outcome the player needs from sign-out.

**Independent Test**: Sign in with one Steam account, sign out, select a second account on Steam's authentication screen, and verify that the app shows the second account's nickname and profile picture.

**Acceptance Scenarios**:

1. **Given** the player has signed out of the app, **When** they start Steam sign-in, **Then** they reach Steam's authentication experience and can choose or switch to another Steam account without entering Steam credentials in the app.
2. **Given** the player selects a different Steam account and successfully authenticates, **When** they return to the app, **Then** the app shows the selected account's nickname and profile picture and does not show the previous account's profile.
3. **Given** the player cancels or fails the new Steam sign-in, **When** they return to the app, **Then** they remain signed out.

---

### Edge Cases

- The app session has expired before the player chooses sign out; the app remains signed out and permits a new sign-in.
- The player signs out in one browser tab while another tab is displaying the app; the other tab must not continue to present the old profile as authenticated.
- The player uses browser back or reload after sign-out; the previous signed-in profile must not be restored as an authenticated view.
- The app cannot complete session termination; it must not claim sign-out succeeded while the old session remains usable, and it must provide a clear recovery message.
- Steam remains signed in to the previous account in the browser; the player must use Steam's account-switch option to select another account. Signing out of the app does not sign the player out of Steam itself.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The signed-in account area MUST provide a clearly labeled **Sign out** action.
- **FR-002**: Choosing **Sign out** MUST end the current app session and remove the browser's ability to resume that session.
- **FR-003**: After a successful sign-out, the app MUST show its signed-out experience and MUST NOT display the previous account as signed in.
- **FR-004**: A signed-out session MUST remain unauthenticated after reload, browser back navigation, or use of an already open app tab.
- **FR-005**: Repeating sign-out when already signed out or when a session has expired MUST leave the player signed out without presenting an error as a successful sign-out.
- **FR-006**: After sign-out, the player MUST be able to start a new Steam sign-in and select or switch to a different Steam account through Steam's authentication experience.
- **FR-007**: After successful authentication with another Steam account, the app MUST display that account's nickname and profile picture and MUST NOT display the previous account's profile.
- **FR-008**: If the player cancels or cannot complete the new Steam sign-in, the app MUST leave them signed out and provide a clear status message.
- **FR-009**: The app MUST NOT request or handle Steam account passwords, and signing out of the app MUST NOT imply that the player was signed out of Steam or other Steam services.
- **FR-010**: If the app cannot end the current session, it MUST clearly report that sign-out did not complete and MUST NOT claim the player is signed out while the session remains valid.

### Key Entities *(include if feature involves data)*

- **App session**: The authenticated session that allows the browser to access the signed-in app experience; it has an active or ended state.
- **Steam account identity**: The verified identity selected during Steam sign-in, distinct from the browser's current Steam login state.
- **Player profile**: The nickname and publicly visible profile picture associated with the selected Steam account.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In all sign-out acceptance tests, the signed-out experience is shown within 5 seconds of the player selecting **Sign out**.
- **SC-002**: In 100% of reload, back-navigation, and multi-tab tests after sign-out, the previous account is not shown as authenticated.
- **SC-003**: In 100% of successful account-switch tests, the app displays the newly selected Steam account's nickname and profile picture, not the previous account's.
- **SC-004**: At least 9 out of 10 test participants can sign out and start a different-account sign-in within 2 minutes without entering Steam credentials in the app.

## Assumptions

- Signing out ends only the app's session. It does not globally sign the player out of Steam or other Steam services.
- If Steam is already authenticated to an account in the browser, the player can use Steam's own account-switch option (such as **Not You?**) during the next sign-in.
- The existing Steam sign-in flow and profile display remain unchanged apart from supporting sign-out and a subsequent different-account sign-in.
- If the app cannot confirm that a session ended, it must prioritize truthful status and safe recovery over showing a success message.
