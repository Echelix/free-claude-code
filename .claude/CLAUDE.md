# Claude Code Skills Discovery

This document lists the available skills defined in this project that can be invoked using the `/<skill-name>` syntax or through the Skill tool.

## Available Skills

### 1. `python-api-docs`

**Description**: Generate consistent, professional documentation for Python APIs — including Google-style docstrings, README.md files, and Mermaid/ASCII diagrams for API flows and architecture.

**When to use**:

- Document a Python API, router, service, or endpoint
- Create or update a README for a Python project  
- Generate a flow diagram for an API request lifecycle
- Produce any combination of docstrings + README + diagrams
- When user says "document this", "add docstrings", "write a README", "create a flow diagram", or "explain this API" in Python context

**Invocation**: `/python-api-docs` or use Skill tool with name `python-api-docs`

### 2. `upstream-merge`

**Description**: Merge upstream Alishahryar1/free-claude-code into the Echelix fork while preserving the Echelix layer.

**When to use**:

- Sync upstream: "sync upstream", "pull upstream", "upstream merge", "upstream sync"
- Bring in upstream fixes or features
- Maintain fork alignment with upstream repository

**Invocation**: `/upstream-merge` or use Skill tool with name `upstream-merge`

## How to Invoke Skills

Skills can be invoked in two ways:

1. **Slash Command**: Type `/<skill-name>` in the chat (e.g., `/python-api-docs`)
2. **Skill Tool**: Use the `Skill` tool programmatically:

   ```json
   {
     "skill": "<skill-name>",
     "args": "<optional-arguments>"
   }
   ```

## Skill Location

Skills are defined in the `.claude/skills/` directory:

- `.claude/skills/python-api-docs/`
- `.claude/skills/upstream-merge/`

Each skill directory contains:

- `SKILL.md`: The skill definition and instructions
- `references/`: Reference materials used by the skill

## Adding New Skills

To add a new skill:

1. Create a directory in `.claude/skills/<skill-name>/`
2. Add a `SKILL.md` file with the skill definition
3. Add any reference materials in a `references/` subdirectory
4. The skill will be automatically discoverable

---
*Skills enable specialized workflows and encapsulate expert knowledge for recurring tasks.*
