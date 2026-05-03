---
name: rust-pro
description: >
  Rust programming patterns and conventions from std library docs. Covers ownership, borrowing, lifetimes,
  traits, smart pointers (Box, Rc, Arc), Option/Result, iterators, error handling, collections, async
  (Future, Pin, async/await), concurrency (thread, Mutex, channels), I/O (fs, io, net), strings, macros,
  proc_macro, unsafe patterns, no_std, tooling (cargo, clippy, rustfmt, miri). Trigger: writing or
  reviewing Rust code, `/rust`, Rust std library questions.
---

# Rust Pro

Self-contained ref from `core`, `alloc`, `std`, `proc_macro`, `test` crate docs. Modern idioms only.

## Crate hierarchy

- **core** — dependency-free foundation. No heap, no libc, no I/O. Primitives, traits, iterators, Option/Result, sync primitives, future/pin, cell, convert, cmp, hash, mem, ptr, slice, str, time, panic, ffi, fmt, num, marker, prelude, error.
- **alloc** — heap allocation on top of core. Box, Rc, Arc, Vec, String, collections. Used in `#![no_std]` crates without std.
- **std** — full standard library. Re-exports core + alloc. Adds I/O (io, fs, net), threading (thread, sync with Mutex/RWLock/channels mpsc/mpmc), env, process, path, backtrace.
- **proc_macro** — macro author support. TokenStream, Ident, Literal, Punct, Span, Group. For `#[proc_macro]`, `#[proc_macro_attribute]`, `#[proc_macro_derive]`.
- **test** — nightly-only test/benchmark framework. Bencher, black_box, #[test], #[bench].

## Ownership & borrowing

Core Rust model. No GC, no reference counting by default.

Rules:
- One owner per value. Value dropped when owner goes out of scope.
- `&T` — shared borrow. Multiple allowed. Immutable access only.
- `&mut T` — mutable borrow. Only one at a time. Exclusive access.
- Borrow cannot outlive owned data. Compiler enforces via lifetimes.

```rust
let s1 = String::from("hello");
let r1 = &s1;    // OK: shared borrow
// let r2 = &mut s1; // ERROR: mutable borrow while shared exists
let r3 = &s1;    // OK: another shared borrow
drop(r1); drop(r3);
let r4 = &mut s1; // OK: mutable borrow after shared borrows dropped
```

Move semantics — value transfers ownership. Original binding invalidated.
Types that implement `Copy` (primitives, tuples of Copy types) copy instead of move.

## Core types

### Option<T>

Represents optional values. No null. Pattern match or combinators.

```rust
let x: Option<i32> = Some(4);
match x {
    Some(v) => println!("{v}"),
    None => println!("empty"),
};
// Combinators
x.unwrap_or(0);
x.map(|v| v * 2);
x.and_then(|v| if v > 0 { Some(v) } else { None });
```

### Result<T, E>

Error handling type. Never use panic for control flow.

```rust
let x: Result<i32, String> = Ok(4);
match x {
    Ok(v) => println!("{v}"),
    Err(e) => eprintln!("error: {e}"),
};
// Combinators
x.unwrap_or_default();
x.map_err(|e| format!("wrapped: {e}"));
x.and_then(|v| if v > 0 { Ok(v) } else { Err("bad") });
```

`?` operator — propagate errors. Returns early with `Err`, unwraps `Ok`.

```rust
fn read() -> Result<String, std::io::Error> {
    let mut f = std::fs::File::open("data.txt")?;
    let mut contents = String::new();
    f.read_to_string(&mut contents)?;
    Ok(contents)
}
```

## Traits

Traits define shared behavior. Like interfaces with implementation.

### Prelude traits (auto-imported)

`Clone`, `Copy`, `Default`, `Drop`, `Into`, `From`, `TryInto`, `TryFrom`, `AsRef`, `AsMut`, `PartialEq`, `PartialOrd`, `Eq`, `Ord`, `Hash`, `Sized`, `Send`, `Sync`, `Unpin`.

### Key traits

```rust
// Clone — explicit copy
impl Clone for MyType {
    fn clone(&self) -> Self { /* ... */ }
}

// Default — zero-value construction
impl Default for Config {
    fn default() -> Self { Config { timeout: 30, retries: 3 } }
}

// Drop — cleanup on scope exit
impl Drop for FileHandle {
    fn drop(&mut self) { unsafe { libc::close(self.fd); } }
}

// From/Into — infallible conversion. Implement From<T>, get Into<U> free.
impl From<u32> for MyInt {
    fn from(n: u32) -> Self { MyInt { n } }
}
let x: MyInt = 42u32.into();

// TryFrom/TryInto — fallible conversion, returns Result
impl TryFrom<&str> for Age {
    type Error = ParseError;
    fn try_from(s: &str) -> Result<Self, Self::Error> { /* ... */ }
}

// AsRef/AsMut — zero-cost reference conversion
fn len<T: AsRef<str>>(s: T) -> usize { s.as_ref().len() }

// PartialEq + Eq — equality. Eq requires reflexivity (no NaN).
impl PartialEq for Point {
    fn eq(&self, other: &Self) -> bool { self.x == other.x && self.y == other.y }
}

// PartialOrd + Ord — ordering. Ord requires totality (no NaN).
impl PartialOrd for Point {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> { /* ... */ }
}

// Hash — hashing for HashMap/HashSet
use std::hash::{Hash, Hasher};
impl Hash for Point {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.x.hash(state);
        self.y.hash(state);
    }
}

// Iterator — composable external iteration
struct Counter { count: u32 }
impl Iterator for Counter {
    type Item = u32;
    fn next(&mut self) -> Option<Self::Item> {
        if self.count < 5 { self.count += 1; Some(self.count) } else { None }
    }
}

// Deref — implicit reference coercion (smart pointers)
use std::ops::Deref;
impl Deref for MyBox<T> { type Target = T; fn deref(&self) -> &T { &self.inner } }

// Drop, Index, IndexMut — operator overloading via std::ops module
```

### Marker traits (no impl needed, compiler assigns)

- `Sized` — type has known size at compile time. All types except DSTs.
- `Send` — safe to transfer ownership across threads. Automatic for types without interior mutability or raw pointers.
- `Sync` — safe to share references across threads (`&T` is Send). Automatic for types with thread-safe interior mutability (Mutex, Atomic*).
- `Unpin` — value can move in memory after being pinned. Most types are Unpin.

Use `impl<T: Send + Sync>` bounds when generics need cross-thread safety.

## Lifetimes

Lifetimes tie references to scopes. Compiler verifies borrows don't outlive data.

```rust
// Explicit lifetimes — elision rules often cover this
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

// Lifetime elision — one input → output gets that lifetime; multiple inputs with &self → self's lifetime
fn first_word(s: &str) -> &str { /* ... */ } // &str → &str, elided

// Struct lifetimes
struct Quote<'a> { text: &'a str }

// Static lifetime — lives for program duration
static GREETING: &str = "hello"; // &'static str

// 'static in traits — trait objects with static lifetime
fn takes_static(s: &'static str) { /* ... */ }
```

Lifetime rules:
- Every reference has a lifetime.
- Function signatures with references may need explicit lifetimes when compiler can't infer.
- Structs holding references always need lifetime annotations.
- `&'static T` — data lives entire program. String literals, static vars.

## Iterators

Lazy, composable, zero-cost abstraction over loops. Defined in `core::iter`.

```rust
// Chain combinators
let sum: i32 = (1..=100).filter(|&x| x % 3 == 0).map(|x| x * 2).sum();

// Adapter chain — no allocation until collected
let words: Vec<&str> = "hello world foo".split_whitespace().collect();

// Key adapters
iter.map(f)      // transform each item
iter.filter(p)   // keep items where predicate true
iter.flat_map(f) // transform + flatten one level
iter.enumerate() // (index, item) pairs
iter.zip(other)  // pair with another iterator
iter.take(n)     // first n items
iter.skip(n)     // drop first n items
iter.chain(iter2)// concatenate iterators
iter.peekable()  // peek at next without consuming

// Consuming adapters — materialize results
.iter().collect::<Vec<T>>()
.iter().count()
.iter().sum() / .product()
.iter().min() / .max()
.iter().reduce(f)      // fold with first element as initial
iter.fold(init, f)     // reduce with explicit initial value
iter.any(p) / iter.all(p)  // short-circuit predicates
iter.find(p)           // first matching item
iter.position(p)       // index of first match

// IntoIterator — for loops use this. Vec<T> → &T (borrow), Vec<T> moved → T (consume)
for x in &vec { /* borrows */ }
for x in vec { /* consumes, vec moved */ }
```

## Error handling patterns

No exceptions. `Result` + `?` for recoverable errors. `panic!` for unrecoverable bugs only.

```rust
// Custom error type with thiserror-like derive pattern
#[derive(Debug)]
enum AppError {
    Io(std::io::Error),
    Parse(ParseError),
    NotFound(String),
}
impl std::fmt::Display for AppError { fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { /* ... */ } }
impl From<std::io::Error> for AppError { fn from(e: std::io::Error) -> Self { AppError::Io(e) } }

// Box<dyn Error> for error type erasure in public APIs
fn run() -> Result<(), Box<dyn std::error::Error>> { /* ... */ }

// thiserror crate — derive Error, Display, From automatically
```

## Collections

### Vec<T> — growable heap array

```rust
let mut v = Vec::new();          // empty vec
let v2 = vec![1, 2, 3];         // macro, infers capacity
v.push(4);                      // append
v.pop();                        // remove last, returns Option<T>
v.len();                        // current length
v.capacity();                   // allocated space
v.reserve(100);                 // pre-allocate
let slice: &[i32] = &v[1..3];  // borrow as slice
```

### String / &str — UTF-8 text

`String` — owned, growable. `&str` — borrowed slice, UTF-8 guaranteed.

```rust
let s = String::from("hello");    // from literal
let s2 = format!("{} {}", s, "world");  // formatted string
let slice: &str = &s;             // borrow as str slice
s.push_str(&s2);                  // append
s.chars().count();                // grapheme count (not byte len)
s.len();                          // byte length
s.is_empty();                     // check empty

// Str methods — available on both String and &str via Deref
"hello".trim();                   // strip whitespace
"hello,world".split(',');         // split iterator
"a.b.c".replace('.', "-");       // replace all
"123".parse::<i32>();            // FromStr trait → Result<i32, _>
```

### HashMap<K, V> / HashSet<T>

```rust
use std::collections::{HashMap, HashSet};
let mut map = HashMap::new();
map.insert("key", 42);
*map.entry("key").or_insert(0) += 1;  // upsert pattern
map.get("key");                       // Option<&V>
map.remove("key");                    // removes and returns Option<V>

let set = HashSet::from([1, 2, 3]);
set.contains(&2);
set.union(&other_set);
```

### Other collections (std::collections)

- `BTreeMap` / `BTreeSet` — sorted by key. No Hash required, Ord only. Predictable iteration order.
- `BinaryHeap<T>` — max-heap priority queue.
- `LinkedList<T>` — doubly-linked list. Rarely needed; Vec usually faster.
- `VecDeque<T>` — double-ended queue. O(1) push/pop both ends.
- `hash_map::Entry` / `btree_map::Entry` — upsert API, avoid double lookup.

## Smart pointers & interior mutability

### Box<T> — single-owner heap allocation

```rust
let b = Box::new(42);        // heap allocated, stack pointer
let recursive: Box<Node> = Box::new(Node { next: None });  // infinite types require Box
```

Use when: type size unknown at compile time (recursive), transferring ownership without copying, trait objects (`Box<dyn Trait>`).

### Rc<T> — single-threaded reference counting

```rust
use std::rc::Rc;
let a = Rc::new(42);
let b = Rc::clone(&a);       // increment count, not deep copy
Rc::strong_count(&a);        // how many references exist
```

Pair with `RefCell<T>` for interior mutability:

### RefCell<T> — runtime borrow checking

```rust
use std::cell::RefCell;
let cell = RefCell::new(vec![1, 2]);
{
    let mut guard = cell.borrow_mut(); // panics if already borrowed
    guard.push(3);
} // borrow released here
let read = cell.borrow();       // panics if mutable borrow active
```

`Rc<RefCell<T>>` — shared ownership + mutation, single-threaded. Common in ASTs, graphs.

### Arc<T> — thread-safe reference counting

```rust
use std::sync::Arc;
let a = Arc::new(42);
let b = Arc::clone(&a);       // atomic ref count increment
// Send + Sync safe. Use across threads with Mutex/RwLock for mutation.
```

### Cell<T> — copy-only interior mutability

```rust
use std::cell::Cell;
let c = Cell::new(0);
c.set(42);       // only works for Copy types
let v = c.get();
```

No borrowing rules. Only T: Copy. Zero overhead. Use for simple counters, flags.

## Async programming

`async fn` returns `impl Future`. Requires async runtime (tokio, async-std).

### Future trait — lazy computation

```rust
use std::future::Future;
async fn fetch(url: &str) -> String { /* ... */ }
let fut = fetch("https://example.com"); // created, not running yet
let result = fut.await;                 // polls until ready, suspends thread
```

Futures are lazy. Nothing runs until `.await` or `poll()`. No executor → future does nothing.

### Pin — memory pinning for self-referential structs

```rust
use std::pin::Pin;
// Futures can hold references to their own state. Must not move in memory.
fn spawn<F: Future + Send + 'static>(fut: F) { /* executor takes ownership, pins internally */ }
let pinned = Box::pin(fetch("url")); // Pin<Box<Future>>
```

`Pin<T>` prevents unsafe memory moves. Used with async, generators, self-referential types. Most code doesn't interact directly — runtime handles it.

### Async patterns

```rust
// Parallel execution with futures::join! or tokio::join!
let (a, b) = tokio::join!(fetch("url1"), fetch("url2"));

// Sequential with error propagation
async fn pipeline() -> Result<(), Error> {
    let data = fetch_data().await?;
    process(data).await?;
    Ok(())
}

// async/await in struct methods — return impl Future, not blocking
impl Client {
    async fn get(&self, url: &str) -> Response { /* ... */ }
}
```

## Concurrency

### Threads (std::thread)

```rust
use std::thread;
let handle = thread::spawn(|| {
    // Closure must be Send + 'static — owns all captured data
    "work done"
});
let result = handle.join().unwrap();  // blocks until thread finishes
```

`Send` — type can transfer across threads. `Sync` — type's reference can share across threads. Compiler enforces automatically; opt out with `unsafe impl`.

### Mutex<T> / RwLock<T> — shared mutable state

```rust
use std::sync::{Arc, Mutex};
let data = Arc::new(Mutex::new(0));
{
    let mut guard = data.lock().unwrap(); // PoisonError on panic
    *guard += 1;
} // unlock

// RwLock — multiple readers OR one writer
use std::sync::RwLock;
let lock = RwLock::new(5);
{ let r1 = lock.read().unwrap(); }     // shared read
{ let mut w = lock.write().unwrap(); *w += 1; } // exclusive write
```

### Channels — message passing (std::sync::mpsc)

```rust
use std::sync::mpsc;
let (tx, rx) = mpsc::channel();
thread::spawn(move || { tx.send("hello").unwrap(); });
let msg = rx.recv().unwrap();          // blocks until message arrives
// mpsc — multi-producer, single-consumer. Clone tx for multiple senders.
```

For async, use `tokio::sync::mpsc` or `async_std::channel`.

## I/O (std::io)

Trait-based. `Read`, `Write`, `Seek`, `BufRead`.

```rust
use std::io::{self, Read, Write};
// File operations
use std::fs;
let contents = fs::read_to_string("file.txt")?;
fs::write("out.txt", "data")?;
fs::create_dir_all("path/to/dir")?;

// Stream I/O
use std::io::{BufReader, BufWriter};
let file = fs::File::open("in.txt")?;
let mut reader = BufReader::new(file);   // buffered reads
let mut line = String::new();
reader.read_line(&mut line)?;            // read until newline

// Stdin/stdout/stderr
io::stdout().write_all(b"hello\n")?;
```

## Filesystem (std::fs, std::path)

```rust
use std::path::{Path, PathBuf};
let p = Path::new("dir/file.txt");
p.parent();       // Some(Path: "dir")
p.file_name();    // Some(OsStr: "file.txt")
p.extension();    // Some(OsStr: "txt")
p.exists();       // check existence

// Cross-platform paths — use Path methods, not string ops
let joined = p.parent().unwrap().join("other.txt");
```

## Networking (std::net)

```rust
use std::net::{TcpListener, TcpStream, SocketAddr, UdpSocket};
// TCP server
let listener = TcpListener::bind("127.0.0.1:8080")?;
for stream in listener.incoming() {
    let mut s = stream?;
    // handle connection
}

// UDP
let socket = UdpSocket::bind("0.0.0.0:4000")?;
socket.send_to(b"hello", "127.0.0.1:5000")?;
```

## Strings deep dive

- `String` — owned, heap-allocated, UTF-8. Methods on `str` available via Deref coercion.
- `&str` — borrowed slice. `'static str` for literals.
- `OsString` / `&OsStr` — OS-native strings. Not necessarily UTF-8. For file paths, env vars.
- `CString` / `CStr` — null-terminated C strings. FFI use only.

```rust
// Parsing
let n: i32 = "42".parse()?;          // FromStr trait
// Formatting
let s = format!("{name} is {age}", name = "Alice", age = 30);
println!("debug: {:?}", value);      // Debug trait
eprintln!("error: {}", err);         // stderr output

// Char iteration — UTF-8 aware, not byte-level
for c in "café".chars() { /* 'c', 'a', 'f', 'é' */ }
```

## Macros

### Declarative macros (macro_rules!)

Pattern-based code generation. Hygienic by default.

```rust
// Custom vec-like macro
macro_rules! my_vec {
    ($($x:expr),*) => {
        {
            let mut v = Vec::new();
            $(v.push($x);)*
            v
        }
    };
}
let v = my_vec![1, 2, 3];

// Pattern matching fragments: expr, ident, pat, ty, stmt, block, item, meta, tt, path, literal

// Built-in macros from core/std
assert!(condition);           // panic if false
assert_eq!(a, b);            // panic if not equal (Debug required)
cfg!(feature = "ssl");       // compile-time config check
env!("RUST_LOG");            // compile-time env var, fails build if missing
option_env!("HOME");         // compile-time env var, None if missing
format!("{:?}", x);          // format string → String
vec![1, 2, 3];               // create Vec from literals
include_str!("file.txt");    // embed file contents at compile time
println!("{}", x);           // stdout with newline
```

### Procedural macros (proc_macro crate)

Compile-time code generation. Three kinds: function-like `#[proc_macro]`, attribute `#[proc_macro_attribute]], derive `#[proc_macro_derive]`.

```rust
// Derive macro — auto-generate trait impls
use proc_macro::TokenStream;

#[proc_macro_derive(MyDerive)]
pub fn my_derive(input: TokenStream) -> TokenStream {
    let ast = syn::parse(input)?;           // parse tokens → AST
    let generated = quote! {                // generate tokens from AST
        impl MyTrait for #ast { /* ... */ }
    };
    generated.into()
}
```

Common crates: `syn` (parse), `quote` (generate), `proc-macro2` (nightless development).

## Unsafe Rust

`unsafe` blocks disable compiler safety checks. You uphold invariants manually.

Valid reasons only:
- Dereference raw pointers (`*ptr`)
- Call unsafe functions/methods
- Access mutable static variables
- Implement unsafe traits (`Send`, `Sync`)
- Access union fields

```rust
let x = 42;
let ptr: *const i32 = &x;
unsafe {
    let val = *ptr;           // raw pointer deref — UB if dangling, unaligned, or misaligned
}

// FFI calls are unsafe
use std::ffi::c_char;
extern "C" { fn printf(format: *const c_char, ...) -> c_int; }
unsafe { printf(b"hello\0".as_ptr() as *const c_char); }
```

Rules: never expose UB through safe APIs. Document preconditions in unsafe function docs. Prefer safe abstractions over raw unsafe.

## no_std development

`#![no_std]` — no std crate, only core + alloc (optional). Embedded, OS dev, kernels.

```rust
#![no_std]
#![feature(alloc_error_handler)]  // nightly for custom OOM handler
extern crate alloc;               // manual alloc import
use alloc::{boxed::Box, rc::Rc, vec::Vec, string::String};
use core::fmt;                    // formatting without std

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }  // must define
```

What's available:
- `core` — always. Primitives, traits, iterators, Option/Result, sync primitives.
- `alloc` — opt-in. Box, Rc, Arc, Vec, String, collections.
- No `std::io`, `std::fs`, `std::net`, `std::thread`.

## Tooling

| Tool | Purpose |
|---|---|
| `cargo build` | Compile project |
| `cargo run` | Build + execute |
| `cargo test` | Run tests |
| `cargo check` | Fast compile-only check, no binary |
| `cargo clippy` | Lint for idioms, common mistakes |
| `cargo fmt` / `rustfmt` | Format code to style guide |
| `cargo doc --open` | Generate + open documentation |
| `cargo bench` | Run benchmarks |
| `cargo miri` | Undefined behavior detector (nightly) |
| `cargo publish` | Publish to crates.io |

## Naming conventions

- Crates, packages: kebab-case (`my-crate`)
- Modules, functions, variables: snake_case (`fn read_file()`)
- Types, traits, structs, enums, macros: PascalCase (`struct MyType`, `trait Clone`)
- Constants, statics: UPPER_SNAKE_CASE (`const MAX_SIZE: usize = 100;`)
- Private fields/methods: leading underscore for unused (`_unused`)
- Acronyms: treat as words (`HttpRequest`, not `HTTPRequest`)

## Workflow

1. Read `Cargo.toml` — edition, features, dependencies, toolchain config
2. Map codebase before writing — existing modules, trait impls, error types
3. Design type system first — structs, enums, traits. Types encode invariants.
4. Implement with Result-returning functions. Reserve panic for bugs only.
5. Use iterators over index-based loops. Combinators > manual state tracking.
6. Apply `#[derive]` traits: Debug always. Clone, PartialEq, Eq, Hash as needed.
7. Error types — custom enum with From impls + Display. Or thiserror crate.
8. Run `cargo clippy -- -D warnings`. Address all lints.
9. Run `cargo fmt`. Enforce consistent style.
10. Write tests: unit (`#[test]`), integration (tests/ directory), doc tests.

## Output requirements

- Rust edition from Cargo.toml (2021 or 2024)
- Result<T, E> for fallible operations. `?` operator propagation over manual match where clear.
- Iterator combinators preferred over index-based loops
- `#[derive(Debug)]` on all custom types minimum
- `&str` over `String` in function parameters when ownership not needed
- `Box<dyn Error>` or custom error enums for public APIs — never bare panic for errors
- Match exhaustiveness — handle all variants, use `_` only when intentional
- Lifetime elision used where compiler can infer. Explicit only when required
- `impl Trait` in signatures over explicit generic bounds for readability
- `const fn` for compile-time computable functions

## Guiding principles

- Ownership model is primary abstraction. Borrow checker errors → redesign data flow, not bypass with unsafe.
- Types encode invariants. Enums represent state machines. Result encodes recoverability.
- Iterators lazy + composable. No allocation until collect(). Prefer over indexed loops.
- Traits enable polymorphism without vtables when possible (generics). Trait objects (`dyn`) only when dynamic dispatch needed.
- `&str` at boundaries, `String` for ownership. Avoid unnecessary clones.
- Error handling explicit. No exceptions. `?` propagates cleanly in Result chains.
- Unsafe is last resort. Document why, what invariant maintained, what UB results from violation.

## Boundaries

- No legacy patterns unless user specifies edition < 2021.
- No async runtime preference imposed — tokio, async-std, or custom executor left to project choice.
- No planning docs unless asked. Skill is reference, not autonomous agent.

