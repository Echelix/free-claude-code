# README.md Template for Python API Projects

Copy this template and fill in all `{{PLACEHOLDER}}` values. Remove sections that don't apply, but never remove the section headers — replace with "N/A" or "Coming soon" instead so readers know the section was considered.

---

```markdown
# {{PROJECT_NAME}}

> {{ONE_LINE_DESCRIPTION}} — e.g., "REST API for managing research compliance workflows across IRB, IACUC, and IBC modules."

![Build Status](https://img.shields.io/github/actions/workflow/status/{{ORG}}/{{REPO}}/ci.yml?branch=main)
![Python](https://img.shields.io/badge/python-{{PYTHON_VERSION}}+-blue)
![License](https://img.shields.io/badge/license-{{LICENSE}}-blue)

---

## Overview

{{2–4 sentences covering: what the API does, who the primary consumers are, and what makes it notable.}}

**Key capabilities:**
- {{CAPABILITY_1}}
- {{CAPABILITY_2}}
- {{CAPABILITY_3}}

---

## Prerequisites

| Requirement | Version |
| ---- | ---- |
| Python | {{PYTHON_VERSION}} or later |
| {{DATABASE}} | {{DB_VERSION}} |
| {{OTHER_DEPENDENCY}} | {{VERSION}} |

> **Azure deployments**: Requires Managed Identity with `{{ROLE}}` on `{{RESOURCE}}`.

---

## Getting Started

### 1. Clone and configure

```bash
git clone https://github.com/{{ORG}}/{{REPO}}.git
cd {{REPO}}
cp .env.example .env
```

Update `.env` with your local values (see [Configuration](#configuration)).

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

> **Using uv**: `uv sync --all-extras`  
> **Using Poetry**: `poetry install`

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn {{PACKAGE}}.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## Configuration

### `.env` structure

```bash
# Database
DATABASE_URL=postgresql+asyncpg://your-user:your-password@localhost:5432/your-db

# Authentication
AUTH_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
AUTH_AUDIENCE=api://your-app-id

# {{FEATURE}}
{{KEY}}=your-value-here
```

### Environment variables

| Variable | Description | Required |
| ---- | ---- | ---- |
| `DATABASE_URL` | Async-compatible database connection string | ✅ |
| `AUTH_AUTHORITY` | OIDC authority URL | ✅ |
| `AUTH_AUDIENCE` | Expected audience claim in the JWT | ✅ |
| `{{ENV_VAR}}` | {{DESCRIPTION}} | {{YES/NO}} |

All settings are validated at startup via Pydantic `BaseSettings`. A missing required variable raises a `ValidationError` before the app binds to any port.

### Azure App Configuration

If using Azure App Config, set `AZURE_APP_CONFIG_ENDPOINT` to your endpoint URI. Managed Identity must have `App Configuration Data Reader` role.

---

## API Reference

### Authentication

{{DESCRIBE_AUTH_PATTERN}}

**Example:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

Required scopes:
- `{{SCOPE_1}}` — {{DESCRIPTION}}
- `{{SCOPE_2}}` — {{DESCRIPTION}}

---

### Endpoints

#### {{RESOURCE_GROUP_NAME}} — `/api/{{base-path}}`

| Method | Path | Auth | Description |
| ---- | ---- | ---- | ---- |
| `GET` | `/api/{{resource}}` | Bearer | {{DESCRIPTION}} |
| `GET` | `/api/{{resource}}/{id}` | Bearer | {{DESCRIPTION}} |
| `POST` | `/api/{{resource}}` | Bearer + `{{scope}}` | {{DESCRIPTION}} |
| `PUT` | `/api/{{resource}}/{id}` | Bearer + `{{scope}}` | {{DESCRIPTION}} |
| `DELETE` | `/api/{{resource}}/{id}` | Bearer + `{{scope}}` | {{DESCRIPTION}} |

#### {{RESOURCE_GROUP_2}} — `/api/{{base-path-2}}`

| Method | Path | Auth | Description |
| ---- | ---- | ---- | ---- |
| `GET` | `/api/{{resource2}}` | Bearer | {{DESCRIPTION}} |

---

### Request / Response Examples

#### `POST /api/{{resource}}`

**Request:**
```json
{
  "{{field1}}": "{{example_value}}",
  "{{field2}}": 42
}
```

**Response `201 Created`:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "{{field1}}": "{{example_value}}",
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### Error Responses

All errors follow [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457):

```json
{
  "type": "https://{{domain}}/errors/{{error-type}}",
  "title": "{{Human-readable title}}",
  "status": 400,
  "detail": "{{Specific explanation}}",
  "instance": "/api/{{resource}}/{{id}}"
}
```

| Status | When |
| ---- | ---- |
| `400 Bad Request` | Validation failure or malformed request |
| `401 Unauthorized` | Missing or invalid bearer token |
| `403 Forbidden` | Valid token but insufficient scope |
| `404 Not Found` | Resource does not exist or not visible to caller |
| `409 Conflict` | Duplicate or state conflict |
| `422 Unprocessable Entity` | Business rule violation |
| `500 Internal Server Error` | Unexpected server error |

---

## Architecture

### High-Level Flow

```mermaid
sequenceDiagram
    actor Client
    participant GW as API Gateway / APIM
    participant API as {{PROJECT_NAME}} API
    participant Auth as Azure AD / Entra ID
    participant DB as {{DATABASE}}

    Client->>GW: HTTPS Request
    GW->>Auth: Validate JWT
    Auth-->>GW: Claims
    GW->>API: Forward + Claims
    API->>DB: Query / Mutation
    DB-->>API: Result
    API-->>Client: Response
```

> **Full diagrams**: See [`docs/diagrams/`](docs/diagrams/) for detailed flow diagrams per module.

### Project Structure

```
src/
└── {{PACKAGE}}/
    ├── main.py              # FastAPI app factory, middleware, router registration
    ├── config.py            # Pydantic BaseSettings — all env vars in one place
    ├── routers/             # FastAPI APIRouter modules, one per resource
    ├── services/            # Business logic — no framework dependencies
    ├── repositories/        # Data access — SQLAlchemy, external APIs
    ├── models/              # SQLAlchemy ORM models
    ├── schemas/             # Pydantic request/response schemas
    └── dependencies/        # FastAPI Depends() factories
tests/
├── unit/                    # Pure logic — services, domain rules
├── integration/             # DB, external services
└── e2e/                     # Full HTTP tests via TestClient / httpx
```

---

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# With coverage
pytest --cov={{PACKAGE}} --cov-report=term-missing
```

### Lint and format

```bash
ruff check .
ruff format .
mypy src/
```

### Add a migration

```bash
alembic revision --autogenerate -m "{{description}}"
alembic upgrade head
```

### Code style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [mypy](https://mypy-lang.org/) for static type checking. Run `ruff format . && ruff check .` before committing.

---

## Contributing

1. Branch from `main` using `feature/{{description}}` or `fix/{{description}}`
2. Follow the [coding standards](docs/coding-standards.md)
3. Ensure all tests pass: `pytest`
4. Open a PR with a description linking to the relevant issue

---

## License

{{LICENSE}} — see [LICENSE](LICENSE) for details.
```

---

## README Writing Rules

### Voice and tense
- Present tense throughout: "The API **validates**..." not "The API **will validate**..."
- Second person for instructions: "**Run** the migrations" not "The developer should run..."
- Imperative for commands: "**Clone** the repository"

### Code blocks
Always specify the language:
- ` ```bash ` for shell commands
- ` ```python ` for Python snippets
- ` ```json ` for JSON payloads
- ` ```http ` for raw HTTP examples
- ` ```mermaid ` for inline diagrams

Never use ` ```shell ` or ` ```sh ` — use ` ```bash `.

### Credential safety
- All connection strings: `"your-connection-string-here"`
- All tenant IDs: `"your-tenant-id"`
- All secrets/keys: `"your-secret-here"`
- JWT examples: use a clearly truncated token like `eyJ0eXAiOiJKV1QiLC...`

### Endpoint tables
Use this exact column order: `Method | Path | Auth | Description`
- Method: backtick-wrapped: `` `GET` ``
- Path: backtick-wrapped: `` `/api/projects/{id}` ``
- Auth: `Bearer`, `API Key`, `None`, or `Bearer + scope:write`
- Description: brief, present tense, lowercase start

### Version references
- Python version: always `Python 3.12` not `py312` or `python3.12`
- Package versions: include major version in prerequisites table
- FastAPI: note FastAPI version and Pydantic version (e.g., `FastAPI 0.115 / Pydantic v2`)
