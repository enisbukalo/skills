---
name: fastapi
description: >
  FastAPI 2.x patterns and conventions. Covers dependency injection, Annotated params,
  Pydantic request/response models, async vs sync path operations, streaming (JSON Lines,
  SSE, bytes), routers, Asyncer for sync/async bridging, SQLModel, HTTPX, and tooling
  (uv, Ruff, ty). Trigger: writing or reviewing FastAPI APIs, Pydantic models, dependency
  injection, streaming responses, async patterns, perf optimization, or `/fastapi`.
---

# FastAPI 2.x

Self-contained ref. Modern FastAPI idioms. No legacy patterns.

## Before writing code

1. Read `pyproject.toml` first — Python version, FastAPI version, deps, tooling config. Don't ask for what file already says.
2. Clarify only what configs don't answer.
3. Map codebase before adding new endpoints — find existing impls, no duplicate logic.

## Dependency injection

Use deps when:
- Not Pydantic-validatable
- Needs extra logic
- Depends on external resources
- Shared across endpoints (auth, error handling)
- Needs cleanup with `yield`
- Needs request input (headers, query params)

`yield` deps have `scope`. Controls exit code timing.
- Default `"request"` — exit runs after response sent.
- Scope `"function"` — exit runs after response data generated, before sent to client.

```python
from typing import Annotated
from fastapi import Depends, FastAPI

app = FastAPI()

def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

DBDep = Annotated[DBSession, Depends(get_db)]

@app.get("/items/")
async def read_items(db: DBDep):
    return db.query(Item).all()
```

Class deps — avoid. Need class → make function dep that returns instance.

```python
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends, FastAPI

@dataclass
class DatabasePaginator:
    offset: int = 0
    limit: int = 100
    q: str | None = None

    def get_page(self) -> dict:
        return {"offset": self.offset, "limit": self.limit, "q": self.q, "items": []}

def get_db_paginator(offset: int = 0, limit: int = 100, q: str | None = None) -> DatabasePaginator:
    return DatabasePaginator(offset=offset, limit=limit, q=q)

PaginatorDep = Annotated[DatabasePaginator, Depends(get_db_paginator)]

@app.get("/items/")
async def read_items(paginator: PaginatorDep):
    return paginator.get_page()
```

Shared deps at router level via `dependencies=[Depends(...)]`.

## Annotated for everything

Always prefer `Annotated` for params and deps. Keeps signatures usable in other contexts. Respects types. Allows reuse.

Params:
```python
from typing import Annotated
from fastapi import FastAPI, Path, Query

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    return {"message": "Hello World"}
```

Dependencies — make type alias for reuse:
```python
from typing import Annotated
from fastapi import Depends, FastAPI

app = FastAPI()

def get_current_user():
    return {"username": "johndoe"}

CurrentUserDep = Annotated[dict, Depends(get_current_user)]

@app.get("/items/")
async def read_item(current_user: CurrentUserDep):
    return {"message": "Hello World"}
```

No `RootModel`. Use regular type annotations with `Annotated` and Pydantic validation utils. FastAPI creates `TypeAdapter` automatically.

```python
from typing import Annotated
from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()

@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

## No ellipsis for required params

No `...` as default for required params. Not needed. Not recommended.

```python
from typing import Annotated
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)

app = FastAPI()

@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query()]): ...
```

## Return types & response models

Include return type when possible. Validates, filters, documents, serializes response. Pydantic serializes in Rust — main perf win over `ORJSONResponse`/`UJSONResponse` (deprecated).

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None

@app.get("/items/me")
async def get_item() -> Item:
    return Item(name="Plumbus", description="All-purpose home device")
```

Return type filters data. Blocks sensitive info leak. Need not be Pydantic — list, dict, etc. work.

When return type differs from validation/filter type → use `response_model` on decorator:
```python
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel

class InternalItem(BaseModel):
    name: str
    secret_key: str

class Item(BaseModel):
    name: str

@app.get("/items/me", response_model=Item)
async def get_item() -> Any:
    return InternalItem(name="Foo", secret_key="hidden")
```

## Async vs sync path operations

Use `async` only when inner logic is async-compatible (called with `await`) or non-blocking.
In doubt, use `def`. Runs in threadpool. No event loop block. Same rule for deps.
No blocking code in `async def` — kills perf.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/async-items/")
async def read_async_items():
    data = await some_async_library.fetch_items()
    return data

@app.get("/items/")
def read_items():
    data = some_blocking_library.fetch_items()
    return data
```

Mix blocking and async — use Asyncer.

## Streaming

JSON Lines — declare return type, `yield`:
```python
@app.get("/items/stream")
async def stream_items() -> AsyncIterable[Item]:
    for item in items:
        yield item
```

SSE — `response_class=EventSourceResponse`, `yield` items. Plain objects auto JSON-serialized as `data:` fields:
```python
from collections.abc import AsyncIterable
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/items/stream", response_class=EventSourceResponse)
async def stream_items() -> AsyncIterable[Item]:
    yield Item(name="Plumbus", price=32.99)
```

Full SSE field control (`event`, `id`, `retry`, `comment`) — yield `ServerSentEvent`:
```python
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
```

`raw_data` instead of `data` — send pre-formatted strings, no JSON encoding:
```python
yield ServerSentEvent(raw_data="plain text line", event="log")
```

Bytes — declare `response_class=StreamingResponse` or subclass. `yield` data. Prefer over returning response object direct:
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"

@app.get("/image", response_class=PNGStreamingResponse)
def stream_image():
    with read_image() as image_file:
        yield from image_file
```

## Including routers

Put router-level params (prefix, tags) on `APIRouter`, not `include_router()`. Shared deps at router level via `dependencies=[Depends(...)]`.

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/items", tags=["items"])

@router.get("/")
async def list_items():
    return []

app.include_router(router)
```

## One HTTP operation per function

No mix. One func per HTTP op. Separates concerns. Organizes code.

```python
@app.get("/items/")
async def list_items():
    return []

@app.post("/items/")
async def create_item(item: Item):
    return item
```

No `api_route` with multiple methods.

## Tooling

- **uv** for dep management
- **Ruff** for lint and format — enable FastAPI rules
- **ty** for typecheck

## Asyncer — blocking/async bridge

Run blocking code in async or async in blocking. Prefer over AnyIO or asyncio.

```bash
uv add asyncer
```

Blocking sync in async — `asyncify()`:
```python
from asyncer import asyncify

def do_blocking_work(name: str) -> str:
    return f"Hello {name}"

@app.get("/items/")
async def read_items():
    result = await asyncify(do_blocking_work)(name="World")
    return {"message": result}
```

Async in blocking sync — `syncify()`:
```python
from asyncer import syncify

async def do_async_work(name: str) -> str:
    return f"Hello {name}"

@app.get("/items/")
def read_items():
    result = syncify(do_async_work)(name="World")
    return {"message": result}
```

## SQLModel for SQL databases

SQL DB work — prefer SQLModel. Integrated with Pydantic. Same models for validation and ORM. Prefer over raw SQLAlchemy.

## HTTPX for HTTP communication

HTTP calls to other APIs — use HTTPX. Sync and async support. Prefer over Requests.

## CLI

- Dev: `fastapi dev` (localhost, reload)
- Prod: `fastapi run`
- Entrypoint from pyproject.toml preferred: `[tool.fastapi] entrypoint = "my_app.main:app"`
- Fallback: `fastapi dev my_app/main.py`

## Naming

- Modules, packages: snake_case, short, descriptive
- Models, schemas: PascalCase (Pydantic models)
- Functions, methods, variables, parameters: snake_case
- Constants: UPPER_SNAKE_CASE
- Dependencies: `<Type>Dep` pattern — `DBDep`, `CurrentUserDep`
- Routes: kebab-case paths `/items/{item_id}`

## Workflow

1. Read pyproject.toml, FastAPI config — version, deps, tooling
2. Map codebase before writing
3. Design dependency graph before writing endpoints
4. Define Pydantic models for request/response contracts first
5. Implement with `Annotated` params, typed return annotations
6. Route-level prefix/tags on router, not include_router
7. Use async only when inner logic is async-native
8. Write tests with pytest — cover happy path, validation errors, edge cases
9. Run ruff + ty. Address all lint and type errors
10. Review against FastAPI docs conventions

## Output requirements

- FastAPI latest patterns from pyproject.toml version
- `Annotated` for all params (`Path`, `Query`, `Header`) and dependencies — create type aliases for reuse
- No ellipsis (`...`) as default for required params
- Return types on all path operations — Pydantic models filter sensitive data
- No `RootModel`. Use `Annotated[list[T], Field(...)]` with FastAPI's built-in TypeAdapter
- Class deps avoided. Function factory returns instance instead
- Router-level prefix, tags on `APIRouter`. Shared deps via router `dependencies=`
- One HTTP operation per function. No `api_route` with multiple methods
- No `ORJSONResponse`, `UJSONResponse` — deprecated. Pydantic serializes in Rust
- Async only for async-native inner logic. Use `def` in doubt (threadpool)

## Guiding principles

- `Annotated` everywhere — params and deps. Reusable type aliases.
- Return types filter sensitive data. Pydantic Rust serialization is fastest path.
- Async only when async-native. `def` runs in threadpool — safe fallback.
- One HTTP op per function. No mixing methods on single handler.
- Router owns prefix, tags, shared deps. Not `include_router`.
- Map before write — never duplicate existing logic.
- No RootModel. FastAPI handles type annotations natively.

## Boundaries

- No backwards-compatibility shims unless user asks.
- No planning docs unless user asks (skill is reference, not autonomous agent).
