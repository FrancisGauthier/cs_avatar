<!--
Sync Impact Report
- Version change: 1.2.0 -> 1.2.1
- Modified principles: VII. Repository Structure (clarified code documentation versus Spec Kit artifacts)
- Added sections: none
- Added principles: none
- Removed sections: none
- Follow-up TODOs: RATIFICATION_DATE remains TODO because the original adoption date is unknown; existing application paths outside the canonical layout require a separately planned migration
-->

# cs_avatar Constitution

## Core Principles

### I. Security First
Security is a non-negotiable product requirement. Every feature, dependency, data flow,
and integration MUST be evaluated for confidentiality, integrity, availability, and
misuse resistance before release. Secure defaults, least privilege, defense in depth,
and explicit error handling MUST be preferred over convenience. Rationale: security
failures can compromise users and invalidate every other product goal.

### II. Complete Input Validation
All user-controlled input MUST be validated at the boundary where it enters the
application, using explicit type, shape, size, range, encoding, and authorization
checks appropriate to its use. Validation MUST occur again at security-sensitive
backend or integration boundaries and MUST reject invalid input with a clear,
non-sensitive error. Rationale: validation prevents malformed, unexpected, and
hostile data from reaching application logic or external systems.

### III. SPA-First Architecture
Features MUST maximize useful work in the single-page application and MUST minimize
server and backend responsibilities. A backend or server endpoint MAY be added only
when it is required for security, protected secrets, trusted authorization, durable
shared state, or an external integration that cannot safely run in the client.
Client-side behavior MUST remain functional and testable without unnecessary server
round trips. Rationale: a smaller backend reduces attack surface, operational cost,
latency, and architectural complexity.

### IV. Testable Contracts
Every feature MUST define testable behavior and explicit contracts for inputs,
outputs, errors, and security-sensitive decisions. New validation rules, client-server
boundaries, persistence behavior, and integration contracts MUST have focused tests
covering valid, invalid, and boundary cases. Rationale: executable contracts expose
regressions and make security and SPA behavior reviewable.

### V. Simplicity and Maintainability
Implementations MUST use the simplest design that satisfies the requirements and
these principles. Complexity, new dependencies, backend endpoints, and persistent
state MUST have a documented need and an owner. Repeated logic SHOULD be centralized
behind clear, typed interfaces, and obsolete paths MUST be removed when safe.
Rationale: small, understandable systems are easier to secure, test, and operate.

### VI. Counter-Strike 2 Brand and Theme Consistency
Every user-facing surface MUST consistently evoke Counter-Strike 2's competitive,
tactical setting through a coherent visual style, including color, typography,
imagery, and tone. The product MUST use original or properly authorized assets and
MUST NOT imply official affiliation without authorization. Reviews of user-facing
changes MUST verify consistency with the product's Counter-Strike 2-inspired
identity. Rationale: consistent theming makes the application recognizable to its
intended players while distinguishing it from the official game.

### VII. Repository Structure
Application source MUST be organized under the root `src/` directory,
code and product documentation under `docs/`, automated tests under `tests/`,
and infrastructure and deployment configuration under `infra/`. Documentation
in `docs/` MUST describe the code or its use; it MUST NOT contain Spec Kit's
feature-planning artifacts. Spec Kit feature artifacts, including specifications,
plans, tasks, and checklists, MUST remain under the configured `specs/` feature
directory. Spec Kit templates, scripts, and memory MUST remain under `.specify/`.
Each directory MAY contain subdirectories as needed, but projects MUST NOT add
parallel root-level directories for these same purposes. Root-level manifests,
version-control metadata, and tool configuration MAY remain at the repository
root. Existing application content outside this layout MAY remain until a
separately planned migration; new application files MUST use the canonical
directories. Rationale: consistent locations make code, documentation, tests,
and operational configuration easier to discover and maintain.

## Security and Architecture Constraints

The application MUST avoid embedding secrets or privileged credentials in client
code. Sensitive operations MUST use narrowly scoped backend capabilities with
validated requests, authenticated and authorized access, rate limiting where
appropriate, and safe logging that excludes secrets and unnecessary personal data.
Client and server boundaries MUST use explicit schemas and versioned contracts.
Data collection and retention MUST be limited to what the feature requires.
Build and code-documentation tools MUST create new files in the canonical
directories defined by Principle VII. Spec Kit commands MUST keep feature
artifacts under `specs/` and tool configuration under `.specify/`.

## Development Workflow and Quality Gates

Each change MUST identify its affected principles, validation boundaries, and
client-server interactions. Reviews MUST verify input validation, authorization,
secret handling, error behavior, and whether any backend work is justified. Before
release, the smallest relevant test suite MUST pass, security-sensitive changes
MUST receive focused review, and known exceptions MUST be documented with an owner,
mitigation, and expiration or re-evaluation date.

## Governance

This constitution is the highest-level project governance document. If another
practice conflicts with it, the conflict MUST be resolved in favor of this
constitution or recorded as an approved exception.

Amendments MUST document the proposed change, its rationale, affected principles,
migration impact, and validation plan. Amendments require review by the project
maintainers and MUST update the version, last-amended date, and Sync Impact Report.
The constitution MUST be reviewed during planning and code review for changes that
affect security, input handling, architecture, data, or operational behavior.

Versioning follows semantic versioning: MAJOR for backward-incompatible governance
changes or principle removals/redefinitions, MINOR for new principles or materially
expanded requirements, and PATCH for clarifications and non-semantic refinements.
Approved exceptions do not suspend the constitution; they are temporary, explicit,
and subject to the documented mitigation and review date.

**Version**: 1.2.1 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date is unknown | **Last Amended**: 2026-11-25
