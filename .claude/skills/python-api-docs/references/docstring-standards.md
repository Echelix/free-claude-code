# Google-Style Docstring Standards for Python APIs

## Section Reference

### First Line (Summary)
**Required** for all public members. One sentence, present tense, active voice. End with a period.

| ✅ Good | ❌ Bad |
| ---- | ---- |
| `Validate the request payload and return a normalized command.` | `This function validates the request payload and returns a normalized command.` |
| `Represent a paginated list of items with cursor metadata.` | `A class for paginated lists.` |
| `Raise DuplicateProjectError when a duplicate project name is detected within a tenant.` | `Exception class for duplicate projects.` |

**Patterns by member type:**
- **Function/method**: starts with a verb (`Retrieve`, `Create`, `Validate`, `Raise`, `Map`, `Parse`)
- **Property**: describes what it represents (`The UTC timestamp when the record was last modified.`)
- **Class**: describes what the type *is* or *does* (`Orchestrate the project creation workflow, including validation and event dispatch.`)
- **Module**: describes the module's responsibility (`FastAPI router for project management endpoints.`)
- **Exception**: describes when it is raised (`Raised when a project name already exists within the same tenant.`)

---

### `Args:`
**Required** for every parameter. Lowercase start, no period. Describe semantic meaning; do not restate the type (it is in the signature).

```python
def get_projects(
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
    cancellation_token: asyncio.Event | None = None,
) -> PagedResult[ProjectDto]:
    """...

    Args:
        tenant_id: Tenant scope used to isolate query results.
        page: 1-based page index.
        page_size: Maximum number of records per page (1–100); defaults to 20.
        include_deleted: True to include soft-deleted records; False to exclude them.
        cancellation_token: Optional event; when set, the operation aborts early.
    """
```

Special cases:
- Boolean flags → describe both states: `"True to include soft-deleted records; False to exclude them."`
- Optional params → note the default: `"Maximum number of results per page; defaults to 20."`
- `*args` / `**kwargs` → describe what the variadic args represent, not just `"Additional arguments."`

---

### `Returns:`
**Required** for all non-`None` functions. Describe what the value *means*, not just its type.

```python
# ✅ Good
"""
Returns:
    The newly assigned record UUID, or None if creation was deferred.
"""

# ❌ Bad
"""
Returns:
    UUID.
"""
"""
Returns:
    The result.
"""
```

For `async` functions, document the unwrapped value (same as synchronous equivalent):
```python
# async def get_projects(...) -> list[ProjectDto]
"""
Returns:
    All active projects visible to the caller's tenant, ordered by creation date descending.
"""
```

For FastAPI endpoints returning `Response` / `JSONResponse`, describe the HTTP semantics:
```python
"""
Returns:
    201 Created with the project ID and resource URI on success.
    409 Conflict if a project with the same name exists in the tenant.
    422 Unprocessable Entity if validation fails.
"""
```

---

### `Raises:`
**Required** for all explicitly raised exceptions and semantically important propagated ones.

```python
"""
Raises:
    ValueError: If page_size is outside the range 1–100.
    DuplicateProjectError: If a project with the same name already exists
        in the tenant.
    asyncio.CancelledError: If the operation is cancelled before completion.
"""
```

Use the exception class name, not the module path (`ValueError` not `builtins.ValueError`).
For `HTTPException`, note the status code: `HTTPException: 404 if the project does not exist.`

---

### `Yields:`
**Required** for generator functions. Describe each yielded value.

```python
def stream_projects(tenant_id: uuid.UUID) -> Generator[ProjectDto, None, None]:
    """Stream all projects for a tenant without loading them all into memory.

    Yields:
        Each active project for the tenant, ordered by creation date ascending.
    """
```

---

### `Example:`
Use for non-obvious usage patterns:

```python
"""
Example:
    Register the service with a custom retry policy::

        service = ProjectService(
            repo=ProjectRepository(session),
            retry_count=3,
            retry_delay=2.0,
        )
        project_id = await service.create_project(command)
"""
```

Note the double colon `::` before indented code blocks (reStructuredText convention honored by most doc renderers including Sphinx and mkdocstrings).

---

### `Note:` and `Warning:`
Use sparingly — only when the behavior would surprise a reader:

```python
"""
Note:
    This method is not thread-safe. Do not call concurrently with update_project()
    on the same tenant.

Warning:
    Calling this with a session that has pending uncommitted changes may cause
    unexpected constraint violations.
"""
```

---

## Patterns for Common Python Constructs

### FastAPI Router Endpoint
```python
@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    service: Annotated[ProjectService, Depends(get_project_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    """Retrieve a single project by its ID.

    Only returns projects visible to the authenticated user's tenant.

    Args:
        project_id: UUID of the project to retrieve.
        service: Injected project service.
        current_user: Authenticated user extracted from the bearer token.

    Returns:
        The full project details including metadata and member count.

    Raises:
        HTTPException: 404 if the project does not exist or is not visible to
            the caller's tenant.
        HTTPException: 401 if the bearer token is missing or invalid.
    """
```

### Pydantic Model
```python
class CreateProjectRequest(BaseModel):
    """Request payload for creating a new project.

    Attributes:
        name: Display name for the project; must be unique within the tenant.
        description: Optional human-readable description (max 500 characters).
        tags: Optional list of tag strings for filtering and discovery.
    """

    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
```

Note: use `Attributes:` (not `Args:`) for class-level field documentation in Pydantic models and dataclasses.

### SQLAlchemy / Repository Method
```python
async def find_by_tenant(
    self,
    tenant_id: uuid.UUID,
    *,
    include_deleted: bool = False,
    session: AsyncSession,
) -> list[Project]:
    """Retrieve all projects belonging to a tenant.

    Args:
        tenant_id: Tenant scope used to filter results.
        include_deleted: True to include soft-deleted records; defaults to False.
        session: Active async database session.

    Returns:
        All matching projects ordered by created_at descending, or an empty
        list if none exist.
    """
```

### Dependency / Factory Function
```python
async def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> ProjectService:
    """Construct and yield a ProjectService with injected infrastructure.

    Args:
        session: Active async database session from the request context.
        event_bus: Event bus for publishing domain events.

    Yields:
        A fully configured ProjectService instance scoped to the current request.
    """
```

### Exception Class
```python
class DuplicateProjectError(ValueError):
    """Raised when a project name already exists within the same tenant.

    Attributes:
        tenant_id: The tenant in which the duplicate was detected.
        name: The conflicting project name.
    """

    def __init__(self, tenant_id: uuid.UUID, name: str) -> None:
        """Initialize with the conflicting tenant and project name.

        Args:
            tenant_id: Tenant in which the duplicate was detected.
            name: The conflicting project name.
        """
        self.tenant_id = tenant_id
        self.name = name
        super().__init__(f"Project '{name}' already exists in tenant {tenant_id}.")
```

### Context Manager / Lifespan
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    Initializes the database connection pool and event bus on startup,
    then flushes pending events and closes connections on shutdown.

    Yields:
        Nothing; control returns to FastAPI during the application's lifetime.
    """
```

---

## Anti-Patterns to Avoid

| Anti-pattern | Example | Fix |
| ---- | ---- | ---- |
| Restating the type | `Args: name (str): The name string.` | `Args: name: Display name for the project.` |
| Vague summary | `Handle the request.` | `Validate the authorization header and extract the caller's tenant claims.` |
| Empty sections | `Returns:\n    ` | Remove the section or fill it in |
| Obvious parameter docs | `Args: id: The id.` | `Args: id: UUID of the project to retrieve.` |
| "This function/method" opener | `This function creates a project.` | `Create a new project within the tenant workspace.` |
| Missing `Raises:` for `HTTPException` | _(no `Raises:` despite `raise HTTPException(404)`)_ | Always document raised HTTP exceptions with their status code |
| Docstring on private members | `def _build_query(...):` | Skip docstrings on private/internal helpers unless the logic is non-obvious |
