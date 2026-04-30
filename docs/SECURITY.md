# Security Assessment: free-claude-code

> Deep-dive audit performed April 27, 2026.  
> Scope: data egress, secret handling, proxy security, logging, and attack surface.

---

## Table of Contents

1. [Where Your Data Goes](#where-your-data-goes)
2. [Findings by Severity](#findings-by-severity)
   - [HIGH — Unrestricted Subprocess Execution in Bot Mode](#high--unrestricted-subprocess-execution-in-bot-mode)
   - [MEDIUM — Weak Public-Default Auth Token](#medium--weak-public-default-auth-token)
   - [MEDIUM — Proxy Binds to All Interfaces](#medium--proxy-binds-to-all-interfaces)
   - [LOW — Log File Truncated on Restart](#low--log-file-truncated-on-restart)
   - [LOW — Web Fetch User-Agent Identifies the Proxy](#low--web-fetch-user-agent-identifies-the-proxy)
3. [What Was Audited and Found Clean](#what-was-audited-and-found-clean)
4. [Recommended Actions](#recommended-actions)
5. [Raw Notes by Subsystem](#raw-notes-by-subsystem)

---

## Where Your Data Goes

When running the proxy in its default configuration (NVIDIA NIM provider, no bot, no web tools), your conversation content flows to exactly **one external destination**:

| Destination | What is sent | Condition |
|---|---|---|
| `https://integrate.api.nvidia.com` | Your full prompt + conversation history | Every LLM request |
| `server.log` (local disk) | Metadata only (counts, IDs, model names) by default | Every request |
| `https://lite.duckduckgo.com` | Search query text | Only if `ENABLE_WEB_SERVER_TOOLS=true` AND Claude triggers `web_search` |
| Target URL host | Fetched page content (stays local, returned to Claude) | Only if `ENABLE_WEB_SERVER_TOOLS=true` AND Claude triggers `web_fetch` |
| Telegram API / Discord gateway | Message text and Claude responses | Only if bot is configured and running |
| HuggingFace (model download) | Nothing sensitive — model weights download only | Only on first run with local Whisper voice |

There is **no telemetry, analytics pipeline, beacon, or third-party tracking** anywhere in the codebase. Zero calls to Sentry, Segment, Mixpanel, Amplitude, Datadog, PostHog, or similar services were found.

---

## Findings by Severity

### HIGH — Unrestricted Subprocess Execution in Bot Mode

**File:** `cli/session.py` lines 136 and 147  
**Status:** Not exploitable in default (proxy-only) setup. Active risk if bot is enabled.

When the Discord or Telegram messaging bot is running, every Claude CLI subprocess is launched with:

```python
"--dangerously-skip-permissions"
```

This flag disables all Claude Code permission prompts — Claude will read files, write files, run shell commands, and execute code **without asking for confirmation**. Combined with the fact that:

- Discord bots can be reached by anyone in an allowed channel
- Channel access controls are only a comma-separated ID list (`ALLOWED_DISCORD_CHANNELS`) with no cryptographic authentication
- Telegram bots use a single `ALLOWED_TELEGRAM_USER_ID` which is just a numeric string comparison

…this means anyone who can send a message to the bot effectively has unrestricted code execution on the machine running the proxy.

**Mitigation:** Do not run the bot unless you fully control who can reach those channels. Treat bot access as equivalent to SSH access to your machine.

---

### MEDIUM — Weak Public-Default Auth Token

**File:** `.env` line 16, `api/dependencies.py` lines 89–122  
**Status:** Active risk if proxy is reachable beyond localhost.

The value `freecc` is the project's publicly documented default `ANTHROPIC_AUTH_TOKEN`, listed in the README and visible on GitHub. Anyone who knows this project can authenticate to your proxy and consume your NVIDIA NIM quota.

The auth mechanism itself is correctly implemented — it checks `x-api-key`, `Authorization: Bearer`, and `anthropic-auth-token` headers, strips model-name suffixes (e.g. `freecc:model/name`), and returns 401 for missing or mismatched tokens. The weakness is purely in using a guessable default.

**Mitigation:** Change `ANTHROPIC_AUTH_TOKEN` in `.env` to a long random secret (32+ chars). The `.env` value always overrides any shell environment variable (`prefer_dotenv_anthropic_auth_token` validator).

---

### MEDIUM — Proxy Binds to All Interfaces

**File:** `config/settings.py` (`host` default), launch command  
**Status:** Active risk on any machine connected to a LAN or VPN.

The default run command (`--host 0.0.0.0`) binds the proxy to all network interfaces. Combined with the weak default token above, anyone on the same LAN or VPN can reach your proxy and use your NIM API key without ever learning the key value itself.

**Mitigation (preferred):** Bind to loopback only:

```powershell
uv run uvicorn server:app --host 127.0.0.1 --port 8082
```

This single change eliminates both the interface-exposure and weak-token risks simultaneously, since the proxy becomes unreachable from outside your machine.

---

### LOW — Log File Truncated on Restart (No Audit Trail)

**File:** `config/logging_config.py`

On every startup, the log file is wiped:

```python
Path(log_file).write_text("")
```

This is intentional for clean debugging but means there is no persistent audit trail. If a request results in a downstream incident (e.g. NIM quota exhaustion, unexpected charges), past log context is gone after the next restart.

**Mitigation:** If you need retention, redirect or copy logs before restart, or replace the truncation with log rotation (e.g. `logger.add(..., rotation="10 MB", retention="7 days")`).

---

### LOW — Web Fetch Identifies the Proxy to Target Servers

**File:** `api/web_tools/constants.py`

When `ENABLE_WEB_SERVER_TOOLS=true`, all outbound web requests carry:

```
User-Agent: Mozilla/5.0 compatible; free-claude-code/2.0
```

This is not a security vulnerability per se, but target servers can identify and block, log, or profile requests from this proxy.

---

## What Was Audited and Found Clean

| Subsystem | Finding |
|---|---|
| Outbound HTTP (provider calls) | Only goes to the configured provider (NIM, OpenRouter, etc.). No secondary destinations. |
| Secret/token logging | API keys are never logged. Bearer tokens in log lines are redacted by regex in `logging_config.py`. Telegram bot tokens are also redacted. |
| Payload logging | Request body, SSE stream, and CLI output are NOT logged by default. All raw-content logging requires explicit opt-in flags. |
| SSRF protection (web fetch) | `api/web_tools/egress.py` blocks localhost, RFC-1918, link-local, and `.local` hostnames. Uses DNS-pinning (`_PinnedEgressStaticResolver`) to prevent DNS rebind attacks. |
| Web search destination | Hardcoded to `https://lite.duckduckgo.com/lite/` — no configurable or user-injectable URL. |
| Provider API key handling | `NVIDIA_NIM_API_KEY` is read at startup, held in memory, sent only to NIM. Never written to logs or returned in API responses. |
| Request validation | Pydantic models validate all incoming Claude Code requests. Validation errors log only field names and error types — not field values. |
| Auth bypass | Auth check applies to all routes including `/`, `/v1/messages`, `/v1/messages/count_tokens`, and probes. No unauthenticated backdoor routes found. |
| Third-party telemetry | None found. No Sentry, Segment, Datadog, Amplitude, Mixpanel, PostHog, or similar. |
| Subprocess injection | CLI session builds the command as a list (`asyncio.create_subprocess_exec`), not a shell string. Shell injection via `prompt` text is not possible. |

---

## Recommended Actions

Listed in priority order for a local single-user setup:

### 1. Bind to loopback (eliminates LAN exposure)

```powershell
# In your launch command
uv run uvicorn server:app --host 127.0.0.1 --port 8082
```

### 2. Change the auth token if you keep `0.0.0.0`

Generate a random token and set it in `.env`:

```dotenv
ANTHROPIC_AUTH_TOKEN=<your-long-random-secret-here>
```

Use the same value when launching Claude Code:

```powershell
$env:ANTHROPIC_AUTH_TOKEN="<your-long-random-secret-here>"
$env:ANTHROPIC_BASE_URL="http://localhost:8082"
claude
```

### 3. Do not enable the bot unless you treat it as SSH access

If you enable Discord/Telegram integration, anyone who can message the bot gets unrestricted shell and file access on your machine via `--dangerously-skip-permissions`.

### 4. Leave raw logging flags off (default)

Do not set these unless actively debugging and only for short periods:

```dotenv
LOG_RAW_API_PAYLOADS=false   # full request bodies (default: false)
LOG_RAW_SSE_EVENTS=false     # full streaming content (default: false)
LOG_RAW_MESSAGING_CONTENT=false  # chat message text (default: false)
LOG_RAW_CLI_DIAGNOSTICS=false    # Claude CLI stderr (default: false)
```

### 5. Leave web server tools disabled (default)

```dotenv
ENABLE_WEB_SERVER_TOOLS=false  # default
```

Only enable if you need Claude to browse the web. When enabled, Claude can initiate outbound HTTP to arbitrary URLs on your behalf (SSRF-guarded but still outbound).

---

## Raw Notes by Subsystem

### Proxy Auth (`api/dependencies.py`)

- `require_api_key` is a FastAPI dependency applied to every route
- Accepts token in `x-api-key`, `Authorization: Bearer <token>`, or `anthropic-auth-token` header
- Strips `:model/suffix` from tokens (supports `freecc:provider/model` format)
- When `ANTHROPIC_AUTH_TOKEN` is empty string, auth is completely disabled (open proxy)
- `.env` value always wins over shell env via `prefer_dotenv_anthropic_auth_token` model validator

### Logging (`config/logging_config.py`)

- All logs written as JSON lines to `server.log`
- Telegram bot token URLs are regex-redacted before writing
- `Authorization: Bearer <token>` patterns are regex-redacted
- Log file is **truncated to zero on each startup** — no persistent history
- Sensitive content only logged when explicit debug flags are set

### Outbound HTTP

- Provider calls: via `openai.AsyncOpenAI` (NIM), `anthropic.AsyncAnthropic` (OpenRouter/DeepSeek/LM Studio/Ollama)
- Web search: `httpx.AsyncClient` → `https://lite.duckduckgo.com/lite/`
- Web fetch: `aiohttp.ClientSession` with pinned DNS resolver (SSRF mitigation)
- No proxy, CDN, or relay in the path — direct connection to provider endpoint

### CLI Subprocess (`cli/session.py`)

- Prompt text passed as a command-line argument (`-p <prompt>`) to `claude` binary
- `asyncio.create_subprocess_exec` used (not shell=True) — no shell injection
- `ANTHROPIC_API_KEY` is injected as `sk-placeholder-key-for-proxy` when absent — this is a dummy value, not a real key
- `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_URL` are set to the local proxy URL
- `--dangerously-skip-permissions` is always passed in bot mode (see HIGH finding)
- stderr is drained and capped at 256 KB to prevent memory exhaustion

### Voice Transcription (`messaging/transcription.py`, `messaging/voice.py`)

- Local Whisper (cpu/cuda): model weights downloaded from HuggingFace on first use; audio processed entirely on-device, nothing sent externally
- NVIDIA NIM Whisper: audio file sent to NIM endpoint using same `NVIDIA_NIM_API_KEY`
- Audio files are read from disk by path; size capped at 25 MB
