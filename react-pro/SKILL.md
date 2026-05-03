---
name: react-pro
description: >
  React 18+ and Next.js App Router patterns. Covers React Server Components (RSC), server/client
  boundaries, Flight protocol, Next.js vendored React layer (entry-base.ts, $$compiled.internal.d.ts),
  Node-only React APIs, Turbopack remap, hooks (useState, useTransition, useDeferredValue, useId),
  perf (React.memo, lazy, virtualization), ESLint patterns. Trigger: React component architecture,
  server/client boundaries, RSC, hooks, state mgmt, perf, or `/react`.
---

# React Pro

Self-contained ref. Modern React + Next.js App Router idioms.

## Before writing code

1. Read `package.json` first — React version, Next.js version, bundler (webpack/turbopack), build targets. Don't ask for what file already says.
2. Clarify only what config files do not answer.
3. Map codebase before adding new code via code-index MCP — no duplicate logic.

## React Server Components (RSC)

Server components default. Mark client with `"use client"` directive only when needed.

- Server component → server component: synchronous props, no serialization.
- Server component → client component: props serialized via Flight protocol.
- Client component → server component: NOT allowed direct. Use server actions or restructure tree.
- `cache()` for deduping data fetches in server components.
- `revalidate()` and `unstable_cache()` for granular cache control.

```tsx
// server component (default)
async function PostList() {
    const posts = await fetchPosts();
    return <ul>{posts.map(p => <Post key={p.id} post={p} />)}</ul>;
}

// client component
"use client";
import { useState } from "react";
export function Counter() {
    const [n, setN] = useState(0);
    return <button onClick={() => setN(n+1)}>{n}</button>;
}
```

## App Router & server boundaries

- Entry point: `entry-base.ts` — only file compiled in rspack `(react-server)` layer.
- ALL imports from `react-server-dom-webpack/*` (Flight server/static APIs) must route through `entry-base.ts`.
- Files like `stream-ops.node.ts`, `app-render.tsx` access Flight APIs via `ComponentMod` parameter.
- Direct import from `react-server-dom-webpack/server.node` or `/static` outside `entry-base.ts` fails in production with "The react-server condition must be enabled". Dev mode masks this.

## React vendoring (Next.js)

- React NOT resolved from `node_modules` for App Router. Vendored into `packages/next/src/compiled/` during `pnpm build` (task: `copy_vendor_react()` in `taskfile.js`).
- Pages Router resolves from `node_modules` normally — different path, different rules.
- Two channels: stable (`compiled/react/`) and experimental (`compiled/react-experimental/`). Runtime bundle webpack config aliases via `makeAppAliases({ experimental })`.

## Type declarations for vendored packages

- `packages/next/types/$$compiled.internal.d.ts` holds `declare module` blocks for vendored React packages.
- Adding new API (e.g. `renderToPipeableStream`, `prerenderToNodeStream`) → add declaration here first.
- Bare specifier types (`declare module 'react-server-dom-webpack/server'`) are what source in `src/` imports against.

## Node.js-only React APIs

Exist in `.node` builds, absent from type definitions. Steps:

1. Add declaration to `$$compiled.internal.d.ts`
2. Export from `entry-base.ts` behind `process.env` guard with ESLint suppression
3. Access via `ComponentMod` in other files

```typescript
// In entry-base.ts (react-server layer) only:
/* eslint-disable import/no-extraneous-dependencies */
export let renderToPipeableStream: ... | undefined
if (process.env.__NEXT_USE_NODE_STREAMS) {
  renderToPipeableStream = (
    require('react-server-dom-webpack/server.node') as typeof import('react-server-dom-webpack/server.node')
  ).renderToPipeableStream
} else {
  renderToPipeableStream = undefined
}
/* eslint-enable import/no-extraneous-dependencies */

// In other files, access via ComponentMod:
ComponentMod.renderToPipeableStream!(payload, clientModules, opts)
```

## Turbopack remap

- `react-server-dom-webpack/*` silently remapped to `react-server-dom-turbopack/*` by Turbopack import map.
- Code says "webpack" everywhere. Turbopack gets own bindings at runtime.
- Debugging: stack traces and errors reference turbopack variant, not webpack.

## Hooks & state patterns

- `useState`, `useReducer` for local state. Lift to context or external store when shared.
- `useMemo` only for expensive computations. Profile before memoizing.
- `useCallback` for stable referential identity passed to memoized children.
- `useRef` for mutable values that don't trigger re-render.
- `useId` for accessible component IDs in SSR.
- `useTransition` for non-urgent updates with pending state.
- `useDeferredValue` for debouncing expensive renders without timer boilerplate.

```tsx
"use client";
import { useState, useTransition, useDeferredValue } from "react";

export function Search() {
    const [query, setQuery] = useState("");
    const deferred = useDeferredValue(query);
    const [isPending, startTransition] = useTransition();

    return (
        <input value={query} onChange={e => {
            startTransition(() => setQuery(e.target.value));
        }} />
    );
}
```

## Performance

- `React.lazy` + `Suspense` for route-level code splitting. Not for small components — overhead outweighs gain.
- `React.memo` on pure presentational components with stable props. Skip if parent re-renders rarely.
- Virtualize long lists: `@tanstack/react-virtual` or `react-window`.
- Avoid inline functions/objects as props to memoized children — breaks referential equality.
- `startTransition` for low-priority state updates that shouldn't block urgent interactions.

## ESLint patterns

- Guarded runtime `require()` blocks need `import/no-extraneous-dependencies` suppression.
- Prefer scoped block disable/enable pairs over line-level comments.
- If using `eslint-disable-next-line`, comment must be on line immediately before `require()`, NOT before `const` declaration.

## Workflow

1. Read package.json, next.config.js — versions, bundler, experimental flags
2. Map codebase with code-index MCP
3. Identify server/client boundary before writing component
4. Design prop contracts — what serializes, what stays server-side
5. Implement with RSC patterns, minimal client directives
6. Add type declarations for vendored APIs if needed
7. Write tests: React Testing Library for client components, integration tests for server flows
8. Verify production build — dev mode masks react-server condition errors
9. Review against React docs, Next.js app router conventions

## Output requirements

- React 18+ patterns from package.json version
- `"use client"` directive only when hooks, event handlers, or browser APIs needed
- Server components default for data-fetching pages and layouts
- Type-safe props — TypeScript interfaces or `React.ComponentPropsWithRef` for wrappers
- No direct `react-server-dom-webpack/*` imports outside `entry-base.ts`
- Flight API access through `ComponentMod` in non-entry files
- Vendored API declarations in `$$compiled.internal.d.ts` before source import
- ESLint suppression scoped. Block disable/enable preferred over line comments.

## Naming

- Components: `PascalCase`
- Hooks: `use` + `PascalCase` (`useMyHook`)
- Server actions: `verbNoun` format, async — `createPost`, `deleteComment`
- Utilities: `camelCase`
- Files matching components: same name as component
- Layouts and pages: lowercase kebab-case or match project convention

## Guiding principles

- Server components default. Client components explicit opt-in.
- Serialize minimal props across server/client boundary. Push logic to correct layer.
- Dev mode lies about react-server condition errors. Always test production build.
- Profile before memoize. Premature optimization root of all evil.
- Map before write — always use code-index MCP before writing anything new.

## Boundaries

- No backwards-compatibility shims unless user asks.
- No planning docs unless user asks (skill is reference, not autonomous agent).
