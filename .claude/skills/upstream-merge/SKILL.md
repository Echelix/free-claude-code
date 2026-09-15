# Upstream Merge Skill

Execute a controlled upstream sync from `Alishahryar1/free-claude-code` into this Echelix fork using cherry-picking. Never use `git merge upstream/main` — it generates ~10+ modify/delete conflicts every time.

## Trigger

Use when the user says: "sync upstream", "pull upstream", "upstream merge", "upstream sync", or asks to bring in fixes/features from upstream.

## Reference material

Full conflict playbook, preserve list, skip list, and prior sync examples are in:
`references/upstream-sync-guide.md`

---

## Execution steps

### 1. Verify clean state

```bash
git checkout main && git pull origin main && git status
```

Must be clean. If not, stop and tell the user to commit or stash first.

### 2. Fetch and survey

```bash
git fetch upstream
git log --oneline main..upstream/main          # new commits
git diff --stat main..upstream/main | tail -5  # scope
git diff --name-status main..upstream/main | awk '$1=="D"'      # deletions — highest risk
git diff --name-status main..upstream/main -M | awk '$1 ~ /^R/' # renames
```

**Deletion alert:** if upstream deleted any Echelix-specific files (see preserve list in reference), flag it — those are kept regardless.

### 3. Triage into tiers

| Tier | Content | Action |
|------|---------|--------|
| 1 | Bug fixes, security fixes, protocol corrections | Cherry-pick |
| 2 | New providers, new endpoints, new capabilities | Cherry-pick if desired |
| 3 | README rewrites, `.env.example` changes, dep bumps, image swaps, merge commits | **Skip** |

Sort candidates chronologically before picking:

```bash
for sha in <sha1> <sha2> ...; do
  git log -1 --format="%ad %h %s" --date=iso $sha
done | sort
```

### 4. Create sync branch

```bash
git checkout -b sync/upstream-$(date +%Y-%m)
```

### 5. Cherry-pick oldest-first

```bash
git cherry-pick -x <sha>
```

On conflict, identify the pattern (A/B/C/D from the reference) and resolve. Key rules:
- **README conflict** → `git checkout --ours README.md && git add README.md`
- **Echelix file deleted upstream** → `git checkout HEAD -- <path> && git add <path>`
- **`cli/` path mismatch** → apply change to `core/cli/` instead, `git rm cli/<file>`
- **Missing dependency** → `git cherry-pick --abort`, pick prereq first, retry

After every conflict resolution: `git cherry-pick --continue --no-edit`

### 6. Fix up `core.cli` path references

Upstream uses `cli.*`; this fork uses `core.cli.*`. After all picks land, scan for broken references:

```bash
grep -rn '"cli\.' tests/ api/
grep -rn "importlib.resources.files(\"cli\")" .
```

Fix any found, then re-run checks.

### 7. Verify

```bash
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest --tb=no -q
```

Compare failure count against main baseline. **Pass criterion:** failures ≤ main's count. Regressions must be fixed before merging.

### 8. Fast-forward main and push

```bash
git checkout main
git merge --ff-only sync/upstream-YYYY-MM
git push origin main
git branch -d sync/upstream-YYYY-MM
```

### 9. Update the sync guide

Add a new entry to `docs/UPSTREAM_SYNC.md` → "Reference: prior sync example" with the picked SHAs, skipped commits, conflict patterns hit, and result (failures + new passing tests).

Also update `references/upstream-sync-guide.md` to match.

---

## Summary format

After completing, report:

```
[Files Changed] N files across M commits
[Logic Altered] what each commit added/fixed
[Verification Method] ruff + ty + pytest (N failed, M passed, +X new)
[Residual Risks] any known gaps or deferred items
```
