# Diagram Patterns for Python API Documentation

## Diagram Type Decision Guide

```
What are you documenting?
│
├── HTTP request lifecycle (middleware → router → service → DB)
│   └── sequenceDiagram
│
├── Auth flow (JWT validation, OAuth2, Entra ID)
│   └── sequenceDiagram
│
├── Service dependency graph (what depends on what)
│   └── graph TD (top-down)
│
├── Decision/routing logic (branching behavior)
│   └── flowchart TD
│
├── Event-driven / message bus / Celery task flows
│   └── sequenceDiagram
│
└── Simple overview for README (minimal tooling)
    └── ASCII box diagram
```

---

## Pattern 1: Standard HTTP Request Lifecycle

Use this for any router endpoint — customize participants for your actual stack.

```mermaid
sequenceDiagram
    actor Client
    participant APIM as Azure APIM
    participant MW as Middleware<br/>(Auth + Logging + CORS)
    participant R as ProjectsRouter
    participant S as ProjectService
    participant Repo as ProjectRepository
    participant DB as PostgreSQL

    Client->>APIM: POST /api/projects<br/>Authorization: Bearer {token}
    APIM->>APIM: Rate limit check
    APIM->>MW: Forward request
    MW->>MW: JWT validation<br/>scope: projects:write
    MW->>R: Request + user claims

    R->>R: Pydantic model validation
    alt Validation fails
        R-->>Client: 422 Unprocessable Entity<br/>ValidationError detail
    end

    R->>S: create_project(command)
    S->>S: Business rule validation
    alt Duplicate name
        S-->>R: DuplicateProjectError
        R-->>Client: 409 Conflict
    end

    S->>Repo: insert(entity)
    Repo->>DB: INSERT INTO projects
    DB-->>Repo: project_id
    Repo-->>S: Project entity
    S-->>R: CreateProjectResponse
    R-->>Client: 201 Created<br/>Location: /api/projects/{id}
```

---

## Pattern 2: JWT / Entra ID Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Client App
    participant EntraID as Azure AD / Entra ID
    participant APIM as Azure APIM
    participant API as Python API

    User->>App: Initiates login
    App->>EntraID: Authorization Code Request<br/>scope: api://{{app-id}}/projects:read
    EntraID->>User: Login prompt
    User->>EntraID: Credentials
    EntraID-->>App: Authorization code
    App->>EntraID: Token exchange (code + PKCE)
    EntraID-->>App: Access token (JWT)

    App->>APIM: GET /api/projects<br/>Authorization: Bearer {jwt}
    APIM->>EntraID: Validate token (JWKS endpoint)
    EntraID-->>APIM: Token valid + claims
    APIM->>API: Forward + X-Claims header
    API->>API: Extract tenant from claims
    API-->>App: 200 OK + projects
```

---

## Pattern 3: FastAPI Dependency Injection Flow

```mermaid
sequenceDiagram
    participant R as Router
    participant D as Depends()<br/>Resolvers
    participant Auth as get_current_user
    participant DB as get_db_session
    participant Svc as get_project_service
    participant S as ProjectService

    R->>D: Resolve dependencies
    D->>Auth: Validate bearer token
    Auth-->>D: User claims
    D->>DB: Open AsyncSession
    DB-->>D: session
    D->>Svc: ProjectService(session, bus)
    Svc-->>D: service instance
    D->>R: Inject (user, service)
    R->>S: create_project(command)
    S-->>R: CreateProjectResponse
    Note over DB: Session closed<br/>after response
```

---

## Pattern 4: Celery / Background Task Flow

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant RMQ as Redis / RabbitMQ
    participant W as Celery Worker
    participant H as Task Handler
    participant S as ProjectService
    participant DB as Database
    participant DLQ as Dead Letter Queue

    API->>RMQ: enqueue(process_project_task, project_id)
    API-->>Client: 202 Accepted + task_id

    RMQ->>W: Message received
    W->>H: process_project_task(project_id)
    H->>H: Deserialize + validate

    alt Deserialization fails
        H->>DLQ: Move to DLQ (poison message)
        H-->>RMQ: Acknowledge (discard)
    end

    H->>S: handle_event(event)
    S->>DB: Update record

    alt Transient error
        DB-->>S: OperationalError
        S-->>H: Raise (retry eligible)
        Note over RMQ,H: Celery retries (max_retries=10)<br/>with exponential backoff
    end

    DB-->>S: OK
    S-->>H: Complete
    H-->>RMQ: Acknowledge message
```

---

## Pattern 5: Service Dependency Graph

Use `graph TD` for showing architecture layers and dependencies.

```mermaid
graph TD
    API[ProjectsRouter<br/>FastAPI]
    SVC[ProjectService<br/>Application Layer]
    REPO[ProjectRepository<br/>SQLAlchemy]
    CACHE[CacheService<br/>Redis]
    BUS[EventBus<br/>Azure Service Bus]
    DB[(PostgreSQL)]
    BLOB[(Azure Blob Storage)]

    API --> SVC
    SVC --> REPO
    SVC --> CACHE
    SVC --> BUS
    REPO --> DB
    REPO --> BLOB

    style API fill:#0078d4,color:#fff
    style SVC fill:#004e8c,color:#fff
    style REPO fill:#005a9e,color:#fff
    style DB fill:#50e6ff,color:#000
    style BLOB fill:#50e6ff,color:#000
```

---

## Pattern 6: Strangler Fig Migration (for modernization projects)

```mermaid
graph TD
    LB[Load Balancer / APIM]

    subgraph Legacy["Legacy System (Django / DRF)"]
        LC[Legacy View]
        LS[Legacy Service]
        LDB[(Legacy DB)]
    end

    subgraph Modern["New System (FastAPI)"]
        NC[FastAPI Router]
        NS[New Service]
        NDB[(New DB)]
    end

    LB -->|/legacy-path| LC
    LB -->|/api/v2/*| NC
    LC --> LS --> LDB
    NC --> NS --> NDB

    style Legacy fill:#ffd700,color:#000
    style Modern fill:#0078d4,color:#fff
```

---

## Pattern 7: ASCII Box Diagram (no Mermaid renderer)

Use when the target platform may not render Mermaid (plain GitHub wikis, Confluence basic mode, etc.).

```
┌─────────────────────────────────────────────────────────┐
│                     Client (React SPA)                  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS + Bearer JWT
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Azure APIM                           │
│          (Rate limiting, auth validation)               │
└────────────────────────┬────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
┌───────────────────┐     ┌────────────────────────────┐
│  Projects API     │     │  Documents API             │
│  (FastAPI)        │     │  (FastAPI)                 │
└─────────┬─────────┘     └─────────────┬──────────────┘
          │                             │
          ▼                             ▼
┌───────────────────┐     ┌────────────────────────────┐
│   PostgreSQL      │     │   Azure Blob Storage       │
│   (Projects DB)   │     │   (Document Store)         │
└───────────────────┘     └────────────────────────────┘
```

---

## Mermaid Naming and Styling Conventions

### Participant naming

```mermaid
sequenceDiagram
    %% Actors (humans / external systems)
    actor User
    actor ExternalService as External CRM

    %% Internal services — use actual module/class name
    participant R as ProjectsRouter
    participant S as ProjectService

    %% Infrastructure — descriptive label with technology
    participant DB as PostgreSQL
    participant CACHE as Redis Cache
    participant BUS as Service Bus
    participant BLOB as Azure Blob

    %% External identity providers
    participant AAD as Azure AD / Entra ID
```

### Notes and annotations
```mermaid
sequenceDiagram
    participant A as ServiceA
    participant B as ServiceB

    %% Single-participant note
    Note over A: Retries up to 3x with<br/>exponential backoff

    %% Cross-participant note
    Note over A,B: async — no blocking wait

    %% Error path annotation
    A->>B: risky call
    alt Error
        B-->>A: 500 error
        Note over A: Log + publish<br/>FailureEvent
    end
```

### Arrow types

| Arrow | Meaning | When to use |
| ---- | ---- | ---- |
| `->>` | Solid arrow | Synchronous call / request |
| `-->>` | Dashed arrow | Response / async return |
| `-x` | Solid with X | Fire-and-forget / no response |
| `-->` | Open dashed | Return value (non-critical) |

### Color coding in graph diagrams (Azure palette)
```
Azure Blue (primary):     fill:#0078d4,color:#fff
Dark Azure:               fill:#004e8c,color:#fff
Azure Cyan (data):        fill:#50e6ff,color:#000
Legacy / Warning:         fill:#ffd700,color:#000
Error / Deprecated:       fill:#d13438,color:#fff
Success / New:            fill:#107c10,color:#fff
```

---

## Diagram Quality Checklist

Before including a diagram in documentation:

- [ ] All participant names match actual class/module names in the codebase
- [ ] Happy path is shown completely end-to-end
- [ ] At least one error/failure path is shown
- [ ] Auth/token flow is visible (don't hide it "behind" the API box)
- [ ] No placeholder text (`{{}}`) left in participant labels
- [ ] Mermaid syntax validated (no unclosed brackets, correct arrow syntax)
- [ ] Diagram is scoped — one flow per diagram, not everything at once
- [ ] Notes used sparingly — only for non-obvious behavior
