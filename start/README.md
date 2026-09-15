# start — From Clone to Running Claude Code

> Step-by-step developer guide for the Echelix workflow: one managed config file, a proxy
> that runs in the background, and `claudex` to launch Claude Code from any directory.

![Python 3.14](https://img.shields.io/badge/python-3.14-blue?style=for-the-badge)

---

## What you end up with

```text
 claudex ──► Claude Code ──► http://localhost:8082 (fcc-server, background) ──► NVIDIA NIM
                                        ▲
                     ~/.fcc/.env  (the ONE config file, editable in the Admin UI)
```

| Piece | Where it lives |
| ----- | -------------- |
| Config | `~/.fcc/.env` (created by you in step 3, then owned by FCC) |
| Proxy process | `fcc-server`, started detached by `fcc-start`; PID in `~/.fcc/fcc.pid` |
| Logs | `~/.fcc/logs/server.log` (JSON lines) |
| Admin UI | `http://localhost:8082/admin` |
| Commands | `fcc-start`, `fcc-stop`, `fcc-status`, `fcc-models`, `claudex` (console scripts in `.venv/bin`) |

**What changed from the pre-September layout:** the repo-local `.env` is no longer the
config source. FCC imports it into `~/.fcc/.env` once on first start and then ignores it.
`ENABLE_*_THINKING` became `REASONING_*`, auth has an explicit `PROXY_AUTH_ENABLED` switch,
`fcc-init`, `claude-pick` and `uvicorn server:app` are gone, and the PID file moved from the
repo to `~/.fcc/fcc.pid`.

---

## Step 0: Prerequisites

| Requirement | How to check | How to install |
| ----------- | ------------ | -------------- |
| uv ≥ 0.12.13 | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (step 1 also does this) |
| Python 3.14 | installed by uv in step 1 | `uv python install 3.14` |
| Claude Code | `claude --version` | `npm install -g @anthropic-ai/claude-code` |
| NVIDIA NIM API key | starts with `nvapi-` | [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys) |
| `openssl` (for the auth token) | `openssl version` | ships with macOS/Linux; Git for Windows on Windows |

Windows users: run the `.ps1` equivalents shown in each step from PowerShell.

---

## Step 1: Clone and set up the environment

```bash
git clone https://github.com/Echelix/free-claude-code.git
cd free-claude-code
./start/setup-env.sh                # Windows: .\start\setup-env.ps1
```

`setup-env.sh` does four things:

1. Installs or updates uv and installs Python 3.14.
2. Runs `uv sync`, which creates `.venv` and installs the project, so
   `.venv/bin/fcc-start`, `fcc-stop`, `fcc-status`, `fcc-models` and `claudex` exist.
3. Warns if `~/.fcc/.env` does not exist yet (you create it in step 3).
4. Offers to append aliases for `fcc-start`, `fcc-stop`, `fcc-status`, `fcc-models` and
   `claudex` to your shell profile
   (`~/.zshrc`, `~/.bash_profile` or `~/.profile`; `$PROFILE` on Windows).

Answer `y` to the alias prompt, then reload your shell:

```bash
source ~/.zshrc                     # or ~/.bash_profile
```

**Check:** `fcc-status` prints `Proxy is not running.`

If you prefer not to use aliases, prefix every command below with `uv run` from the repo
root, for example `uv run fcc-start`.

---

## Step 2: Generate the proxy auth token

The proxy listens on `0.0.0.0:8082` by default, so it must require a bearer token.

```bash
openssl rand -base64 32
```

Copy the output; you paste it into `ANTHROPIC_AUTH_TOKEN` in the next step. Nothing else
needs the token: `claudex` reads it from the managed config and hands it to Claude Code.

---

## Step 3: Create the managed config

```bash
mkdir -p ~/.fcc
cp .env.nvidia.example ~/.fcc/.env
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.fcc
Copy-Item .env.nvidia.example $env:USERPROFILE\.fcc\.env
```

Open `~/.fcc/.env` and set the three values that have no usable default:

```dotenv
NVIDIA_NIM_API_KEY="nvapi-..."                     # from build.nvidia.com
PROXY_AUTH_ENABLED=true
ANTHROPIC_AUTH_TOKEN="<paste the openssl output>"
```

Everything else in the template is a working default:

| Key | Template value | Meaning |
| --- | -------------- | ------- |
| `MODEL` | `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` | Fallback model for unknown tiers |
| `MODEL_OPUS` | `nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b` | Reasoning-heavy requests |
| `MODEL_SONNET` | `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` | Most Claude Code traffic |
| `MODEL_HAIKU` | `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` | Fast, cheap requests |
| `REASONING_POLICY` / `REASONING_*` | `client` / `inherit`, `off`, `off` | Replaces `ENABLE_*_THINKING` |
| `PORT` | `8082` | Proxy port |
| `FCC_OPEN_BROWSER` | `false` | Keeps `fcc-start` headless |
| `TRUNCATE_LOG_ON_START` | `true` | Echelix: `false` keeps an audit trail |
| `MESSAGING_PLATFORM` | `none` | Bots stay disabled |

Only this machine needs the proxy? Add `HOST=127.0.0.1`.

**Check the models are still served** (providers retire models without notice):

```bash
fcc-models                 # every line should read LIVE; exits 1 if anything is MISSING
```

Migrating from the old layout? Copy your previous repo `.env` to `~/.fcc/.env` instead of
the template. FCC rewrites `ENABLE_*_THINKING` keys and retired Kimi K2 model refs on first
start and logs each repair.

---

## Step 4: Start the proxy

```bash
fcc-start
```

Expected output:

```text
Proxy started (PID 41234) · logs → /Users/you/.fcc/logs/server.log
```

`fcc-start` spawns `fcc-server` detached from your terminal and returns immediately.
Running it again while the proxy is up prints `Proxy already running (PID …)`.

**Check it is really serving** (give it a few seconds on first start):

```bash
fcc-status                                   # Proxy is running (PID 41234)
curl -s http://localhost:8082/health         # {"status":"healthy"}
tail -n 3 ~/.fcc/logs/server.log
fcc-models                                   # all configured models LIVE
```

On first start FCC also writes `FCC_CONFIG_SCHEMA=1` into `~/.fcc/.env` and reorders the
file. That is expected; from now on edit values in the Admin UI or in that file and restart.

---

## Step 5: Review the config in the Admin UI (optional)

Open `http://localhost:8082/admin` in a browser on the same machine. The Admin UI edits
`~/.fcc/.env` directly:

- **Providers**: paste or rotate `NVIDIA_NIM_API_KEY`; the model dropdown lists the live
  NIM catalogue.
- **Model Config**: `MODEL_*` tiers and `REASONING_*`.
- **Diagnostics** (advanced): `LOG_LEVEL`, `TRUNCATE_LOG_ON_START`.

Click **Apply**; FCC restarts itself when a changed key requires it. If you edited
`~/.fcc/.env` by hand instead, restart manually:

```bash
fcc-stop && fcc-start
```

---

## Step 6: Launch Claude Code

From any project directory:

```bash
cd ~/src/my-project
claudex
```

`claudex` (an alias of upstream's `fcc-claude`) waits up to 30 seconds for the proxy health
check, exports `ANTHROPIC_BASE_URL=http://localhost:8082` and `ANTHROPIC_AUTH_TOKEN` from the
managed config, then runs `claude` with any extra arguments you pass
(`claudex --continue`, `claudex -p "explain this repo"`).

**Check inside Claude Code:** run `/model`. The picker lists the NIM models the proxy
exposes; the default entry is your `MODEL_SONNET`. Send a prompt and watch a new line
appear in `~/.fcc/logs/server.log`.

If `claudex` prints `Free Claude Code proxy is not reachable`, run `fcc-status`; if the proxy
is not running, go back to step 4.

---

## Step 7: Stop the proxy

```bash
fcc-stop                                     # Proxy stopped (PID 41234)
fcc-status                                   # Proxy is not running.
```

`fcc-stop` sends SIGTERM (SIGBREAK on Windows) to the recorded PID and removes
`~/.fcc/fcc.pid`. A stale PID file (machine rebooted, process killed) is cleaned up
automatically by the next `fcc-status` or `fcc-start`.

---

## Daily use

```bash
fcc-start          # once per boot
claudex            # in each project, as often as you like
fcc-stop           # when you are done
fcc-models         # whenever a request fails with HTTP 410, or after git pull
```

The proxy survives closed terminals and multiple `claudex` sessions.

---

## Updating

```bash
cd free-claude-code
git pull
uv sync
fcc-models                 # confirm the configured models are still served
fcc-stop && fcc-start
```

Your config is untouched: it lives in `~/.fcc/.env`, not in the repo.

---

## Command reference

| Command | What it does |
| ------- | ------------ |
| `fcc-start` | Spawn `fcc-server` detached; write `~/.fcc/fcc.pid`; no-op if already running |
| `fcc-status` | Report whether the recorded PID is alive; remove a stale PID file |
| `fcc-stop` | Signal the recorded PID and remove the PID file |
| `fcc-models` | Compare configured `MODEL*` refs with each provider's live `/models` list; exit 1 if any is missing |
| `claudex` | Wait for the proxy, inject token and base URL, run `claude …` |
| `fcc-server` | Run the proxy in the foreground (Ctrl-C to stop); useful for debugging |
| `fcc-server --version` | Print the installed version |

Implementation: `fcc-start`/`fcc-stop`/`fcc-status` are in
`src/free_claude_code/cli/background.py`, `fcc-models` in
`src/free_claude_code/cli/models_check.py`; `claudex` is registered in `pyproject.toml`
alongside `fcc-claude`.

### Scripts in this directory

| Script | Purpose |
| ------ | ------- |
| `setup-env.sh` / `setup-env.ps1` | Step 1: uv, Python, `uv sync`, shell aliases |
| `server.sh` / `server.ps1` | Foreground proxy (`uv sync && uv run fcc-server`) |
| `run.sh` / `run.ps1` | Launch Claude Code via `uv run claudex` (checks `~/.fcc/.env` exists) |

---

## Troubleshooting

| Symptom | Cause / fix |
| ------- | ----------- |
| `fcc-start: command not found` | Aliases not loaded: `source ~/.zshrc`, or use `uv run fcc-start` from the repo |
| `fcc-status` says running but `curl /health` fails | Server still booting (wait a few seconds) or crashed after fork: read `~/.fcc/logs/server.log` |
| `Could not start FCC: [Errno 48] Address already in use` in the log | Another proxy on `PORT`; `fcc-stop`, or change `PORT` in `~/.fcc/.env` |
| Claude Code returns `401` | Token mismatch: `claudex` reads `~/.fcc/.env`, so a stale `ANTHROPIC_AUTH_TOKEN` exported in your shell is not the cause; check the value in the file and restart |
| `API Error: 410 … has reached its end of life` | Provider retired the model. Run `fcc-models`, replace the `MISSING` refs, restart. Known retirements are auto-repaired on start |
| `MODEL … is not available` in the log | Model ref typo or retired model; run `fcc-models`, fix in Admin → Model Config |
| Browser opens on every `fcc-start` | `FCC_OPEN_BROWSER=true` in `~/.fcc/.env`; set it to `false` |
| Logs vanish after restart | Expected with `TRUNCATE_LOG_ON_START=true`; set `false` to keep an audit trail |
| Old repo `.env` edits have no effect | Config moved to `~/.fcc/.env`; edit there or in the Admin UI |

---

## Development checks

```bash
uv sync --all-groups
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest
```

Echelix-specific tests: `tests/cli/test_background.py`,
`tests/config/test_model_deprecations.py`, `tests/config/test_logging_config.py`.

---

## License

Proprietary - Echelix
