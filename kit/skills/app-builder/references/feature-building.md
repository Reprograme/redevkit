# Feature Building

> How to analyze and implement new features. The pipeline is `{{CMD:redevkit-enhance}}`
> (small and medium changes) or `{{CMD:redevkit-plan}}` (large changes).

## Feature Analysis

```text
Request: "add payment system"

Analysis:
├── Required Changes:
│   ├── Database: orders, payments tables
│   ├── Backend: /api/checkout, /api/webhooks/stripe
│   ├── Frontend: CheckoutForm, PaymentSuccess
│   └── Config: Stripe API keys
│
├── Dependencies:
│   ├── stripe package
│   └── Existing user authentication
│
└── Scope: DB + 2 API routes + 2 components + config
```

## Iterative Enhancement Process

```text
1. Analyze the existing project and architecture (code-archaeologist + memory)
2. Record the change in specs/NNN-short-name/ (spec delta + tasks.md)
3. If UI is modified or added: check and align with DESIGN.md
4. Present the change plan to the user and get approval
5. Apply the changes with the specialist personas
6. Test and validate (lint, typecheck, unit tests) with evidence
7. Start a local preview with redevkit-preview
```

## Error Handling

| Error Type | Solution Strategy |
|------------|-------------------|
| TypeScript Error | Fix type, add missing import |
| Missing Dependency | Run npm install |
| Port Conflict | Suggest alternative port |
| Database Error | Check migration, validate connection |

## Recovery Strategy

```text
1. Detect error
2. Try automatic fix
3. If failed, report to user
4. Suggest alternative
5. Rollback if necessary
```
