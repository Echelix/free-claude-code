---
name: upstream-merge
description: Merge upstream Alishahryar1/free-claude-code into the Echelix fork while preserving the Echelix layer. Use when the user says "sync upstream", "pull upstream", "upstream merge", "upstream sync", or asks to bring in upstream fixes or features.
---

# Upstream Merge Skill

Execute a controlled upstream sync from `Alishahryar1/free-claude-code` into this Echelix
fork. Since the 2026-09 re-base the fork shares upstream's `src/free_claude_code/` layout,
so the sync is a plain `git merge upstream/main` on a sync branch, followed by a short,
predictable conflict pass. Do **not** cherry-pick commit-by-commit any more.

## Reference material

The Echelix layer inventory, conflict playbook and sync history are in
`references/upstream-sync-guide.md` (mirror of `docs/UPSTREAM_SYNC.md`). Read it first.

---

## Execution steps

### 1. Verify clean state

```bash
git checkout main && git pull origin main && git status
```

Must be clean. If not, stop and tell the user to commit or stash first.

### 2. Fetch and survey

```bash
git fetch upstream                                  # add the remote first if missing
git log --oneline main..upstream/main | wc -l
git diff --name-status main..upstream/main | awk '$1=="D"'   # deletions
```

Flag any deletion that touches the Echelix layer (see the reference's inventory).

### 3. Merge on a sync branch

```bash
git checkout -b sync/upstream-$(date +%Y-%m)
git merge upstream/main
```

### 4. Resolve conflicts

Follow playbook patterns A–F in the reference. Key rules:

- **README.md** → take theirs, re-insert the `## Echelix Fork` section before `## Project Links`.
- **pyproject.toml** → take theirs, keep the four Echelix script lines; update the scripts
  test in `tests/cli/test_entrypoints.py`.
- **Files with `# Echelix:` hunks** (`config/model_refs.py`, `config/settings.py`,
  `config/logging_config.py`, `runtime/bootstrap.py`, `config/admin/manifest.py`) → keep
  both sides; re-apply the marked hunk if the surrounding code moved.
- **`.gitignore`, `tests.yml`** → ours for the `.claude` rules and `push:` trigger, theirs otherwise.
- **`uv.lock`** → theirs, then `uv lock --check`.

Then `git add -A && git commit --no-edit`.

### 5. Verify

```bash
uv sync --all-groups
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest --tb=no -q
uv run pytest tests/cli/test_background.py tests/config/test_model_deprecations.py tests/config/test_logging_config.py -q
```

**Pass criterion:** failures ≤ upstream/main's own failure count, and every Echelix test
passes. Regressions must be fixed before merging.

### 6. Fast-forward main and push

```bash
git checkout main
git merge --ff-only sync/upstream-YYYY-MM
git push origin main
git branch -d sync/upstream-YYYY-MM
```

### 7. Record the sync

Add an entry to `docs/UPSTREAM_SYNC.md` → "Sync history" (range merged, conflicts hit,
result), then copy the file over `references/upstream-sync-guide.md`.

---

## Summary format

```
[Files Changed] N files, upstream range <old>..<new>
[Logic Altered] notable upstream features/fixes now in the fork; any Echelix hook re-ported
[Verification Method] ruff + ty + pytest (N failed, M passed) vs upstream baseline
[Residual Risks] known gaps or deferred items
```
