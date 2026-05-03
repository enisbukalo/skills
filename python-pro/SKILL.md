---
name: python-pro
description: >
  Modern Python 3.12+ patterns. Covers PEP 695 type params, type statement, f-strings (PEP 701),
  @override (PEP 698), TypedDict + Unpack (PEP 692), comprehension inlining, itertools.batched,
  typing.Protocol/TypeIs/ReadOnly, pytest patterns (fixtures, parametrize, monkeypatch), asyncio
  (TaskGroup, Queue, Semaphore), perf optimization (slots, functools.cache, comprehensions),
  pythonic idioms (pathlib, walrus, match, dataclass, Enum). Trigger: writing or reviewing Python,
  type hints, pytest, async, perf, or `/python`.
---

# Python Pro

Self-contained ref. Modern Python 3.12+ idioms. Skip legacy patterns.

## Before writing code

1. Read `pyproject.toml` first — Python version, deps, build system, lint/typecheck tools. Don't ask for what file already says.
2. Clarify only what pyproject.toml does not answer.
3. Map codebase before adding new code via code-index MCP — no duplicate logic.

## Python 3.12+ features

- **PEP 695**: Type parameter syntax — `def func[T](...)` instead of `TypeVar` boilerplate
- `type` statement for type aliases — `type Point = tuple[float, float]`
- Generic type aliases — `type Point[T] = tuple[T, T]`
- **PEP 701**: f-strings lift restrictions — nested quotes, multiline expressions, backslashes
- **PEP 698**: `@override` decorator for method overrides
- **PEP 692**: `TypedDict` + `Unpack` for `**kwargs` typing
- **PEP 709**: Comprehension inlining — faster list/dict/set comprehensions
- `itertools.batched()` for chunking iterables
- `math.sumprod()` for sum of products
- `copy.replace()` protocol for immutable object modification
- `pathlib.Path.walk()` for directory tree traversal

```python
type Vector[T: (int, float)] = list[T]

def process[T](items: list[T]) -> list[T]:
    return list(reversed(items))
```

## Type hints & static analysis

- PEP 484 type hints on all public functions, methods, class attributes
- `typing.Protocol` for structural subtyping over inheritance
- `TypeVar`, `ParamSpec`, `TypeVarTuple` for generic code (or PEP 695 `[T]` syntax)
- PEP 695 `[T]` syntax preferred over standalone `TypeVar` declarations
- `type` statement over `TypeAlias` assignment for type aliases
- `TypedDict` for dict schemas with known keys
- `@override` on all overridden methods — catches typos, signature drift
- `typing.TypeIs` (3.13+) for type narrowing without full guard semantics
- `typing.ReadOnly` (3.13+) for read-only TypedDict items
- PEP 702 `warnings.deprecated()` decorator for deprecations
- Run mypy strict mode. No `# type: ignore` unless documented why.

```python
from typing import Protocol, override

class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    @override
    def draw(self) -> None:
        print("circle")
```

## Testing — pytest

- pytest over unittest. Fixtures, parametrize, markers, plugins.
- Plain `assert`, not `self.assertEqual`.
- Fixtures for shared setup/teardown. Use `yield` for teardown.
- `@pytest.mark.parametrize` for data-driven tests.
- `monkeypatch` fixture for env vars, attrs, sys.modules patches.
- `conftest.py` for shared fixtures. Scope: function default, class/module/session explicit.
- Test functions and classes prefixed `test_`. Files named `test_<module>.py`.
- Tests mirror source tree under `tests/`.
- Factory pattern or data builders over mocks for domain objects. Reserve mocks for external I/O.
- `pytest-asyncio` for async test support. Mark coroutines with `@pytest.mark.asyncio`.
- Coverage target: 80%+ lines, 90%+ branches on core logic.

```python
import pytest

@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.close()

@pytest.mark.parametrize("input,expected", [(1, 2), (3, 4)])
def test_increment(input, expected):
    assert increment(input) == expected
```

## Async patterns — asyncio

- `asyncio.run()` as entry point. No nested event loops.
- `await` over `asyncio.gather()` for sequential deps. `gather()` for independent coroutines.
- `async with` for resource management (connections, locks, contexts).
- `asyncio.TaskGroup` (3.11+) for structured concurrency — replaces manual task tracking.
- `asyncio.Queue` for producer-consumer patterns. Set maxsize to bound memory.
- `asyncio.Semaphore` to limit concurrent operations.
- Avoid `asyncio.sleep()` in production code — use proper event signaling.
- Prefer `aiohttp`, `asyncpg`, other async-native libs over sync wrappers with executor.
- `concurrent.futures.ProcessPoolExecutor` for CPU-bound work, not I/O-bound.

```python
import asyncio

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fetch("a"))
        tg.create_task(fetch("b"))

asyncio.run(main())
```

## Performance optimization

- List/dict/set comprehensions over loops. Generator expressions for lazy evaluation.
- `itertools.batched()`, `chain.from_iterable()`, `map()` over manual iteration.
- `str.join()` with generator for string concatenation, never `+=` in loop.
- `collections.namedtuple`, `dataclasses.dataclass`, `typing.NamedTuple` over raw dicts for structured data.
- `__slots__` on classes instantiated millions of times — saves per-instance dict overhead.
- `functools.cache` (3.9+, replaces `lru_cache(maxsize=None)`) for pure function memoization.
- `functools.lru_cache(maxsize=N)` when cache bounded.
- `functools.partial` over lambda for currying.
- `operator.itemgetter`, `attrgetter`, `methodcaller` over lambdas in sort/map.
- `collections.Counter`, `defaultdict`, `deque` for specialized ops — faster than dict/list equivalents.
- Avoid global lookups: bind to local var (`append = list.append`) in tight loops.
- Profile before optimize: `cProfile`, `py-spy`, or `sys.monitoring` (3.12+).

```python
from functools import cache
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

@cache
def fib(n: int) -> int:
    return n if n < 2 else fib(n-1) + fib(n-2)
```

## Pythonic patterns

- PEP 8 style. `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants.
- Context managers (`with`) for all resources — files, locks, connections.
- `pathlib.Path` over `os.path`. Use `.read_text()`, `.write_text()`, `.glob()`.
- Walrus operator `:=` to combine test + assignment: `if (match := pattern.search(text)):`
- Match statement (3.10+) for complex conditional branching, type dispatching.
- Dataclasses with `frozen=True` for immutable data structures.
- `Enum` over string/int constants for fixed sets of values.
- Avoid deep inheritance — prefer composition or Protocol-based duck typing.

```python
match command.split():
    case ["go", direction]:
        move(direction)
    case ["look"]:
        describe()
    case _:
        print("unknown")
```

## Workflow

1. Read pyproject.toml — version, deps, tooling config
2. Map codebase with code-index MCP
3. Design interfaces before writing impl
4. Type annotate all public APIs first
5. Implement with Pythonic patterns, comprehensions, context managers
6. Write pytest tests for all new public functions and non-trivial logic. Cover happy path, boundary conditions, error paths.
7. Run mypy strict. Address all type errors.
8. Profile if perf concern identified. Optimize data structures, algorithms, not micro-syntax.
9. Review against PEP 8, PEP 20 (Zen of Python). Document intentional deviations.

## Output requirements

- Python 3.12+ syntax and features from pyproject.toml version
- PEP 8 compliant. Line length 88 (black default) or match project config.
- Type hints on all public functions, methods, class attributes. Return types explicit — no implicit `None`.
- Docstrings on all public APIs: Google or Sphinx style, match project convention.
- f-strings over `%` formatting or `.format()`. Use `=` specifier for debug: `f"{x=}"`.
- No bare `except:`. Catch specific exceptions.
- Context managers for resource handling.
- Comprehensions/generators preferred over manual loops where idiomatic.
- Test files mirror source tree under `tests/`. Named `test_<module>.py`.
- pytest fixtures in conftest.py when shared across modules.

## Naming

- Modules, packages: `snake_case`, short, descriptive
- Classes: `PascalCase`
- Functions, methods, variables, parameters: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: single underscore prefix `_internal`
- Dunder `__method__` only for Python protocol implementation, not custom naming
- Files: `snake_case`

## Guiding principles

- Readability counts. Code is read more often than written (PEP 20).
- Explicit over implicit. Type hints document intent at call site.
- Comprehensions and generators express iteration intent clearly.
- Static type checking catches errors before runtime — mypy strict mode default.
- Profile before optimize. Premature optimization root of all evil.
- Map before write — always use code-index MCP before writing anything new.

## Boundaries

- No backwards-compatibility shims unless user asks.
- No planning docs unless user asks (skill is reference, not autonomous agent).
