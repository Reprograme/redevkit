# Code state

The code state ties a test or verify run to the exact code it ran on. The test and verify
commands record it in the **Code state** table of their report run; the verify command (step
1, to reuse a test run) and the deploy command recompute it and compare. Every command here is read-only (`git hash-object` without `-w`
writes nothing).

## Scope

The fingerprints cover the project except `.redevkit/` and `specs/`: reports and memory are
written after the run and must not make the code look changed. Use this pathspec in every
`git status` and `git diff` below:

```text
-- . ':(exclude).redevkit' ':(exclude)specs'
```

## Record (test and verify)

Run from the project root, right after the suite (the verify command: when it writes its
report; it changes no code after step 1), in the same shell type the deploy will use (the
fingerprints hash command output, so mixing shells can change them).

```bash
git rev-parse HEAD                     # Commit (HEAD)
git branch --show-current              # Branch
git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs'
                                       # Changed files; empty = clean, otherwise dirty
git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin
                                       # Status fingerprint
git diff HEAD -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin
                                       # Diff fingerprint
```

The same lines work in PowerShell. Copy the values into the Code state table of the run.

- Not a git repository: Commit (HEAD) is `n/a (not a git repository)` and the other fields
  are `n/a`.
- No commit yet: Commit (HEAD) is `none`; use `git diff --cached` instead of `git diff HEAD`.
- Line-ending warnings on stderr do not change the fingerprints; ignore them.

## Compare (verify step 1 and deploy)

Two code states are the **same** when Commit (HEAD), Working tree, Status fingerprint and Diff
fingerprint are all equal (step 2 below), or when the commit-after-run rule (step 3) holds. A
field that starts with `n/a` (not a git repository) is never equal to anything. The verify
command uses this to decide whether it can reuse the latest `test-report.md` run; the deploy
command uses it on its reference run.

1. **Deploy reference run** (the single definition; the deploy command and its template refer
   here). Look only at the active feature:
   - **Debug pending:** `active.md` › Last results › Debug names this feature and is newer
     than the latest `converged+verified` run of its `verification.md` (or there is no such
     run). Then there is no reference: `BLOCKED` until `redevkit-verify` runs (verify is
     mandatory after a debug, D26).
   - Otherwise the reference is the **latest feature-wide** run (Scope `feature`) of its
     `test-report.md` (standalone or run by verify step 1), and it must be `PASS`.
   - No active feature, or no test run → no reference: `BLOCKED`.
2. Recompute every field with the same commands and the same shell type, and compare each with
   the reference: Commit (HEAD), Working tree, Status fingerprint, Diff fingerprint.
3. Commit made after the run (HEAD differs, everything else may differ too): the code is
   still the tested code when the current tree, compared with the **reference** commit, gives
   the recorded diff fingerprint and nothing is untracked:

   ```bash
   git diff <reference HEAD> -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin
   git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs'   # no "??" lines
   ```

   Equal → the same code state (note "committed after test" in the report).
4. Deploy: same code state and a `PASS` reference → every row of the Preconditions table is
   `OK`. Anything else (no reference, a reference that is not `PASS`, a different code state,
   `n/a` fields) → `BLOCKED`: the current code was not tested. Require `redevkit-verify` when a
   debug is pending, otherwise `redevkit-test`.
