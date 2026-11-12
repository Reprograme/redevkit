# Code state

The code state ties a test or verify run to the exact code it ran on. The test and verify
commands record it in the **Code state** table of their report run; the verify command (step
1, to reuse a test run) and the deploy command recompute it and compare.

Two code states are the **same** when their **Tree fingerprint** is equal. The fingerprint is
a hash of the contents of the project's files, so it changes whenever a file is added,
removed, renamed or edited, tracked by git or not, and it does not depend on the shell, on the
commit history or on git being present. A commit made after a run does not change it.

## Scope

The fingerprint covers the project's code. It never covers `.redevkit/`, `specs/` or the agent
folders (`.claude/`, `.agents/`, `.codex/`) at the project root: reports and memory are written
after a run and must not make the code look changed. Dependencies, build output and generated
reports are left out too (what git ignores, plus the shared defaults in
`.redevkit/audits/README.md`).

## Record (test and verify)

Run from the project root, right after the suite (the verify command: when it writes its
report; it changes no code after step 1). `<PY>` is the interpreter found as
`.redevkit/audits/README.md` describes. The script is read-only.

```bash
<PY> .redevkit/audits/code_state.py .
```

Copy its lines into the Code state table of the run: Commit (HEAD), Branch, Working tree,
Changed files and Tree fingerprint (`sha256:…`).

- Not a git repository: Commit (HEAD) is `n/a (not a git repository)`, Branch and Working tree
  are `n/a`; the Tree fingerprint is still computed.
- No commit yet: Commit (HEAD) is `none`.
- No Python interpreter: the Tree fingerprint is `n/a (no Python interpreter)`. Fill Commit
  (HEAD), Branch and Working tree from `git rev-parse HEAD`, `git branch --show-current` and
  `git status --porcelain` when git exists.

## Compare (verify step 1, status and deploy)

Give the recorded fingerprint to the script; it prints `Compare: SAME` (exit 0) or
`Compare: DIFFERENT` (exit 1):

```bash
<PY> .redevkit/audits/code_state.py . --expect sha256:<recorded fingerprint>
```

- A fingerprint that starts with `n/a` is never the same as anything, and neither is a run
  recorded without a Tree fingerprint (reports written by an older kit version).
- Commit (HEAD), Branch and Working tree are context for the reader: they never decide the
  comparison.

## Deploy reference run

The single definition; the deploy command and its template refer here. Look only at the active
feature:

1. **Verify pending:** `active.md` › Last results › `- Verify pending:` names this feature
   (after a debug, or after a verify that ended in `gaps` or `failed`; rule in
   `redevkit-verify` step 6). Then there is no reference: `BLOCKED` until `redevkit-verify`
   ends in `converged+verified`.
2. Otherwise the reference is the **latest feature-wide** run (Scope `feature`) of its
   `test-report.md` (standalone or run by verify step 1), and it must be `PASS`.
3. No active feature, or no test run → no reference: `BLOCKED`.
4. Same code state as the reference and a `PASS` reference → every row of the Preconditions
   table is `OK`. Anything else → `BLOCKED`: the current code was not tested. Require
   `redevkit-verify` when a verify is pending, otherwise `redevkit-test`.
5. The code state cannot be computed (no Python interpreter): `BLOCKED` with the reason
   `code state unavailable`. Running the tests again does not change that: ask the user to
   install Python 3.9 or newer, or to override stating that the code did not change since the
   reference run.
