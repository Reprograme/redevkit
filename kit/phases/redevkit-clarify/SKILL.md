---
name: redevkit-clarify
description: Resolve spec ambiguities: up to 5 questions, one at a time, with recommendations.
---

# redevkit-clarify

Internal phase. Finds the decisions the active spec still leaves open, asks about the ones
that matter, and writes each answer back into `spec.md`. Called by
`{{CMD:redevkit-brainstorm}}` (active feature), by `{{CMD:redevkit-plan}}` and by
`redevkit-specify` (to resolve `[NEEDS CLARIFICATION]` markers).

Write into the spec in the project language ({{LANG}}). Ask the user in their language.
Build every question with [dynamic-questioning](references/dynamic-questioning.md).

## Input (from the calling command)

- Feature directory (default: the active feature in `.redevkit/memory/active.md`).
- Mode: `full` (taxonomy scan) or `markers` (only the spec's `[NEEDS CLARIFICATION]` markers).
- Question budget: 5 minus the questions the command already asked.
- Optional focus given by the user (for example "security" or "offline behavior").
- `--auto` flag, if the command runs in auto mode.

## Section names

| Section | en | pt-BR |
| --- | --- | --- |
| Clarifications | `## Clarifications` | `## Esclarecimentos` |
| Session | `### Session YYYY-MM-DD` | `### Sessão AAAA-MM-DD` |
| Stories | `## User Scenarios & Testing` | `## Cenários de Usuário e Testes` |
| Edge cases | `### Edge Cases` | `### Casos de Borda` |
| Requirements | `### Functional Requirements` | `### Requisitos Funcionais` |
| Entities | `### Key Entities` | `### Entidades-Chave` |
| Outcomes | `## Success Criteria` | `## Critérios de Sucesso` |
| Assumptions | `## Assumptions` | `## Suposições` |

Use the headings already present in the spec.

## Steps

### 1. Locate the spec

Read `specs/NNN-short-name/spec.md`. If it is missing, stop and tell the caller to run the
specify step of `{{CMD:redevkit-plan}}`; never create a spec here.

### 2. Load constraints

Read `.redevkit/memory/constitution.md` and the out-of-scope list in
`.redevkit/memory/project.md`. Never propose an option that violates a MUST principle.

### 3. Scan for ambiguity

In `full` mode, mark each category Clear, Partial or Missing in an internal coverage map:

- Functional scope and behavior: goals, success criteria, out of scope, roles.
- Domain and data: entities, identity and uniqueness, lifecycle, volume.
- Interaction and UX: critical journeys; error, empty and loading states; accessibility;
  localization.
- Non-functional: performance, scalability, reliability, observability, security and
  privacy, compliance.
- Integrations: external services and their failure modes, formats, versioning.
- Edge cases: negative scenarios, rate limits, concurrent edits.
- Constraints and trade-offs: technical constraints, rejected alternatives.
- Terminology: canonical terms, synonyms to avoid.
- Completion signals: testable acceptance criteria, measurable done.
- Placeholders: TODOs, vague adjectives ("fast", "intuitive") without numbers.

In `markers` mode, skip the scan: the queue is the spec's markers (at most 3).

### 4. Build the queue

Turn Partial and Missing categories into candidate questions ranked by impact ×
uncertainty, and keep at most the budget (never more than 5). Keep only questions whose
answer changes architecture, data, tasks, tests, UX or compliance. Drop questions already
answered, stylistic preferences and pure implementation choices (those belong to the plan).

### 5. Ask, one question at a time

Each question has:

- `**Question:**` one interrogative sentence ending in `?` (an FR or SC ID may follow in
  parentheses), never a bare label;
- one plain sentence saying why it matters;
- at most 3 options, the recommended one first and marked "(Recommended)" with a one-line
  reason; for open questions, 2-3 alternatives with trade-offs (table format in the
  reference);
- "yes" or "recommended" accepts the recommendation; another short answer is allowed.

{{ASK}}

A follow-up to disambiguate an unclear answer does not count as a new question. Stop when
the critical ambiguities are resolved, the user says "done" or "stop", or the budget is used.
Never show queued questions in advance. If this phase runs inside a subagent, do not ask:
return the queue, with recommendations, to the orchestrator.

### 6. Integrate and save after each answer

- On the first answer of the run, make sure the Clarifications section exists (create it at
  the end of the spec if missing) and add today's Session subheading.
- Append `- Q: <question> → A: <answer>`.
- Apply the answer where it belongs: functional requirement, user story or scenario, key
  entity, success criterion (turn vague words into numbers), edge case, or a term normalized
  across the spec (`(formerly "X")` once, if needed). Replace a marker or an obsolete
  statement; never leave contradictory text.
- Save `spec.md` immediately (overwrite the whole file).

### 7. Validate

After each save and once at the end, check that:

- there is one bullet per accepted answer, no duplicates, and the total is within budget;
- no marker or vague placeholder remains that an answer was meant to resolve;
- the only new headings are the Clarifications section and the Session subheading;
- the same canonical term is used across all updated sections.

### 8. Re-validate the quality checklist

If `checklists/requirements.md` exists, re-check each item against the spec saved in step 6
and toggle only the markers whose state changed (see
`{{SKILLDIR:redevkit-specify}}/references/requirements-checklist.md`). Record the before and
after counts, for example `12/16 → 15/16`.

## Auto mode

With `--auto` (or a non-interactive run), do not ask. Adopt each recommendation, write it in
the Session as `- Q: <question> → A: <answer> (assumed, --auto)`, and add it to the
Assumptions section.

## Report to the caller

- Questions asked and answered; path of the updated spec; sections touched.
- Checklist before and after counts, items newly passing, regressions, items still open.
- Coverage table: each category with Resolved, Deferred (budget or implementation detail),
  Clear or Outstanding.
- Recommendation: proceed with the plan, or run clarify again after planning.
- If nothing worth asking was found: "No critical ambiguities detected" and a compact
  coverage summary.
