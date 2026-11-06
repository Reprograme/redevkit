---
type: constitution
created: "[RATIFICATION_DATE]"
updated: "[LAST_AMENDED_DATE]"
---

# [PROJECT_NAME] Constitution

<!--
  The project's laws. Every plan runs a Constitution Check against this file; analysis and
  convergence treat a MUST violation as CRITICAL. Changes only through the amendment
  procedure in Governance (gate G1). Replace every [FIELD]; remove these comments once filled.
-->

## Core Principles

### I. Test-First (NON-NEGOTIABLE)

**TDD**: required

Every user story starts with tests that express its acceptance scenarios. The tests MUST be
run and seen to FAIL before the implementation is written, then MUST pass before the story
is done (red, green, refactor). A task is done only when its VERIFY check was observed.

*Rationale*: tests written first pin the expected behavior and prove the code does what the
spec says.

*Waiver*: this principle can be relaxed only by an amendment the user approves, which changes
the line above to `**TDD**: waived`, states the reason and the scope, and bumps the MAJOR
version.

### II. [PRINCIPLE_2_NAME]

[PRINCIPLE_2_DESCRIPTION]
<!-- Example: II. Verification with evidence - no task, test run or audit is reported as
passing without the command that ran and its observed result; skipped checks are SKIPPED. -->

### III. [PRINCIPLE_3_NAME]

[PRINCIPLE_3_DESCRIPTION]
<!-- Example from a domain skill: III. Performance budget - the game MUST hold 60 FPS on the
target devices; frame time is measured in every release candidate. -->

### IV. [PRINCIPLE_4_NAME]

[PRINCIPLE_4_DESCRIPTION]
<!-- Example: IV. Simplicity - start with the simplest design that meets the spec (YAGNI);
extra layers or projects are justified in the plan's Complexity Tracking. -->

### V. [PRINCIPLE_5_NAME]

[PRINCIPLE_5_DESCRIPTION]
<!-- Example: V. Security by default - secrets never enter the repository, memory or
artifacts; input from users and URLs is validated. Add or remove principles as needed. -->

## Technical Constraints

[TECHNICAL_CONSTRAINTS]
<!-- Stack, platforms, engine, performance targets, compliance. Derived from tech.md and
from the domain skills, e.g. "Engine: Phaser 3; target: desktop and mobile browsers". -->

## Design and User Interface

<!-- Remove this section when the project has no user interface. -->

- `DESIGN.md` at the project root is the single visual source of truth; UI work MUST read
  it first and use its tokens.
- Purple Ban: purple and violet are not used by default. The brand or `DESIGN.md` may lift
  the ban explicitly.
- [ACCESSIBILITY_TARGET, e.g. "WCAG 2.2 AA contrast and full keyboard access"]

## Development Workflow

[DEVELOPMENT_WORKFLOW]
<!-- Example: features follow spec → plan → tasks → implementation → test; the plan is
approved before code (gate G2); commits only when the user asks; destructive actions need
explicit confirmation. -->

## Governance

- This constitution prevails over every other project practice. Precedence: the user's
  request > this constitution > `AGENTS.md` > command skills > personas > knowledge skills.
- **Compliance**: every plan has a Constitution Check that cites this file; analysis and
  convergence check MUST principles; a violation stops the work (gate G3) until it is fixed
  or justified in the plan's Complexity Tracking and accepted by the user.
- **Amendments**: proposed explicitly, shown to the user and applied only after confirmation
  (gate G1). Each amendment updates the version line below and appends a Sync Impact Report
  to `.redevkit/memory/changelog.md` (version change, principles and sections changed,
  templates and artifacts to review, deferred items).
- **Versioning** (semver): MAJOR for removing or redefining a principle incompatibly
  (including a TDD waiver); MINOR for a new principle or section, or materially expanded
  guidance; PATCH for wording and clarifications.
- [ADDITIONAL_GOVERNANCE_RULES]

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
