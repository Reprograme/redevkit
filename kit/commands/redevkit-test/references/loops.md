# Test loops

The single definition of the two test ↔ debug loops, of the lines they keep in `active.md` ›
Last results and of gate G5. The test, verify, debug, deploy and status commands and the
specify phase refer here.

## Two scopes

| Scope | Command | What runs | Loop on a code defect | Limit |
| --- | --- | --- | --- | --- |
| `spec` | `redevkit-test` | The tests of the active feature only (its spec test set) | test → debug → test | 5 debug rounds → G5 |
| `global` | `redevkit-verify` | The whole suite, then convergence, execution and audits | verify → debug → verify | 3 debug rounds, or 3 rounds without convergence → G5 |

A `PASS` in the spec scope proves the feature; it never proves the rest of the project, so
only a verify (global scope) opens the way to the deploy. Only code defects enter a loop: a
`product-defect` test failure and, in the verify, a build failure, an application that does
not start, a broken flow or a blocking audit. The other failure classes leave the loop
(`redevkit-test` step 4).

## The lines

```text
- Failing scope: specs/NNN-name — spec | global | none
- Test cycle: specs/NNN-name — debug rounds N/5 [· G5 reached YYYY-MM-DD HH:MM, waiting for the user]
- Correction cycle: specs/NNN-name — debug rounds N/3 · rounds without convergence N/3 [· G5 reached YYYY-MM-DD HH:MM, waiting for the user]
- Unverified: none | specs/NNN-name, specs/NNN-name
```

Labels and values stay in English in every language. Date and time come from the system
clock, never guessed.

Failing scope, Test cycle and Correction cycle belong to the feature they name. A line that
names another feature (or none) reads as `none` and zero counters with no G5 marker; the
command that writes it rewrites it for the active feature. A `- Verify pending:` line written
by kit 1.1 or older is obsolete: delete it when writing Last results; it never blocks
anything.

### Failing scope

Tells the debug command where to hand back.

- `redevkit-test` writes `spec` when its run is `FAIL` by a `product-defect` (the failure
  belongs to the debug command, also when G5 holds the handoff back), and `none` after any
  other run.
- `redevkit-verify` writes `global` when its verdict is `failed` by a code defect (also when G5
  holds the handoff back), and `none` after any other verdict.
- The debug command reads it: `spec` → back to `redevkit-test`; `global` → back to
  `redevkit-verify`; `none`, another feature or no line → it asks (`redevkit-debug` §
  Handoff).

### Test cycle (spec scope)

- **Debug rounds:** the debug command adds 1 on every handoff it makes in this loop (Failing
  scope `spec`), whatever the run changed: back to `redevkit-test` after a fix or with a wrong
  test (so a test ↔ debug disagreement is bounded too), and to `redevkit-create` for behavior
  never built (so test → debug → create → test is bounded too). Reset to 0 by a test `PASS` and
  when the user chooses continue at G5.
- **G5:** a test run that would hand off to the debug command while debug rounds is 5 or more
  (five fixes did not make the spec tests pass) reaches G5 instead.

### Correction cycle (global scope)

- **Debug rounds:** the debug command adds 1 on every handoff it makes in this loop (Failing
  scope `global`), whatever the run changed: back to `redevkit-verify` after a fix or with a
  wrong test (a wrong test of a `global` failure always goes back to `redevkit-verify`, never
  to `redevkit-test`, so the whole suite judges it again), and to `redevkit-create` for
  behavior never built, so verify → debug → create → test → verify is bounded too. A test
  `PASS` never resets this counter. Reset to 0 by a verify that ends in `converged+verified` or
  `gaps`. A verify that follows a debug handback never reuses the old `FAIL` test run
  (`redevkit-verify` step 1), so every round is judged on a new run.
- **Rounds without convergence:** the verify command adds 1 for a `gaps` verdict and for a
  `failed` verdict that hands off to the create command (`not-implemented`), and resets it to 0
  on `converged+verified`. A `failed` verdict that hands off to the debug command is counted by
  the debug rounds instead, so the limit of 3 debug rounds is the one that applies to a code
  defect. Test runs never change it, so a gaps → create → test → verify loop still reaches
  G5. A `failed` verdict whose only failure class is `environment`, or that reused a `FAIL`
  test run on the same code (nothing changed and no debug handback since), changes neither
  counter: the code was not judged. An `environment` `FAIL` is never reused, so the next
  verify runs the suite again; neither is a `test-defect` `FAIL`, whose test correction or
  question for the user only the test procedure resolves.
- **G5:** a verify reaches G5 when its verdict is `failed` while debug rounds is 3 or more, or
  when rounds without convergence reaches 3.

Both cycles reset when the user chooses continue at G5 (only the cycle that reached it), and
a new active feature starts new lines.

### Unverified

Features that left the active slot without a verify, so that no feature skips the
convergence and the audits.

- The specify phase (and the enhance command when it makes another feature active) appends
  the previous active feature when the active feature changes, unless the latest run of its
  `verification.md` is `converged+verified` and its Tree fingerprint is the current one
  ([code-state](code-state.md) § Compare).
- The verify command converges and audits the active feature and every listed feature, and
  writes `none` when it ends in `converged+verified`. A gap found in a listed feature becomes a
  Convergence task of the **active** feature's `tasks.md` (citing the listed feature's spec),
  because the create and test commands work on the active feature only. An open or blocked
  task in the listed feature's own `tasks.md` does not cover the gap: it is carried into the
  active feature's `tasks.md` once (`redevkit-converge` step 3), so each round has work the
  create command can run.
- The deploy is `BLOCKED` while the line lists any feature. To drop a feature that was
  abandoned, the user asks `redevkit-memanager` to remove it from the line; the reason goes to
  `changelog.md`.

## G5

Write `G5 reached` with the date and time to the line of the cycle that reached it, present
the evidence of the runs that counted (test runs, bug folders, verify runs) and ask:

1. Revise the plan with `redevkit-plan` (Recommended): clear the G5 marker, reset that cycle's
   counters and hand off to the plan.
2. Continue: clear the G5 marker, reset that cycle's counters and follow the handoff of that
   run's verdict (the debug command for a code defect, the create command for gaps).
3. Stop: keep the G5 marker; the chain ends. The next run of a command of that loop asks
   again.

The chain stops here even in `--auto`; no handoff runs until the user answers. Only these
answers clear the marker. When the question is asked again at a precondition (test: Test
cycle; verify: Correction cycle; debug: either), there is no verdict yet: continue means
proceed with that run, revise hands off to the plan, stop ends the run.
