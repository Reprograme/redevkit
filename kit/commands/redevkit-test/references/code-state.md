# Code state

The code state ties a test or verify run to the exact code it ran on. The test and verify
commands record it in the **Code state** table of their report run; the deploy command
recomputes it and compares. Every command here is read-only (`git hash-object` without `-w`
writes nothing).

## Scope

The fingerprints cover the project except `.redevkit/` and `specs/`: reports and memory are
written after the run and must not make the code look changed. Use this pathspec in every
`git status` and `git diff` below:

```text
-- . ':(exclude).redevkit' ':(exclude)specs'
```

## Record (test and verify)

Run from the project root, right after the suite, in the same shell type the deploy will use
(the fingerprints hash command output, so mixing shells can change them).

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

## Compare (deploy)

1. Reference run: the latest `PASS` run of the active feature's `test-report.md`, or the
   latest `converged+verified` run of `verification.md` when a debug happened after that
   test.
2. Recompute every field with the same commands and the same shell type.
3. Each row of the deploy report's Preconditions table is `OK` when equal:
   Commit (HEAD), Working tree, Status fingerprint, Diff fingerprint.
4. Commit made after the run (HEAD differs, everything else may differ too): the code is
   still the tested code when the current tree, compared with the **reference** commit, gives
   the recorded diff fingerprint and nothing is untracked:

   ```bash
   git diff <reference HEAD> -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin
   git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs'   # no "??" lines
   ```

   Equal → every row is `OK` (note "committed after test" in the report).
5. Any other difference, a reference that is not green, or `n/a` fields → `BLOCKED`: the
   current code was not tested. Require a new test run.
6. The only way past `BLOCKED` is `OVERRIDDEN`: a reason stated by the user, recorded in
   their words in the deploy report.
