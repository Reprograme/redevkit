# Code state

The code state ties a test or verify run to the exact code it ran on. The test and verify
commands record it in the **Code state** table of their report run; the verify command (step
1, to reuse a test run), the status command and the deploy command recompute it and compare.

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

- **Case of the reserved folders.** When the file system of the project folder ignores case
  (Windows, macOS by default; the script probes the folder instead of assuming it from the
  OS), the reserved names match in any case: `SPECs/` is the `specs/` folder the kit writes
  to, so a report written there never changes the code state. On a case-sensitive file
  system `Specs/` is a different folder from `specs/` and may hold code, so it stays in.
- **Git submodules.** A checked-out submodule counts with its own files (tracked plus
  untracked, not ignored), under its path: an uncommitted edit inside it and a checkout of
  another revision both change the fingerprint. A submodule that is not checked out counts
  with the commit the index records for it. The recorded commit of a checked-out submodule
  is not hashed: like any commit made after a run, staging or committing a submodule bump
  does not change the code state (its content already did).
- **Nested git repositories.** An untracked folder with its own `.git` that is not a
  submodule (a clone that was never added) counts like a checked-out submodule: with its own
  files (tracked plus untracked, not ignored), under its path, so an edit inside it changes
  the fingerprint. A folder whose files cannot be listed (a nested repository git cannot
  read, a folder the script cannot open) is never left out in silence: the Tree fingerprint
  is `n/a (code state unavailable: cannot list <folder>/ …)` and `--expect` prints
  `Compare: DIFFERENT (code state unavailable: …)` (exit 1). Repair the folder, or add it to
  `.gitignore` when it is not code, and run the script again.
- **Executable bit.** A file whose git index mode is `100755` counts as executable (an
  untracked file, or any file without git: its execute bit, on a POSIX file system only;
  Windows has none), so `chmod +x` followed by `git add`, or `git update-index --chmod=+x`,
  changes the fingerprint. A file that is not executable is hashed as before: the
  fingerprint of a project without executable files is the one older kit versions recorded.

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

## Compare (verify step 1, status, deploy and the Unverified list)

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

1. **Reference:** the latest run of the active feature's `verification.md`. A test run never
   is the reference: the test command runs the spec scope only, and only the verify runs the
   whole suite with the convergence and the audits.
2. It must be `converged+verified`, and `active.md` › Last results › `- Unverified:` must be
   `none` (rules in [loops](loops.md)). No active feature, no verify run, another verdict or
   a feature still listed as Unverified → `BLOCKED`: require `redevkit-verify`.
3. No later red test: every run that the active feature's `test-report.md` has after the test
   run the reference names in its Test evidence (the file is append-only, so they came later)
   must be `PASS`. A `FAIL` run there → `BLOCKED`, even on the same code: that verify no longer
   holds (the test command also marks `- Verify:` in `active.md` as `invalidated by test
   FAIL`); require a new `redevkit-verify`.
4. Same code state as the reference → every row of the Preconditions table is `OK`. A
   different code state → `BLOCKED`: the current code was not verified; require
   `redevkit-verify`.
5. The code state cannot be computed (no Python interpreter): `BLOCKED` with the reason
   `code state unavailable`. Running the verify again does not change that: ask the user to
   install Python 3.9 or newer, or to override stating that the code did not change since the
   reference run.
