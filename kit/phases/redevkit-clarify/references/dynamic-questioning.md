# Dynamic question generation

> Questions are not for gathering data. They reveal **architectural consequences**.
> Every question must connect to a concrete decision that changes cost, complexity, scope or
> timeline.

Adapted from the AG Kit brainstorming skill. Used by `redevkit-clarify`, by
`{{CMD:redevkit-new}}` (short interview for a new project) and by the brainstorm pipeline.
The REDEVKIT question protocol always applies: one question at a time, at most 3 options
with the recommended one first, at most 5 questions per command, every assumption recorded.

## Core principles

### 1. Questions reveal consequences

```markdown
BAD:  "What authentication method?"
GOOD: "Should users sign up with email and password, or with a social login?"
      Impact:
      - Email/password: password reset, hashing, optional 2FA to build
      - Social login: OAuth providers, profile mapping, less control over accounts
      Trade-off: control vs. development time vs. sign-up friction
```

### 2. Context before content

| Context | Question focus |
| --- | --- |
| New project | Foundation: platform, hosting, scale, audience |
| Feature addition | Integration points, existing patterns, breaking changes |
| Refactor | Why: performance, maintainability, what is broken |
| Bug | Symptoms, root cause, reproduction path |

### 3. Minimum viable questions

Each question must remove a fork in the implementation road:

```text
Before the question:          After the answer:
├── Path A: do X (small)      └── Path A confirmed: do X
├── Path B: do Y (medium)
└── Path C: do Z (large)
```

If a question does not reduce the number of paths, delete it.

### 4. Questions generate data, not assumptions

Do not silently pick a provider, library or policy that changes the architecture. Ask, and
show what each option implies. When the answer does not change the architecture, pick a
reasonable default and record it as an assumption instead of asking.

## Generation algorithm

```text
INPUT: request + context (new project, feature, refactor, bug) + spec coverage map
│
├── 1. Parse: domain, explicit and implied features, scale indicators
├── 2. Find decision points:
│      blocking (cannot proceed) · high-leverage (>30% of the work) · deferrable
├── 3. Rank: P0 blocking > P1 high-leverage > P2 specific features > P3 edge cases
│      keep the top 5 by impact × uncertainty
└── 4. Format each question:
       what (one interrogative sentence ending in "?")
       why it matters (one plain sentence)
       options (2-3, recommended first) with trade-offs
       default if unanswered (= the recommendation)
```

Ask the queue **one question at a time**. Never reveal the queued questions in advance.

## Open questions: 2-3 alternatives with trade-offs

When a question has no natural discrete options (an approach, a flow, a policy), propose 2-3
concrete alternatives yourself and compare them:

```markdown
**Question:** How should the leaderboard handle players who are offline?
Why it matters: it decides whether the game needs a server and accounts.

| Option | What it means | Pros | Cons |
| --- | --- | --- | --- |
| A (Recommended) | Local high scores only | No server, ships fast | No competition between players |
| B | Online board with anonymous nicknames | Competition, simple | Needs a small API and abuse limits |
| C | Online board with accounts | Identity, anti-cheat | Auth, privacy, more scope |
```

## Domain question banks (starting points)

### E-commerce

| Question | Why it matters | Trade-off |
| --- | --- | --- |
| Single or multiple vendors? | Commission logic, vendor dashboards, split payments | Revenue vs. complexity |
| Track inventory? | Stock tables, reservations, low-stock alerts | Accuracy vs. time |
| Digital or physical products? | Downloads vs. shipping and tracking | Different fulfilment |
| Subscription or one-time? | Recurring billing, dunning, proration | Revenue vs. complexity |

### Authentication

| Question | Why it matters | Trade-off |
| --- | --- | --- |
| Social login? | OAuth providers vs. password reset infrastructure | UX vs. control |
| Role-based permissions? | Roles, policy enforcement, admin UI | Security vs. time |
| 2FA required? | TOTP or SMS, backup codes, recovery flow | Security vs. friction |
| Email verification? | Tokens, email service, resend logic | Security vs. sign-up friction |

### Real-time

| Question | Why it matters | Trade-off |
| --- | --- | --- |
| WebSocket or polling? | Connection management and scaling vs. simplicity | Latency vs. complexity |
| Expected concurrent users? | Single server vs. pub/sub vs. specialized infra | Scale vs. complexity |
| Persist messages? | History, storage, pagination | UX vs. storage |

### Content

| Question | Why it matters | Trade-off |
| --- | --- | --- |
| Rich text or Markdown? | Sanitization and XSS risk vs. simplicity | Features vs. safety |
| Draft and publish workflow? | Status, scheduling, versioning | Control vs. complexity |
| Multiple languages? | Translation storage, fallback logic | Reach vs. complexity |

### Games

| Question | Why it matters | Trade-off |
| --- | --- | --- |
| Target platform and input? | Web vs. mobile vs. desktop changes engine, controls, performance budget | Reach vs. effort |
| Frame-rate target? | Drives rendering budget and test thresholds | Smoothness vs. visual richness |
| Single or multiplayer? | Multiplayer adds networking, sync, cheating concerns | Engagement vs. scope |
| Save progress? | Local storage vs. accounts and a backend | Simplicity vs. continuity |

## Iterative questioning

- First pass (up to 5): blocking decisions only.
- Later passes happen in later commands, as patterns emerge ("This implies X. Handle edge
  case Y now or defer?"). Each command keeps its own limit of 5.

## Principles recap

1. Every question is a decision, not data gathering.
2. Show trade-offs so the user sees consequences.
3. Blocking decisions first.
4. Always give a recommendation; it becomes the default (and a recorded assumption) when the
   user does not answer or the run is non-interactive.
5. Domain-aware: questions differ by domain.
