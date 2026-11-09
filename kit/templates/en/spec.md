---
type: spec
feature: "[###-feature-name]"
status: draft
created: "[DATE]"
updated: "[DATE]"
---

# Feature Specification: [FEATURE NAME]

**Feature directory**: `specs/[###-feature-name]/`

**Branch**: `[###-feature-name]` (optional; omit this line when no branch was created)

**Status**: Draft

**Input**: User description: "[FEATURE DESCRIPTION AS WRITTEN BY THE USER]"

## User Scenarios & Testing *(mandatory)*

<!--
  User stories are user journeys ordered by importance (P1 = most critical).
  Each story must be INDEPENDENTLY TESTABLE: implementing only that story still delivers a
  viable increment that can be developed, tested, deployed and demonstrated on its own.
  Every acceptance scenario becomes a failing test before implementation (Test-First).
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [The value and why it has this priority]

**Independent Test**: [How it can be tested on its own, e.g. "Can be fully tested by [action] and delivers [value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [The value and why it has this priority]

**Independent Test**: [How it can be tested on its own]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [The value and why it has this priority]

**Independent Test**: [How it can be tested on its own]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with a priority]

### Edge Cases

- What happens when [boundary condition]?
- How does the system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g. "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g. "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g. "reset their password"]
- **FR-004**: System MUST [data requirement, e.g. "persist user preferences"]

*Marking an unclear requirement (at most 3 markers per spec):*

- **FR-005**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email and password, SSO, OAuth?]

### Key Entities *(include if the feature involves data)*

- **[Entity 1]**: [What it represents, key attributes, no implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  Measurable and technology-agnostic: no frameworks, languages, databases or APIs.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g. "Users complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g. "1,000 concurrent users without visible slowdown"]
- **SC-003**: [Satisfaction metric, e.g. "90% of users complete the main task on the first try"]
- **SC-004**: [Business metric, e.g. "Support tickets about [X] drop by 50%"]

## Assumptions

<!--
  Reasonable defaults chosen where the description was silent, and recommendations adopted
  without an answer (--auto). One line each.
-->

- [Assumption about users, e.g. "Users have a stable internet connection"]
- [Assumption about scope, e.g. "Mobile support is out of scope for v1"]
- [Dependency on an existing system, e.g. "Reuses the existing user profile API"]

## Clarifications

<!--
  Filled by the clarify phase. One subsection per session:
  ### Session YYYY-MM-DD
  - Q: <question> → A: <answer>
  Leave this section empty when the spec is first written.
-->

## Enhancements

<!--
  Filled by the enhance command, which appends one dated subsection per change:
  ### YYYY-MM-DD — <title>
  Leave this section empty when the spec is first written.
-->
