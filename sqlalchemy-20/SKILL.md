---
name: sqlalchemy-20
description: >
  SQLAlchemy 2.0 cheat sheet. Covers Core (Engine, Connection, Table, select/insert/update/delete,
  types, DDL, transactions, pooling, reflection, events) and ORM (DeclarativeBase, Mapped,
  mapped_column, relationship, Session, loader strategies, inheritance, async, dataclasses,
  hybrid, association proxy, cascades). 2.0-style only — no legacy Query API. Trigger when
  user writes/debugs SQLAlchemy 2.x code, asks about Mapped types, mapped_column, select(),
  Session, async ORM, relationship loading, alembic-adjacent schema work, or "/sqlalchemy".
---

# SQLAlchemy 2.0

Self-contained ref. 2.0 idioms only. Skip legacy `Query`, skip `__init__` mappers, skip implicit autocommit.

## Core mental model

- `Engine` = factory for connections + pool. One per process, module-level.
- `Connection` = single DBAPI conn checked out from pool. Use `with engine.connect()` or `engine.begin()`.
- `MetaData` = registry of `Table` objects. ORM `DeclarativeBase` owns one.
- `Session` = unit-of-work + identity map + transactional scope on top of `Connection`.
- 2.0: same `select()` works for Core and ORM. No more `session.query()`.

## Engine

```python
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg://user:pw@host/db", echo=False, pool_size=5, max_overflow=10, pool_pre_ping=True)
engine = create_engine("sqlite+pysqlite:///:memory:")
engine = create_engine("mysql+pymysql://u:p@h/db")
engine = create_engine("mssql+pyodbc://u:p@dsn")
engine = create_engine("oracle+oracledb://u:p@h:1521/?service_name=svc")
```

URL form: `dialect+driver://user:pass@host:port/db?param=val`. Escape `@` in pw via `urllib.parse.quote_plus`.

Common kwargs: `echo`, `echo_pool`, `pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping`, `pool_timeout`, `connect_args={...}`, `isolation_level="AUTOCOMMIT"|"READ COMMITTED"|...`, `execution_options={...}`.

`NullPool` for serverless/lambda. `StaticPool` for SQLite memory across threads.

## Connection + transactions

```python
with engine.begin() as conn:           # BEGIN ... COMMIT (rollback on exc)
    conn.execute(text("INSERT ..."))

with engine.connect() as conn:         # no auto-tx; use conn.begin()
    with conn.begin():
        conn.execute(...)

# nested savepoints
with conn.begin():
    with conn.begin_nested():          # SAVEPOINT
        ...
```

`text("SELECT :x")` for raw SQL. Bind via `conn.execute(text("..."), {"x": 1})` or list of dicts for executemany.

`conn.execution_options(stream_results=True, yield_per=1000, isolation_level="...", schema_translate_map={...})`.

## Core schema (Table)

```python
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, Index, UniqueConstraint, CheckConstraint

md = MetaData(schema="public", naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})

users = Table(
    "user", md,
    Column("id", Integer, primary_key=True),
    Column("name", String(50), nullable=False),
    Column("email", String(120), unique=True),
    UniqueConstraint("name", "email", name="uq_user_name_email"),
    Index("ix_user_name", "name"),
)

addresses = Table(
    "address", md,
    Column("id", Integer, primary_key=True),
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE")),
    Column("email", String(200)),
)

md.create_all(engine)
md.drop_all(engine)
```

Reflection: `Table("x", md, autoload_with=engine)` or `md.reflect(engine)`.

## Core SQL: select / insert / update / delete

```python
from sqlalchemy import select, insert, update, delete, and_, or_, not_, func, case, literal, bindparam

# SELECT
stmt = select(users.c.id, users.c.name).where(users.c.name == "x").order_by(users.c.id.desc()).limit(10)
stmt = select(users).join(addresses, users.c.id == addresses.c.user_id)
stmt = select(users).join(addresses).where(addresses.c.email.like("%@x.com"))
stmt = select(func.count()).select_from(users)
stmt = select(users).where(users.c.id.in_([1,2,3])).where(users.c.name.is_not(None))

# CTE / subquery
sub = select(addresses.c.user_id).where(addresses.c.email.ilike("%@a%")).subquery()
stmt = select(users).join(sub, users.c.id == sub.c.user_id)
cte = select(users).where(users.c.id < 100).cte("u100")
stmt = select(cte)

# UNION
from sqlalchemy import union, union_all
stmt = union_all(select(users.c.id), select(addresses.c.id))

# INSERT
stmt = insert(users).values(name="x", email="x@y").returning(users.c.id)
conn.execute(insert(users), [{"name":"a"},{"name":"b"}])     # executemany

# upsert (dialect-specific)
from sqlalchemy.dialects.postgresql import insert as pg_insert
ins = pg_insert(users).values(name="x", email="x@y")
ins = ins.on_conflict_do_update(index_elements=["email"], set_={"name": ins.excluded.name})

from sqlalchemy.dialects.sqlite import insert as sqlite_insert  # same shape
from sqlalchemy.dialects.mysql  import insert as mysql_insert   # .on_duplicate_key_update(...)

# UPDATE / DELETE
conn.execute(update(users).where(users.c.id == 1).values(name="z"))
conn.execute(delete(users).where(users.c.id == 1))

# Result API
result = conn.execute(stmt)
result.all()                # list[Row]
result.first()              # Row | None
result.one()                # Row, raises if 0/many
result.scalar()             # first col of first row
result.scalars().all()      # list of first col
result.mappings().all()     # list[dict-like]
for row in result:
    row.id, row.name        # attr access
```

Operators on cols: `==`, `!=`, `<`, `>`, `.in_()`, `.not_in()`, `.like()`, `.ilike()`, `.between(a,b)`, `.is_(None)`, `.is_not(None)`, `.contains()`, `.startswith()`, `.endswith()`, `.regexp_match()`, `+`, `-`, `*`, `/`, `.op("@>")(x)` for custom ops.

`func.now()`, `func.count()`, `func.coalesce(a,b)`, `func.lower(x)`, `func.json_extract(x, "$.a")`. Custom: `func.my_fn(args)`.

## Types

Core types (CamelCase = generic, UPPERCASE = backend-specific):

```
Integer, BigInteger, SmallInteger, Numeric, Float, Boolean,
String(n), Text, Unicode, UnicodeText,
Date, Time, DateTime, Interval, TIMESTAMP,
LargeBinary, JSON, Enum(MyEnum), UUID, ARRAY(Integer),
PickleType
```

Dialect: `postgresql.JSONB`, `postgresql.ARRAY`, `postgresql.HSTORE`, `postgresql.INET`, `mysql.LONGTEXT`, `sqlite.JSON`.

Custom type: subclass `TypeDecorator`, override `impl` + `process_bind_param` + `process_result_value`.

## ORM declarative (2.0 style)

```python
from typing import Optional
from datetime import datetime
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), index=True)
    fullname: Mapped[Optional[str]]                         # nullable from Optional
    created: Mapped[datetime] = mapped_column(server_default=func.now())

    addresses: Mapped[list["Address"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class Address(Base):
    __tablename__ = "address"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    user: Mapped["User"] = relationship(back_populates="addresses")

Base.metadata.create_all(engine)
```

`Mapped[T]` = nullable iff `Optional[T]` / `T | None`. Type → SQL type via internal map (override w/ `type_annotation_map` on Base).

`mapped_column(...)` superset of `Column(...)`: `primary_key`, `nullable`, `unique`, `index`, `default`, `server_default`, `onupdate`, `server_onupdate`, `autoincrement`, `comment`, `info`, `deferred`, `init`, `repr`, `kw_only` (dataclass).

## Session

```python
from sqlalchemy.orm import Session, sessionmaker

Session_ = sessionmaker(engine, expire_on_commit=False)

with Session(engine) as session:
    u = User(name="bob", fullname="Bob B")
    session.add(u)
    session.add_all([u1, u2])
    session.flush()                 # emit SQL, no commit
    session.commit()                # flush + COMMIT
    session.rollback()
    session.refresh(u)              # SELECT to repopulate
    session.expire(u)               # mark stale, lazy reload on next access
    session.merge(u)                # copy state into managed instance
    session.delete(u)               # mark for DELETE on flush
    obj = session.get(User, 1)      # PK lookup, identity-map cached
```

Tx: `with session.begin():` or rely on autobegin (default). Nested: `with session.begin_nested():` → SAVEPOINT.

`expire_on_commit=False` if you need attrs after commit without re-SELECT.

## ORM select / DML

```python
from sqlalchemy import select, update, delete

# rows of entities
users = session.scalars(select(User).where(User.name == "x")).all()
user  = session.scalars(select(User).where(User.id == 1)).one()
user  = session.scalar(select(User).where(User.id == 1))    # one_or_none semantics

# columns / mixed
rows = session.execute(select(User.id, User.name)).all()        # list[Row]
rows = session.execute(select(User, Address).join(User.addresses)).all()

# DML — synchronize_session: 'auto'|'evaluate'|'fetch'|False
session.execute(update(User).where(User.id == 1).values(name="z"))
session.execute(delete(User).where(User.id == 1))

# bulk INSERT (RETURNING-aware in 2.0)
session.execute(insert(User), [{"name":"a"},{"name":"b"}])
session.scalars(insert(User).returning(User), [{"name":"a"}]).all()
```

## Relationship loading

```python
from sqlalchemy.orm import selectinload, joinedload, subqueryload, lazyload, raiseload, contains_eager, defer, undefer, load_only, with_loader_criteria

# default: lazy='select' (lazy load on attr access — N+1 risk)
relationship("Address", lazy="select")    # 'select'|'joined'|'subquery'|'selectin'|'raise'|'noload'|'dynamic'|'write_only'

# per-query override
select(User).options(selectinload(User.addresses))               # best for collections
select(User).options(joinedload(User.parent))                    # best for many-to-one
select(User).options(joinedload(User.addresses).selectinload(Address.tags))   # nested

# manual join + populate
stmt = select(User).join(User.addresses).options(contains_eager(User.addresses))

# column loading
select(User).options(load_only(User.name), defer(User.bio))
select(User).options(undefer(User.bio))
```

Rule of thumb: **`selectinload` for collections, `joinedload` for scalars (many-to-one)**. `joinedload` on collections multiplies rows.

`lazy="dynamic"` → returns Query (legacy). 2.0 prefers `lazy="write_only"` → `WriteOnlyCollection` (no implicit load, supports `.select()`, `.insert()`, `.update()`, `.delete()`).

## Relationship patterns

```python
# one-to-many (FK on child)
class Parent(Base):
    children: Mapped[list["Child"]] = relationship(back_populates="parent")
class Child(Base):
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent.id"))
    parent: Mapped["Parent"] = relationship(back_populates="children")

# many-to-one — same as above from the Child side

# one-to-one — uselist=False on the collection side
children: Mapped["Child"] = relationship(back_populates="parent", uselist=False)

# many-to-many via association Table
from sqlalchemy import Table, Column
post_tag = Table("post_tag", Base.metadata,
    Column("post_id", ForeignKey("post.id"), primary_key=True),
    Column("tag_id",  ForeignKey("tag.id"),  primary_key=True),
)
class Post(Base):
    tags: Mapped[list["Tag"]] = relationship(secondary=post_tag, back_populates="posts")

# self-referential (adjacency list)
class Node(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("node.id"))
    children: Mapped[list["Node"]] = relationship(back_populates="parent", remote_side=...)
    parent: Mapped[Optional["Node"]] = relationship(back_populates="children", remote_side=[id])
```

`relationship()` keys: `back_populates`, `cascade` (`save-update`, `merge`, `delete`, `delete-orphan`, `all`), `passive_deletes=True` (let DB cascade), `single_parent=True`, `order_by=`, `primaryjoin=`, `secondary=`, `secondaryjoin=`, `foreign_keys=`, `viewonly=True`, `lazy=`, `innerjoin=True`, `overlaps=`.

## Cascades

`"all, delete-orphan"` = save-update + merge + refresh-expire + expunge + delete + delete-orphan. Default = `"save-update, merge"`. Use `passive_deletes=True` + DB-level `ON DELETE CASCADE` for big collections.

## Inheritance

```python
class Employee(Base):
    __tablename__ = "employee"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]
    __mapper_args__ = {"polymorphic_on": "type", "polymorphic_identity": "employee"}

class Manager(Employee):                          # joined-table
    __tablename__ = "manager"
    id: Mapped[int] = mapped_column(ForeignKey("employee.id"), primary_key=True)
    title: Mapped[str]
    __mapper_args__ = {"polymorphic_identity": "manager"}

# single-table: no __tablename__, no FK id, just polymorphic_identity
# concrete: concrete=True in __mapper_args__, separate tables, no shared SELECT

# query polymorphically
from sqlalchemy.orm import with_polymorphic
emp = with_polymorphic(Employee, [Manager])
session.scalars(select(emp))
```

## Hybrid / computed / association proxy

```python
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy

class User(Base):
    first: Mapped[str]
    last: Mapped[str]

    @hybrid_property
    def full(self):                      # Python
        return f"{self.first} {self.last}"

    @full.expression
    def full(cls):                       # SQL
        return func.concat(cls.first, " ", cls.last)

    keywords: Mapped[list["Kw"]] = relationship()
    keyword_names = association_proxy("keywords", "name")
```

## Async (asyncio)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://u:p@h/db")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async with async_session() as session:
    res = await session.scalars(select(User).where(User.id == 1))
    user = res.one()
    user.name = "z"
    await session.commit()

# concurrent statements: use SEPARATE sessions (Session not concurrency-safe)
import asyncio
async def fetch(uid):
    async with async_session() as s:
        return await s.scalar(select(User).where(User.id == uid))
results = await asyncio.gather(*[fetch(i) for i in ids])

# eager-load lazy attrs in async (lazy='select' will FAIL outside greenlet ctx)
await session.scalars(select(User).options(selectinload(User.addresses)))
# or use AsyncAttrs:
from sqlalchemy.ext.asyncio import AsyncAttrs
class Base(AsyncAttrs, DeclarativeBase): ...
addrs = await user.awaitable_attrs.addresses
```

Drivers: `asyncpg` (pg), `aiosqlite`, `aiomysql`/`asyncmy`, `aioodbc`. No async pool sharing across event loops.

## Dataclass mapping

```python
from sqlalchemy.orm import MappedAsDataclass

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "u"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str]
    fullname: Mapped[Optional[str]] = mapped_column(default=None)
```

Per-column dataclass kwargs on `mapped_column`: `init`, `default`, `default_factory`, `repr`, `compare`, `kw_only`.

## Events (most useful)

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, conn_record):
    cur = dbapi_conn.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

@event.listens_for(User, "before_insert")
def before_insert(mapper, conn, target):
    target.created = datetime.utcnow()

@event.listens_for(Session, "before_flush")
def before_flush(session, ctx, instances): ...

# attribute change tracking
@event.listens_for(User.name, "set")
def on_set(target, value, oldvalue, initiator): ...
```

## Exceptions

`from sqlalchemy.exc import ...`
`SQLAlchemyError` (root), `IntegrityError`, `OperationalError`, `DataError`, `ProgrammingError`, `InvalidRequestError`, `NoResultFound`, `MultipleResultsFound`, `StatementError`, `DBAPIError`, `DisconnectionError`, `TimeoutError`, `ArgumentError`.

## Performance pitfalls

- N+1: missing `selectinload`/`joinedload`. Fix with `.options(selectinload(...))`.
- `joinedload` on collection → cartesian blow-up. Use `selectinload`.
- Big inserts: use bulk `session.execute(insert(X), [dicts])` not loop of `add()`.
- Reads-only path: `session.execute(select(...).execution_options(yield_per=1000))` or `Session(autoflush=False)`.
- `expire_on_commit=False` if attrs accessed after commit.
- Use `passive_deletes=True` + DB `ON DELETE CASCADE` for big delete cascades.
- Connection leak: always `with engine.connect()`/`engine.begin()`. Never store conn at module scope.
- `pool_pre_ping=True` to survive stale DB conns through firewalls/restarts.
- Prepared-stmt caching: enabled by default; `create_engine(..., query_cache_size=1200)` to tune.

## URL examples (drivers)

```
postgresql+psycopg://      (psycopg 3, sync+async)
postgresql+asyncpg://      (async)
postgresql+psycopg2://     (psycopg 2, sync)
mysql+pymysql://
mysql+asyncmy://
mariadb+pymysql://
sqlite:///path/db.sqlite        (relative)
sqlite:////abs/path.sqlite      (absolute, 4 slashes)
sqlite+aiosqlite:///:memory:
mssql+pyodbc://u:p@dsn?driver=ODBC+Driver+18+for+SQL+Server
oracle+oracledb://u:p@h/?service_name=svc
```

## Common recipes

```python
# count
n = session.scalar(select(func.count()).select_from(User))
n = session.scalar(select(func.count(User.id)).where(User.active))

# exists
exists_q = select(User.id).where(User.email == "x").exists()
present = session.scalar(select(exists_q))

# pagination
rows = session.scalars(select(User).order_by(User.id).limit(20).offset(40)).all()

# JSON (pg)
from sqlalchemy.dialects.postgresql import JSONB
data: Mapped[dict] = mapped_column(JSONB)
session.scalars(select(Doc).where(Doc.data["k"].astext == "v"))

# raw SQL fallback
from sqlalchemy import text
rows = session.execute(text("SELECT id FROM u WHERE name=:n"), {"n":"x"}).all()

# server-side cursor (large result)
with engine.connect().execution_options(stream_results=True) as conn:
    for row in conn.execute(stmt).yield_per(500):
        ...

# schema-translate (multi-tenant by schema)
conn = engine.connect().execution_options(schema_translate_map={None: "tenant_42"})
```

## What 2.0 dropped vs 1.x

- `session.query(...)` → use `session.execute(select(...))` / `session.scalars(...)`.
- `Query.filter()` chaining → `select().where()`.
- Implicit autocommit on `engine.execute()` → gone. Use `engine.connect()`/`engine.begin()`.
- `Column` for ORM attrs → `mapped_column` (still works but loses `Mapped[]` typing benefits).
- `relationship("X", lazy="dynamic")` → prefer `lazy="write_only"` for new code.
- Bare string column refs in `relationship(..., order_by="X.id")` still work but typed `order_by=X.id` preferred.
- `from sqlalchemy.ext.declarative import declarative_base` → `DeclarativeBase` subclass.

## Style guide for agents writing SA 2.0

1. Always type-annotate with `Mapped[T]` + `mapped_column(...)`. No bare `Column` on ORM classes.
2. Use `select()` everywhere. Never `session.query()` in new code.
3. `session.scalars(stmt).one()|.all()|.first()` for entity returns. `session.execute(stmt).all()` for tuple rows.
4. Always pick a loader strategy when relationships are accessed: `selectinload` (coll) / `joinedload` (scalar). Never rely on lazy in async.
5. Sessions: `with Session(engine) as s:` or DI a `sessionmaker`. Don't share sessions across threads/tasks.
6. Engine: module-level singleton. Session: short-lived per unit of work / per request.
7. Use `back_populates`, not `backref`, for clarity and typing.
8. Prefer `passive_deletes=True` + DB FK cascade over ORM `delete-orphan` for big trees.
9. Use `text()` for raw SQL with bound params — never f-string interpolate user input into SQL.
10. Run migrations with Alembic (not `create_all` in prod). `create_all` = dev/test only.
