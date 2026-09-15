# Upstream Sync Guide

> How to pull fixes and features from `Alishahryar1/free-claude-code` (upstream)
> into the Echelix fork without losing Echelix-specific additions.

---

## Why this process exists

The Echelix fork has diverged structurally from upstream:

| Echelix has | Upstream has |
| ----------- | ------------ |
| `start/` workflow scripts (`fcc-start`, `claudex`, etc.) | (deleted) |
| `docs/SECURITY.md` security audit | (deleted) |
| `.env.nvidia.example` NVIDIA template | (deleted) |
| `README_NVIDIA.md` NVIDIA setup guide | (never existed) |
| `claude-pick` model selector script | (deleted) |
| `nvidia_nim_models.json` reference list | (deleted) |
| `core/cli/` package layout | renamed to `cli/` |

A naive `git merge upstream/main` would generate ~10+ modify/delete conflicts
and a structural rename conflict on every sync. **Cherry-picking specific
upstream commits onto a sync branch** is the safer pattern — surgical, easy
to abort, and never touches `main` until verified.

---

## One-time setup

The `upstream` remote is already configured:

```bash
git remote -v
# origin   https://github.com/Echelix/free-claude-code.git (fetch/push)
# upstream https://github.com/Alishahryar1/free-claude-code.git (fetch/push)
```

If you cloned fresh and need to re-add it:

```bash
git remote add upstream https://github.com/Alishahryar1/free-claude-code.git
```

---

## Sync workflow

Run this whenever you want to pull in upstream fixes/features.

### 1. Start clean

```bash
git checkout main
git pull origin main
git status   # must report "nothing to commit, working tree clean"
```

If you have uncommitted work, commit or stash it first.

### 2. Fetch upstream history

```bash
git fetch upstream
```

This downloads upstream commits without touching any local branch.

### 3. Survey what's new

```bash
# What's in upstream that you don't have
git log --oneline main..upstream/main

# Scope of the diff
git diff --stat main..upstream/main | tail -5

# What upstream has DELETED that you still have (highest-risk signal)
git diff --name-status main..upstream/main | awk '$1=="D"'

# What upstream has RENAMED
git diff --name-status main..upstream/main -M | awk '$1 ~ /^R/'
```

The deletion list is the most important — if upstream deletes
`start/`, `claude-pick`, `docs/SECURITY.md`, `.env.nvidia.example`,
`nvidia_nim_models.json`, or `README_NVIDIA.md`, **you are keeping all of
them**. See [Echelix-specific files](#echelix-specific-files-to-preserve).

### 4. Triage commits into tiers

Read commit subjects and decide what to pull. Use this rubric:

| Tier | What goes in | Action |
| ---- | ------------ | ------ |
| **1 — Functional & security fixes** | bug fixes, CVE fixes, protocol corrections, auth hardening | Cherry-pick |
| **2 — Features** | new providers, new endpoints, new capabilities | Cherry-pick if you want them |
| **3 — README / config / cosmetic / dependency bumps** | README rewrites, `.env.example` reshaping, dependency bumps that affect `pyproject.toml`, image changes, star charts | **Skip** — they almost always conflict with Echelix-specific docs/config |

Quick filters to identify high-value commits:

```bash
# Just the fixes
git log --oneline main..upstream/main | grep -iE "^[a-f0-9]+ (fix|feat\(security\)|security)"

# Sort the candidates chronologically (cherry-pick in this order)
for sha in <sha1> <sha2> <sha3>; do
  git log -1 --format="%ad %h %s" --date=iso $sha
done | sort
```

### 5. Create a sync branch

Never cherry-pick onto `main` directly — sync branches are your safety net.

```bash
git checkout -b sync/upstream-$(date +%Y-%m)
```

### 6. Cherry-pick chronologically

Apply commits in their original upstream order (oldest first). This minimizes
conflicts because each commit lands against a tree close to what its author saw.

```bash
git cherry-pick -x <sha>
```

The `-x` flag adds a `(cherry picked from commit <sha>)` trailer for traceability.

If you hit a conflict, see the [Conflict playbook](#conflict-resolution-playbook).

### 7. Verify

After all cherry-picks land:

```bash
uv run ruff format --check
uv run ruff check
uv run ty check
uv run pytest --tb=no -q
```

Compare failure counts against `main`:

```bash
# On your sync branch, capture the count
uv run pytest --tb=no -q 2>&1 | tail -3

# Check baseline on main
git stash; git checkout main
uv run pytest --tb=no -q 2>&1 | tail -3
git checkout sync/upstream-YYYY-MM; git stash pop 2>/dev/null
```

**Pass criterion:** failure count must be ≤ main's count. Pre-existing failures
are okay; *regressions* are not.

### 8. Fast-forward into main and push

```bash
git checkout main
git merge --ff-only sync/upstream-YYYY-MM
git push origin main
git branch -d sync/upstream-YYYY-MM
```

If `--ff-only` fails (someone else pushed to `main`), use a regular merge
or rebase the sync branch first.

---

## Conflict resolution playbook

These four patterns cover almost every conflict you'll hit.

### Pattern A — README.md content conflict

**Symptom:** `CONFLICT (content): Merge conflict in README.md`

**Cause:** Echelix's README has different structure (NVIDIA-focused walk-throughs,
Documentation section) than upstream's restructured layout.

**Resolution:** keep your version on every README conflict.

```bash
git checkout --ours README.md
git add README.md
git cherry-pick --continue --no-edit
```

If the upstream commit's *only* purpose is a README change, **skip it entirely**:

```bash
git cherry-pick --abort   # if you haven't started staging
# or
git cherry-pick --skip    # if mid-cherry-pick
```

### Pattern B — Modify/delete on Echelix-specific files

**Symptom:**

```text
CONFLICT (modify/delete): claude-pick deleted in HEAD and modified in <sha>
```

Wait — that's the opposite direction. The realistic version:

```text
CONFLICT (modify/delete): start/README.md deleted in <sha> and modified in HEAD
```

**Cause:** upstream deleted a file you've kept (and possibly modified).

**Resolution:** keep your version, drop upstream's deletion intent.

```bash
git checkout HEAD -- <path>
git add <path>
git cherry-pick --continue --no-edit
```

If the upstream commit was *primarily* about deleting Echelix-kept files
(e.g. `d78869d` "Removed cached models list"), skip the whole commit:

```bash
git cherry-pick --skip
```

### Pattern C — `core/cli/` vs `cli/` path mismatch

**Symptom:**

```text
CONFLICT (modify/delete): cli/entrypoints.py deleted in HEAD and modified in <sha>
```

**Cause:** upstream renamed `core/cli/` → `cli/`. A cherry-pick of any post-rename
commit lands a file at `cli/<x>.py` but your tree expects `core/cli/<x>.py`.

**Resolution:** apply the change to your fork's path manually.

```bash
# 1. See exactly what the commit changed
git show <sha> -- cli/<file>.py

# 2. Discard the misplaced file the cherry-pick wrote
rm cli/<file>.py
rmdir cli 2>/dev/null

# 3. Apply the equivalent edit to core/cli/<file>.py
#    (use Edit tool / your editor)

# 4. Stage and continue
git add core/cli/<file>.py
git cherry-pick --continue --no-edit
```

If the change touches a symbol that doesn't exist in your fork's `api/app.py`,
`config/settings.py`, etc., either skip the commit or do a deeper port.

### Pattern D — Feature commit landing before its dependency

**Symptom:**

```text
CONFLICT (modify/delete): providers/kimi/request.py deleted in HEAD and modified in <sha>
```

**Cause:** you're cherry-picking a fix that touches a file added by an *earlier*
upstream commit you haven't picked yet.

**Resolution:** abort, pick the prerequisite first, then retry.

```bash
git cherry-pick --abort
git cherry-pick -x <prerequisite-sha>
git cherry-pick -x <original-sha>
```

When in doubt, walk the upstream log forward and pick prerequisites before
their dependents (this is why step 6 says cherry-pick chronologically).

---

## Echelix-specific files to preserve

Always keep these — never accept upstream deletions:

| Path | Why |
| ---- | --- |
| `start/` (entire directory) | `fcc-start` / `claudex` background-server workflow |
| `docs/SECURITY.md` | Echelix security audit (data egress, auth, recommended hardening) |
| `docs/UPSTREAM_SYNC.md` | This file |
| `.env.nvidia.example` | NVIDIA-focused environment template |
| `README_NVIDIA.md` | NVIDIA NIM setup guide |
| `claude-pick` | Interactive model selector script |
| `nvidia_nim_models.json` | NVIDIA NIM reference model list |
| `core/cli/` package layout | Echelix kept the original layout; upstream renamed to `cli/` |

The Documentation section in the root `README.md` (links to `README_NVIDIA.md`,
`start/README.md`, `docs/SECURITY.md`, this file) is also Echelix-specific.
Keep it on every README merge.

---

## Skip list — commits that almost never apply cleanly

These categories are safe to skip and rarely worth the merge friction:

- README rewrites (e.g. star chart, contribution guidelines, image swaps)
- `.env.example` updates that don't apply to `.env.nvidia.example`
- Dependency bumps that touch `pyproject.toml` or `uv.lock` heavily
- Default-timeout / config-default tweaks when `.env.nvidia.example` already pins them
- Docs/scripts under `start/` (upstream deleted this directory; nothing should target it)

---

## Reference: prior sync example

### 2026-09 sync (2026-09-15) — 28 upstream commits

Upstream had 505 unpicked commits. Only the window before upstream's June 2026
refactor wave (transports/API/messaging/CLI packages, then `src/free_claude_code/`
namespace move `71a78a0c` on 2026-07-09) was cherry-pickable. Picked, oldest first:

```text
f389cf41 fix: default logs to logs/ and ignore rotations (issue 427)
e5edffa2 Pass proxy auth token to Telegram CLI sessions
d05446f0 Remove Anthropic API key from proxy child env
23e409cb Add fireworks AI support (#476)
fe98abf6 feat(admin): add Fireworks API key and proxy to admin manifest
f5e49ea7 Add OpenCode Go subscription gateway provider (#505)
51d5f29a fix(opencode_go): authenticate with OPENCODE_API_KEY
87057693 Add Mistral Provider
1324c36d Add Gemini Provider
b2f66db0 Add Groq Provider
ab842fd9 Add Cereberas Provider
fbb1d658 feat(providers): native Anthropic Messages for Kimi, Fireworks, Z.ai
a4d7d760 Add Codestral Provider
26c5b356 Reorder providers in README and other places
8ae77959 fix(gemini): nest google extra body for sdk
cebdc02a fix: accept system role messages
e4d6dc1f fix: avoid dual gemini thinking controls
d501e522 Fix live provider smoke defaults
885c26d9 Surface upstream provider errors
fedcc0a3 Fix Gemini thought signature replay
044a152f Add Gemini thought signature smoke
0eee1da0 Try mid stream retries
b867e080 Improve smoke provider coverage and skips
0fb4c7d6 fix: remove duplicate api/admin_static wheel force-include
103869f6 Ignore removed thinking env keys
544008a9 Removed stale ignore (resolved to no-op; fork never had `server.*`)
e79b430c Raise stream and upstream retry attempts to five total.
c1af215f fix: normalize proxy auth token whitespace
```

Skipped (deliberate):

- `a728994e` / `ac2c37f6` / `fc3ef0b5` — relocate config from `~/.config/free-claude-code`
  to `~/.fcc` and add `config/paths.py`. Fork keeps the original location.
- `37974db1` / `943c3db6` / `494c6c9d` / `bd2aaed8` / `543da3d6` — admin UX refactor;
  depends on the `~/.fcc` relocation and removes user-configurable `CLAUDE_WORKSPACE`,
  `CLAUDE_CLI_BIN`, `ZAI_BASE_URL`.
- `89d86d11` Removed PLAN.md (fork keeps it), CI restructure, compaction-window tweaks,
  install/uninstall scripts under `scripts/` (fork uses `start/`), all README/.env.example/
  dep-bump commits.
- Everything from `3abe41d2` (Codex, 2026-06-16) onward — see "Residual" below.

Conflict patterns hit: A (README ×8), plus new variants:

- `config/logging_config.py` / `config/settings.py` — fork has `truncate_log_on_start` and
  audit-log docstring; merged upstream's `mkdir(parents=True)` + `logs/server.log` default.
- `tests/api/test_admin.py` ×4 — each provider commit re-adds the same four admin-UX-only
  tests (`*_omits_stale_*`, `*_preserves_hidden_*`) and `not in keys` asserts. Kept only the
  provider-specific test and assert; rewrote env path `.fcc/.env` → `.config/free-claude-code/.env`.
- `config/provider_catalog.py` — took upstream order wholesale, re-added `base_url_attr="zai_base_url"`.
- `pyproject.toml` / `uv.lock` ×4 — upstream version bumps; kept fork `2.0.0`, re-ran `uv lock`.
- `api/app.py` — upstream uses `server_log_path()` from skipped `config/paths.py`; kept ours
  (fork's `Settings.log_file` already honours `LOG_FILE`).
- **Gotcha:** `uv run python` refuses to start while `pyproject.toml` has conflict markers.
  Use `.venv/bin/python` for resolution scripts, or `git add` will stage the markers.

Echelix fixups committed after cherry-picks:

- `tests/cli/test_cli.py`, `tests/cli/test_cli_manager_edge_cases.py`: `cli.*` → `core.cli.*`
  (the latter also repaired 3 failures that were pre-existing on main).
- `tests/providers/test_registry.py`: import `build_provider_config`.
- Docs (`docs/SECURITY.md`, `start/README.md`, `README_NVIDIA.md`) reference `logs/server.log`.

Result: 2 failures (both pre-existing on main: `test_admin_config_masks_secrets_and_exposes_manifest`,
`test_core_does_not_import_product_packages`), down from 5; +147 new passing tests (1451 total).

**Residual:** ~315 upstream commits after 2026-06-16 are not cherry-pickable with this
playbook. Upstream refactored transports, API pipeline, messaging, CLI, settings and admin
into packages (June 2026) and then moved all runtime code under `src/free_claude_code/`
(`71a78a0c`, 2026-07-09). Future syncs need a different strategy (re-base the Echelix
additions onto upstream, or path-rewritten patch application).

---

### 2026-05 second sync (2026-05-13) — 17 upstream commits

```text
6b7ba35 feat: add Wafer provider
d63605e Add NVIDIA NIM CLI smoke matrix and tool schema aliasing
7491b04 Add Claude CLI smoke matrices
3be97e4 Initial admin impl
35ac54f log urls at startup
6175f29 Improve admin UI setup flow
bdb29a5 Allow unauthenticated root probes
044677a feat(logging): structured TRACE events and end-to-end request correlation
5e11d1d feat(providers): retry upstream HTTP 503 like 429
504c661 feat(providers): retry all upstream 5xx like 429
4ce400e fix(openai): close async client with supported method
8ff1bc7 fix(cli): terminate launched process trees
bafccc7 fix(cli): exit fcc-server cleanly on interrupt
acbf101 fix(cli): resolve claude command before launch
545fa35 fix: handle disallowed special tokens in tiktoken encoder (#382)
87b04d4 feat(opencode): integrate OpenCode Zen provider and API key support (#426)
1599fd3 feat(providers): add Z.ai Coding Plan provider (#440)
```

Skipped: all README-only commits, `07b30aa` (dep bump), `3bde98a` (timeout defaults),
`5669fb2`/`05909e9` (merge commits), `6b8c697` (readme), `5706d00` (readme).

Conflict patterns hit: A (README ×6), C (`core/cli/` path ×4 — entrypoints, manager,
session; `api/admin_config.py` package ref).

Additional Echelix fixups committed after cherry-picks:

- All new upstream test files used `cli.*` / `cli.session.*` / `cli.entrypoints.*` patch
  targets — updated to `core.cli.*` throughout.
- `api/admin_config.py:_template_text()` referenced `importlib.resources.files("cli")` —
  changed to `"core.cli"`.
- Architecture contract test `expected` set had `"cli"` — removed (not a package root).

Result: 5 failures (all pre-existing on main); +130 new passing tests.

---

### 2026-05 first sync — 14 upstream commits

```text
9367b40 fix: accept betas body field (#360)
06e0fb3 feat: add Kimi (Moonshot) provider (#335)
6c9b2b4 Filter OpenRouter model variants by thinking support
02472a5 Add no-thinking model picker variants
5cac9db Added claude-code native model picker
ef30c0d Report startup validation failures without tracebacks
90dd729 Log startup model validation failures clearly
2454db4 Validate configured models at startup
91ed5a8 fix(deepseek): document blocks + tool_result (#358)
e7d5ad2 fixed deepseek issue
98c26b3 fix(security): constant-time auth comparison (#262)
4d45f91 fix: only strip valid env assignments (#229)
8375d83 Fix null usage in SSE for OpenAI-compatible streams
32e1020 fix(messaging): reuse parent CLI session for Telegram (#233)
```

Skipped:

- `d78869d` "Removed cached models list" — would have deleted `nvidia_nim_models.json`.
- All upstream README/image/config-default commits.

Conflict patterns hit: A (README), B (claude-pick deletion), C (`core/cli/` path),
D (Kimi prerequisite for #360).

Result: same failure count as `main` baseline; +52 new passing tests.

---

## Related

- [README_NVIDIA.md](../README_NVIDIA.md) — NVIDIA NIM environment configuration
- [start/README.md](../start/README.md) — Production workflow
- [docs/SECURITY.md](SECURITY.md) — Security audit
- [AGENTS.md](../AGENTS.md) — Coding environment requirements (run order: ruff format → ruff check → ty check → pytest)
