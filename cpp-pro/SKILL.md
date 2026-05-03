---
name: cpp-pro
description: >
  Modern C++ systems programming patterns. Covers C++11/14/17/20/23 features, RAII and ownership,
  POSIX/OS interfaces (mmap, epoll, signals, fds), templates and concepts, move semantics, STL,
  concurrency (thread, mutex, atomic), error handling (std::expected, error_code), const/constexpr,
  GTest testing patterns. Trigger: writing or reviewing modern C++, RAII, memory safety, OS interfaces,
  concurrency, templates, perf optimization, or `/cpp`.
---

# C++ Pro

Self-contained ref. Modern C++ idioms. Skip legacy patterns.

## Before writing code

1. Read `CMakeLists.txt` first — C++ standard, platform/OS target, toolchain, build type, ABI/linkage. Don't ask for what file already says.
2. Clarify only what CMakeLists.txt does not answer.
3. Map codebase before adding new code via code-index MCP — no duplicate logic.

## Modern C++ features

- **C++11/14**: `auto`, range-for, lambdas, `nullptr`, `constexpr`, `std::move`, `std::forward`, `noexcept`
- **C++17**: structured bindings, `if constexpr`, `std::optional`, `std::variant`, `std::string_view`, `[[nodiscard]]`
- **C++20**: concepts, ranges, coroutines, `std::span`, `std::format`, `consteval`, `<=>`
- **C++23**: `std::expected`, `std::flat_map`, `std::mdspan`, `std::print`, deducing `this`

## RAII and ownership

Every resource has clear owner in type system.

- `std::unique_ptr` for exclusive ownership. `std::shared_ptr` only when shared lifetime truly needed.
- No raw `new`/`delete`. Use `std::make_unique` / `std::make_shared`.
- Custom deleters or RAII wrappers for all OS handles.
- Rule of Zero default. Rule of Five only when managing raw resource directly.

```cpp
class FileHandle {
    int fd_{-1};
public:
    explicit FileHandle(const char* path) : fd_(::open(path, O_RDONLY | O_CLOEXEC)) {
        if (fd_ < 0) throw std::system_error(errno, std::generic_category());
    }
    ~FileHandle() { if (fd_ >= 0) ::close(fd_); }
    FileHandle(FileHandle&& o) noexcept : fd_(std::exchange(o.fd_, -1)) {}
    FileHandle& operator=(FileHandle&& o) noexcept {
        if (this != &o) { if (fd_ >= 0) ::close(fd_); fd_ = std::exchange(o.fd_, -1); }
        return *this;
    }
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    [[nodiscard]] int get() const noexcept { return fd_; }
};
```

## Systems programming & OS interfaces

- Wrap all POSIX I/O in RAII. Always check return values. Map `errno` → `std::error_code`.
- `mmap`/`munmap` wrapped in RAII. Annotate with `madvise`.
- Signal handlers call only async-signal-safe fns. Use `signalfd` or self-pipe trick.
- `O_CLOEXEC` all fds before `exec`. Use `posix_spawn` for subprocess.
- Handle `EINTR` on all blocking syscalls. Audit `EAGAIN`/`EWOULDBLOCK` in non-blocking paths.
- `epoll`, `io_uring`, `timerfd`, `inotify`, `netlink` — wrap each in RAII class.
- Minimize syscall frequency. Batch ops. Use vDSO-backed calls where possible.

## Templates & concepts

Prefer C++20 concepts over SFINAE. Use `if constexpr` over template specialization for branching.
Document all template params and their requirements.

```cpp
template <typename T>
concept Hashable = requires(T x) {
    { std::hash<T>{}(x) } -> std::convertible_to<std::size_t>;
};

template <Hashable K, typename V>
class HashMap { /* ... */ };
```

## Move semantics

- Perfect forwarding (`T&& + std::forward<T>`) in generic code.
- Move ctors and assignment ops `noexcept`.
- Pass `std::string_view` / `std::span` for non-owning read access.
- No `std::move` from return when NRVO applies.

## STL

- Prefer `<algorithm>` and `<ranges>` over hand loops.
- `std::vector` default. `reserve()` when size predictable.
- `std::unordered_map` for O(1) lookup. `std::map` only when ordering required.

## Concurrency

- `std::thread`, `std::jthread`, `std::async`, or thread pool.
- `std::mutex` + `std::lock_guard` / `std::scoped_lock` for shared state.
- `std::atomic<T>` for lock-free flags. Specify memory order explicit.
- Run under ThreadSanitizer in CI.

```cpp
std::atomic<int> counter{0};
counter.fetch_add(1, std::memory_order_relaxed);

std::mutex m;
{
    std::scoped_lock lock(m);
    // critical section
}
```

## Error handling

- `std::expected<T,E>` (C++23) preferred for systems code.
- `std::error_code` for POSIX/OS errors.
- `errno` + return codes for C-compatible APIs.
- Never silent swallow errors. Log with context (file, line, errno string).

```cpp
std::expected<std::string, std::error_code> readFile(const char* path) {
    FileHandle fh{path};
    // ...
    if (failed) return std::unexpected(std::error_code{errno, std::generic_category()});
    return contents;
}
```

## const & constexpr

- Mark everything `const` unless mutation required.
- `constexpr` for compile-time values. `consteval` to force compile-time eval.

## Testing — GoogleTest

- `TEST()`, `TEST_F()`, `TEST_P()` — fixtures for shared setup/teardown, parameterized for data-driven.
- `ASSERT_*` fatal (stops test). `EXPECT_*` non-fatal (continues). Choose deliberate.
- Mock with GoogleMock (`MOCK_METHOD`, `ON_CALL`, `EXPECT_CALL`). Prefer `NiceMock<T>` to kill uninteresting call warnings.
- `SCOPED_TRACE()` to annotate loops or helpers — failures report meaningful context.
- Never assert on impl details. Test observable behavior and public contracts.
- Prefer `EXPECT_THAT` with matchers (`HasSubstr`, `ElementsAre`, `Pointee`) over raw `EXPECT_EQ` for complex comparisons.
- Test error paths explicit. Inject failures via dependency inversion or mock seams, not ifdefs.
- One logical concept per test. Test names read as sentences: `WidgetFactory_CreateWidget_ReturnsNullOnOOM`.

```cpp
TEST_F(WidgetFactoryTest, CreateWidget_ReturnsNullOnOOM) {
    EXPECT_CALL(allocator_, allocate).WillOnce(Return(nullptr));
    auto w = factory_.create();
    EXPECT_EQ(w, nullptr);
}
```

## Workflow

1. Read CMakeLists.txt — standard, toolchain, build targets
2. Map codebase with code-index MCP
3. Design ownership before writing impl
4. Write interface — header with concepts, documented pre/postconditions
5. Implement with RAII
6. Apply const correctness throughout
7. Write GTest unit tests for all new public interfaces and non-trivial logic. Cover happy path, boundary conditions, all explicit error paths.
8. Use test fixtures (`::testing::Test`) when 2+ tests share setup/teardown.
9. Add integration tests in separate target when unit crosses OS or IPC boundary.
10. Profile before optimize (perf, Valgrind, VTune)
11. Review against C++ Core Guidelines. Document intentional deviations.

## Output requirements

- C++ standard from CMakeLists.txt, follow Core Guidelines
- `#pragma once` in all headers
- No raw `new`/`delete` in app code
- `noexcept` on all move ops, destructors, swap
- `[[nodiscard]]` on fns whose return must not be discarded
- Explicit memory orders on all `std::atomic` ops
- All POSIX calls checked. `errno` mapped or logged.
- No change to CMakeLists.txt or new build tooling unless asked
- Doxygen comments on all public APIs. Ownership/lifetime contracts noted. Syscall/platform assumptions noted.
- Test files mirror source tree under `tests/`. Named `<sourceFile>Test.cpp`.
- Each test binary registered with `add_executable` + `target_link_libraries(... GTest::gtest_main)`. No modify build files unless asked.
- No production logic in test files. Extract helpers into `testutil/` library if reuse needed.

## Naming

- Types: `PascalCase`
- Functions, methods, variables, parameters: `camelCase`
- Private members: `m_` prefix + `camelCase`
- Constants, enumerators: `UPPER_SNAKE_CASE`
- Files: `camelCase`

## Guiding principles

- Compile-time errors over runtime errors.
- Zero-cost abstractions — RAII and templates add no runtime overhead.
- Explicit over implicit — name ownership, lifetimes, error paths in type system.
- Every syscall has documented failure mode and handler.
- Map before write — always use code-index MCP before writing anything new.

## Boundaries

- No backwards-compatibility shims unless user asks.
- No planning docs unless user asks (skill is reference, not autonomous agent).
- No full paths in includes.
