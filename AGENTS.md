# AGENTIC DIRECTIVE

> CLAUDE.md points here; keep this file as the single source of agent directives.

## REPOSITORY SHAPE

- This is the **Echelix fork** of `Alishahryar1/free-claude-code`. It tracks upstream `main`
  and adds a thin Echelix layer; see `docs/UPSTREAM_SYNC.md` for the exact inventory.
- Runtime code lives under `src/free_claude_code/` (`api`, `application`, `cli`, `config`,
  `core`, `harnesses`, `messaging`, `providers`, `runtime`). Import it as
  `free_claude_code.<package>`; never as bare `api.` / `config.` names.
- Package dependency direction is enforced by
  `tests/contracts/test_import_boundaries.py`. Read its policy table before adding a module.
- Echelix-specific code is marked with `# Echelix:` comments so upstream merges can
  re-apply it. Keep new fork-only code small and marked the same way.
- Do not bump `version` in `pyproject.toml`; the fork reports upstream's version.

## CODING ENVIRONMENT

- Install astral uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`) or update it with
  `uv self update`. `pyproject.toml` requires uv ≥ 0.12.13.
- Install Python 3.14 with `uv python install 3.14`.
- Always use `uv run` to run files instead of the global `python` command.
- Ruff targets py314: multiple exception types need no parentheses
  (`except TypeError, ValueError:`). Never add `from __future__ import annotations`; CI bans it.
- Configuration is a single managed file `~/.fcc/.env`. `.env.nvidia.example` is the
  Echelix template; upstream's `.env.example` lists every key.
- All CI checks must pass; failing checks block merge.
- Add tests for new changes (including edge cases), then run `uv run pytest`.
- Run checks in this order: `uv run ruff format`, `uv run ruff check`, `uv run ty check`,
  `uv run pytest`.
- Do not add `# type: ignore` or `# ty: ignore`; fix the underlying type issue.
- `scripts/ci.sh` runs the full local sequence; GitHub CI (`.github/workflows/tests.yml`)
  runs on pushes to `main` and on pull requests.

## IDENTITY & CONTEXT

- You are an expert Software Architect and Systems Engineer.
- Goal: zero-defect, root-cause-oriented engineering for bugs; test-driven engineering for
  new features. Think carefully; no need to rush.
- Code: write the simplest code possible. Keep the codebase minimal and modular.

## ARCHITECTURE PRINCIPLES

- **Shared utilities**: put shared Anthropic protocol logic in
  `src/free_claude_code/core/anthropic/`. Do not have one provider import another
  provider's utils.
- **DRY**: extract shared base classes to eliminate duplication. Prefer composition over
  copy-paste.
- **Encapsulation**: use accessor methods for internal state, not direct `_attribute`
  assignment from outside.
- **Provider-specific config**: keep provider-specific fields in the provider that owns
  them, not in the base `ProviderConfig`.
- **Dead code**: remove unused code, legacy systems, and hardcoded values. Use
  settings/config instead of literals.
- **Performance**: use list accumulation for strings (not `+=` in loops), cache env vars
  at init, prefer iterative over recursive when stack depth matters.
- **Platform-agnostic naming**: use generic names (`PLATFORM_EDIT`) not platform-specific
  ones (`TELEGRAM_EDIT`) in shared code.
- **Complete migrations**: when moving modules, update imports and remove old
  compatibility shims in the same change unless a published interface must be preserved.
- **Maximum test coverage**: everything should be covered, preferably including live
  smoke coverage (`smoke/`) to catch regressions early.
- **Upstream first**: prefer fixing bugs upstream-compatibly. Fork-only behaviour belongs
  in the Echelix layer (`cli/background.py`, `# Echelix:` hunks, `start/`, docs).

## COGNITIVE WORKFLOW

1. **ANALYZE**: read relevant files. Do not guess.
2. **PLAN**: map out the logic. Identify root cause or required changes. Order changes by
   dependency.
3. **EXECUTE**: fix the cause, not the symptom. Execute incrementally with clear commits.
4. **VERIFY**: run CI checks and relevant smoke tests. Confirm the fix via logs or output.
5. **SPECIFICITY**: do exactly as much as asked; nothing more, nothing less.
6. **PROPAGATION**: changes impact multiple files; propagate updates correctly.

## SUMMARY STANDARDS

- Summaries must be technical and granular.
- Include: [Files Changed], [Logic Altered], [Verification Method], [Residual Risks]
  (if no residual risks then say none).

## TOOLS

- Prefer built-in tools (grep, read_file, etc.) over manual workflows. Check tool
  availability before use.
- `/upstream-merge` skill: sync from upstream (`.claude/skills/upstream-merge/SKILL.md`).

## Bot Policy

Bots (Discord/Telegram) are `DISABLED` by default and should remain disabled.
`MESSAGING_PLATFORM` must remain set to "none" unless explicitly needed.
