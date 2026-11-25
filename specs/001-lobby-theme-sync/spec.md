# Feature Specification: Lobby Theme Sync

**Feature Branch**: `001-lobby-theme-sync`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Develop cs_avatar, a web application of counter strike 2 players who joined a lobby in the game and want to all sync thier player names and avatar according to a theme."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plan a themed roster (Priority: P1)

A player creates a themed roster for their Counter-Strike 2 group. They choose a
curated theme and see distinct, matching name suggestions and avatar choices for
the group, including an assignment for themselves. They can adjust the roster
before inviting anyone.

**Why this priority**: A themed roster is the core value of the application and
remains useful to a player planning a group's identity before others join.

**Independent Test**: Create a roster for one player, choose a theme, and verify
that a matching name and avatar can be selected and displayed together.

**Acceptance Scenarios**:

1. **Given** a player has opened the application, **When** they create a roster
   and choose a curated theme, **Then** they see matching name and avatar options
   for the host and up to nine additional player slots.
2. **Given** a roster has been created, **When** the host changes a name or
   avatar assignment, **Then** the roster preview reflects the new assignment
   and shows no duplicate names.

---

### User Story 2 - Join and choose an identity (Priority: P2)

A player in the game lobby opens the host's invitation, joins the themed roster,
and chooses a distinct name and avatar from the selected theme. The host can
review and manage who joins.

**Why this priority**: Shared participation turns a theme idea into a coordinated
group identity while giving the host control over the private roster.

**Independent Test**: Join a second player to an active roster using its
invitation, select a name and avatar, and verify the host and participant see
the same assignment.

**Acceptance Scenarios**:

1. **Given** a roster is open and has room, **When** a player follows its active
   invitation and the host approves entry, **Then** the player appears in the
   roster and can choose an available name and avatar.
2. **Given** a name is already assigned, **When** another participant tries to
   select that name, **Then** the application rejects the duplicate and keeps
   the participant's previous selection.
3. **Given** a roster has reached ten players or its invitation is revoked,
   **When** another player tries to join, **Then** entry is refused with a clear
   explanation.
4. **Given** an invitation is active, **When** the host rejects a join request
   or removes a participant, **Then** that player cannot view or change the
   private roster.
5. **Given** a player enters an empty, overlong, or control-character-containing
   name, **When** they try to save it, **Then** the application rejects the
   input and explains how to correct it without changing the existing
   assignment.

---

### User Story 3 - Confirm and apply the roster (Priority: P3)

Players review the final roster, mark their own assignment ready, and use the
provided details to update their Counter-Strike 2 or Steam profile themselves.
The host can tell who is ready before the group starts playing.

**Why this priority**: A shared ready state helps the group finish coordinating,
while clear manual instructions make the assignments usable without requesting
access to players' accounts.

**Independent Test**: Have multiple participants select assignments, mark
themselves ready, and verify the final roster and ready states are visible to
everyone.

**Acceptance Scenarios**:

1. **Given** a participant has selected a name and avatar, **When** they mark
   their assignment ready, **Then** the roster shows that participant as ready.
2. **Given** a ready participant's assignment changes, **When** the change is
   saved, **Then** that participant's ready state resets until they confirm the
   new assignment.
3. **Given** the roster is complete, **When** a participant views their
   assignment, **Then** they can copy the name and view the selected avatar and
   concise instructions for applying them manually.
4. **Given** a roster is closed or has been inactive for 24 hours, **When** a
   participant tries to access it, **Then** access is refused and its roster
   data is no longer available.

### Edge Cases

- A player follows an expired, revoked, or closed invitation.
- Two participants try to claim the same name at nearly the same time.
- The host removes a participant or closes the roster while that participant is
  selecting an identity.
- The selected theme has fewer available unique names or avatars than open
  player slots.
- A player submits an empty, overlong, or control-character-containing name.
- A participant loses connectivity or leaves before confirming their assignment.
- A roster has been inactive for 24 hours and a participant tries to reopen it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST allow a host to create a private roster for
  one to ten players and select a curated theme.
- **FR-002**: Each curated theme MUST provide distinct player-name suggestions
  and a matching set of avatar choices sufficient for a ten-player roster.
- **FR-003**: The host MUST be able to review and change roster assignments
  before and after inviting participants.
- **FR-004**: The application MUST provide an invitation that the host can share
  with players and revoke. A host MUST approve each join request, and the host
  MUST be able to remove a participant or close the roster.
- **FR-005**: An approved participant MUST be able to select an available name
  and avatar from the active theme. A participant MUST only be able to edit
  their own assignment.
- **FR-006**: Names MUST be unique within a roster. Names MUST contain between
  one and 32 displayed characters after trimming, and MUST NOT contain control
  characters. The application MUST reject invalid names without saving them.
- **FR-007**: Roster changes and participant readiness MUST be reflected to all
  current participants within five seconds under normal connectivity.
- **FR-008**: A participant MUST be able to mark their current assignment ready.
  Any change to that assignment MUST clear that participant's ready state.
- **FR-009**: The application MUST present each participant with their final
  name, selected avatar, a way to copy the name, and instructions to apply the
  identity manually in the game or on their game profile.
- **FR-010**: The application MUST keep rosters private from public discovery,
  require an active invitation and host approval for entry, and reject joins
  after the roster is closed, the invitation is revoked, or the ten-player
  limit is reached.
- **FR-011**: The application MUST clearly explain invalid input and access
  errors without exposing private roster information to unauthorized visitors.
- **FR-012**: Roster data MUST be deleted when the host closes the roster or
  after 24 hours without activity.

### Key Entities *(include if feature involves data)*

- **Roster**: A temporary private group plan with a host, selected theme,
  participants, invitation status, and activity state.
- **Theme**: A curated visual and naming style with paired name suggestions and
  avatar choices.
- **Participant**: A host or approved player associated with a roster and their
  selected name, avatar, and readiness state.
- **Assignment**: The unique name and avatar selection a participant intends to
  use for the themed group identity.
- **Invitation**: A revocable means for a player to request entry to a roster.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A host can create a roster, choose a theme, and select their own
  name and avatar in under two minutes.
- **SC-002**: A group of ten players can join, select distinct names and
  matching avatars, and complete a roster without exceeding the player limit.
- **SC-003**: At least 95% of roster changes appear to all connected participants
  within five seconds during acceptance testing with normal connectivity.
- **SC-004**: At least 90% of first-time participants can join, select an
  assignment, and mark themselves ready without assistance.
- **SC-005**: In usability testing, at least 90% of participants can correctly
  identify their assigned name and avatar and explain that they must apply them
  manually.

## Assumptions

- “Sync” means coordinating a shared themed roster and readiness state; the
  application does not sign in to, or directly change, Counter-Strike 2 or Steam
  accounts.
- The first release uses curated themes and avatar choices. Participants cannot
  upload images or create custom themes.
- A roster supports up to ten participants, including the host, to cover a full
  match group.
- Players can join without creating an application account, but the host must
  approve each join request.
- Rosters are temporary and expire after 24 hours without activity; closing a
  roster deletes its data.
- Participants have access to the game or profile settings where they can
  manually apply their assigned name and avatar.
