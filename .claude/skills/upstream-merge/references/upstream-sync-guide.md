# Upstream Sync Guide

> How to pull fixes and features from `Alishahryar1/free-claude-code` (upstream)
> into the Echelix fork without losing Echelix-specific additions.

---

## Current model: merge, not cherry-pick

On 2026-09-15 the fork was **re-based onto upstream `main` (6.2.31)**. The old flat
layout (`api/`, `core/cli/`, …) is gone; the tree is now upstream's
`src/free_claude_code/` package plus a thin Echelix layer. The pre-rebase history is
preserved in `main` (the re-base landed as a merge commit) and tagged
`pre-rebase-2026-09`.

Because the fork now shares upstream's structure, syncing is a plain merge:

```bash
git checkout main && git pull origin main && git status   # must be clean
git fetch upstream
git checkout -b sync/upstream-$(date +%Y-%m)
git merge upstream/main
```

Expect a handful of predictable conflicts, all listed in the
[conflict playbook](#conflict-playbook). Cherry-picking is no longer needed and the
old modify/delete storm no longer happens.

---

## One-time setup

```bash
git remote -v
# origin   https://github.com/Echelix/free-claude-code.git
# upstream https://github.com/Alishahryar1/free-claude-code.git
git remote add upstream https://github.com/Alishahryar1/free-claude-code.git  # if missing
```

---

## The Echelix layer

Everything the fork adds on top of upstream. Keep all of it on every merge.

### Files upstream does not have

| Path | Purpose |
| ---- | ------- |
| `start/` | `setup-env.*`, `server.*`, `run.*` scripts and the background-workflow README |
| `README_NVIDIA.md` | NVIDIA NIM setup guide (managed config, model tiers, auth) |
| `.env.nvidia.example` | NVIDIA-focused template for `~/.fcc/.env` |
| `docs/SECURITY.md` | Security audit (paths remapped to the `src/` layout) |
| `docs/UPSTREAM_SYNC.md` | This file |
| `AGENTS.md`, `CLAUDE.md` | Coding-agent directives (upstream removed theirs) |
| `.claude/skills/` | `upstream-merge` and `python-api-docs` skills |
| `src/free_claude_code/cli/background.py` | `fcc-start` / `fcc-stop` / `fcc-status` |
| `src/free_claude_code/cli/models_check.py` | `fcc-models`: configured refs vs live provider `/models` |
| `tests/cli/test_background.py`, `tests/cli/test_models_check.py` | Tests for the above |
| `tests/config/test_model_deprecations.py` | Tests for the NIM deprecation self-heal |

### Edits inside upstream-owned files

| File | Echelix change | Marker |
| ---- | -------------- | ------ |
| `pyproject.toml` | `claudex`, `fcc-start`, `fcc-stop`, `fcc-status`, `fcc-models` console scripts | comment `# Echelix background-server workflow` |
| `tests/cli/test_entrypoints.py` | `test_cli_scripts_are_registered` expects the five extra scripts | the five entries |
| `src/free_claude_code/config/model_refs.py` | `DEPRECATED_NVIDIA_NIM_MODELS`, `replace_deprecated_model_ref`, applied inside `normalize_retired_model_settings` | comment `# Echelix:` |
| `src/free_claude_code/config/settings.py` | `truncate_log_on_start` (`TRUNCATE_LOG_ON_START`) | comment `# Echelix:` |
| `src/free_claude_code/config/logging_config.py` | `truncate_on_start` parameter of `configure_logging` | docstring paragraph |
| `src/free_claude_code/runtime/bootstrap.py` | passes `truncate_on_start=settings.truncate_log_on_start` | one line |
| `src/free_claude_code/config/admin/manifest.py` | `TRUNCATE_LOG_ON_START` diagnostics field | spec after `LOG_LEVEL` |
| `tests/config/test_logging_config.py` | three truncate tests appended | `Echelix:` docstrings |
| `README.md` | `## Echelix Fork` section before `## Project Links` | heading |
| `.gitignore` | `.claude/*` + `!.claude/skills/`, `.fcc.pid`, notes/DS_Store patterns | vs upstream's bare `.claude` |
| `.github/workflows/tests.yml` | `push: branches: [main]` trigger added | `on:` block |

### Deliberately not carried forward

- `claude-pick` and `nvidia_nim_models.json`: relied on the `token:provider/model` auth
  suffix that upstream removed. Claude Code's native `/model` picker (fed by the proxy's
  model catalog) replaces them.
- `fcc-init` and the `free-claude-code` alias: upstream removed them; config is managed
  through the Admin UI and `~/.fcc/.env`.
- `PLAN.md`: described the old layout. The dependency policy now lives in
  `tests/contracts/test_import_boundaries.py`.
- The fork's `2.0.0` version: the fork reports upstream's version so
  `fcc-server --version` and the issue-form version checks stay meaningful.

---

## Sync workflow

### 1. Start clean, fetch, survey

```bash
git checkout main && git pull origin main && git status
git fetch upstream
git log --oneline main..upstream/main | wc -l
git diff --name-status main..upstream/main | awk '$1=="D"'   # deletions touching the Echelix layer?
```

### 2. Merge on a sync branch

```bash
git checkout -b sync/upstream-$(date +%Y-%m)
git merge upstream/main
```

### 3. Resolve conflicts with the playbook, then

```bash
git add -A && git commit --no-edit
```

### 4. Verify

```bash
uv sync --all-groups
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest --tb=no -q
```

Pass criterion: failure count ≤ `upstream/main`'s own count (check with a worktree if in
doubt; upstream occasionally ships environment-specific failures such as
`tests/scripts/test_installers.py` on macOS). Then confirm the Echelix layer still works:

```bash
uv run pytest tests/cli/test_background.py tests/config/test_model_deprecations.py tests/config/test_logging_config.py -q
uv run fcc-start && uv run fcc-status && uv run fcc-stop
```

### 5. Fast-forward main and push

```bash
git checkout main
git merge --ff-only sync/upstream-YYYY-MM
git push origin main
git branch -d sync/upstream-YYYY-MM
```

### 6. Record the sync

Add an entry under [Sync history](#sync-history) and mirror this file to
`.claude/skills/upstream-merge/references/upstream-sync-guide.md`.

---

## Conflict playbook

### A. `README.md`

Upstream rewrites its README often. Take **theirs**, then re-insert the `## Echelix Fork`
section (copy it from `git show main:README.md`) immediately before `## Project Links`.

### B. `pyproject.toml` scripts

Take theirs for everything except the four Echelix script lines under
`# Echelix background-server workflow`; keep those. Update
`tests/cli/test_entrypoints.py::test_cli_scripts_are_registered` to match whatever
upstream added plus the Echelix four.

### C. `config/model_refs.py`, `settings.py`, `logging_config.py`, `bootstrap.py`, `admin/manifest.py`

Keep both sides. The Echelix hunks are small and marked `# Echelix:`; re-apply them on top
of upstream's version if the surrounding code moved. If upstream renames
`normalize_retired_model_settings` or changes `configure_logging`'s signature, port the
Echelix hook to the new shape and run the two Echelix test files.

### D. `.gitignore` / `tests.yml`

Keep ours for the `.claude` rules and the `push:` trigger; take theirs for the rest.

### E. Upstream deletes or moves an Echelix-touched file

`git checkout HEAD -- <path>` restores ours. If upstream moved the surrounding module,
move the Echelix code with it.

### F. `uv.lock`

Take theirs, then `uv lock` to confirm it is consistent (`uv lock --check`).

---

## Sync history

### 2026-09-15 — re-base onto upstream 6.2.31

Fork was 505 commits behind and structurally incompatible (upstream moved to
`src/free_claude_code/` on 2026-07-09 after a June refactor wave). Re-built the fork as
upstream/main + the Echelix layer described above, landed on `main` as a merge commit so
the pre-rebase history remains reachable (tag `pre-rebase-2026-09`).

Ported: `fcc-start` / `fcc-stop` / `fcc-status` (new `cli/background.py`, PID file moved to
`~/.fcc/fcc.pid`, spawns `fcc-server`), `claudex` (alias of `fcc-claude`), NIM deprecated
model self-heal (hooked into `normalize_retired_model_settings`), `TRUNCATE_LOG_ON_START`
(settings + Admin field + `configure_logging`), all docs and `start/` scripts rewritten for
the managed-config model. Retired `claude-pick`, `nvidia_nim_models.json`, `PLAN.md`.

Result: ruff/ty clean; pytest matched upstream's baseline (5 macOS-only installer test
failures pre-existing on upstream) plus the new Echelix tests passing.

### 2026-09-15 — last cherry-pick sync (pre-rebase)

28 upstream commits from mid-May to early June 2026 (Fireworks, OpenCode Go, Mistral,
Codestral, Gemini, Groq, Cerebras providers; stream recovery; error surfacing; retry and
auth fixes). Superseded the same day by the re-base above.

### 2026-05 — two cherry-pick syncs (pre-rebase)

31 upstream commits total (Kimi, Wafer, OpenCode Zen, Z.ai providers; admin UI; structured
TRACE logging; CLI process fixes; security fixes). See git history before
`pre-rebase-2026-09` for details.

---

## Related

- [README_NVIDIA.md](../README_NVIDIA.md): NVIDIA NIM configuration
- [start/README.md](../start/README.md): background proxy workflow
- [docs/SECURITY.md](SECURITY.md): security audit
- [AGENTS.md](../AGENTS.md): coding environment requirements
