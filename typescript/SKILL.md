---
name: typescript
description: >
  TypeScript 6.0 cheat sheet from "The Concise TypeScript Book". Covers type system (structural typing, inference, narrowing, sets),
  primitives, interfaces vs types, generics, utility types, conditional/mapped types, classes, decorators, tsconfig, enums, unions/intersections,
  advanced patterns (discriminated unions, template literal types, satisfies). Trigger when user writes/debugs TS code, asks about types,
  generics, utility types, tsconfig, type narrowing, or "/ts".
---

# TypeScript 6.0

Self-contained ref. Idiomatic TS only. Skip legacy patterns.

## Core mental model

- TS = static layer over JS. Types erased at compile — zero runtime cost.
- Structural typing: compatibility by shape, not name. `{a:string}` matches any object with `a`.
- Type checking and compilation are independent. Code emits even with type errors.
- Runtime needs values, not types. Use tagged unions (`kind: 'dog'`) or `instanceof` (classes only).

## tsconfig.json essentials

```jsonc
{
  "compilerOptions": {
    "target": "ES2022",           // JS version to emit. ES5 removed in TS 6.
    "module": "nodenext",         // module system: nodenext, node16, esnext, commonjs
    "moduleResolution": "node",   // classic deprecated. Use node for modern TS.
    "strict": true,               // enabled by default in TS 6. Enables null checks, noImplicitAny, thisIsAny check.
    "esModuleInterop": true,      // always-on in TS 6. Allows `import x from 'mod'` on CJS modules.
    "skipLibCheck": true,         // speed up compile by skipping .d.ts typechecking of deps.
    "declaration": true,          // emit .d.ts files.
    "sourceMap": true,            // generate source maps.
    "outDir": "./dist",           // output directory.
    "rootDir": "./src"            // root input directory.
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

`importHelpers: true` — uses `tslib` instead of duplicating helpers in output. Smaller bundles.

Migration tip: use `allowJs: true` + `@ts-check` for gradual JS-to-TS migration. Enable `noImplicitAny` later.

## Types as sets (mental model)

| Set concept | TS type | Example |
|---|---|---|
| Empty set | `never` | nothing assignable to it |
| Single element | literal | `'x'`, `42`, `true` |
| Finite set | union / boolean | `'a' \| 'b'`, `boolean` |
| Infinite set | string, number, object | any value in range |
| Universal set | `any`, `unknown` | everything assignable to it |

- Union `(T1 | T2)` = wider (both). Intersection `(T1 & T2)` = narrower (only shared members).
- `extends` = subset constraint. Not OOP inheritance. Pure structural check.

## Primitive types

```typescript
// string, boolean, number, bigint, symbol, null, undefined
let s: string = "hi";
let b: boolean = true;
let n: number = 42;       // no int/float distinction
let bi: bigint = 9007199254740991n;
let sym: symbol = Symbol("id");
let u: undefined = undefined;
let nu: null = null;

// Arrays
let nums: number[] = [1, 2, 3];
let nums2: Array<number> = [1, 2, 3];

// Tuples (fixed-length arrays)
let point: [number, number] = [10, 20];      // anonymous tuple
let person: [string, age?: number] = ["Alice"]; // labeled/optional tuple elements

// any — escape hatch. Skip type checking. Avoid.
// unknown — type-safe any. Must narrow before use.
```

## Type declarations vs assertions

```typescript
// Declaration (preferred) — triggers excess property check
type X = { a: string };
const x: X = { a: 'a', b: 'b' }; // Error: excess property 'b'

// Assertion (as) — skips excess property check. Use for DOM or known data.
const y = { a: 'a', b: 'b' } as X; // Valid, but unsafe

// Type assertion with template literal key remapping
type J<Type> = { [K in keyof Type as `prefix_${string & K}`]: () => Type[K] };
```

## Property checking rules

- Structural typing allows extra properties when assigning variables. Object literals get excess property check ("freshness").
- Weak types (all optional props) reject objects with zero overlapping properties unless asserted or index signature added.
- Freshness lost on variable widening and type assertions.

```typescript
type X = { a: string };
let x: X;
x = { a: 'a', b: 'b' }; // Error (freshness)
var y: { a: string; b: string } = { a: 'a', b: '' };
x = y;                    // OK (widened, no freshness check)
```

## Type inference & widening

- TS infers from initializers, defaults, return types, function returns.
- `let` widens to broader type (`'hello'` → `string`). Use `const` for literal preservation.
- Const modifier on type parameters: `<const T extends string>(x: T) => void`.

```typescript
let x = 'x';        // inferred: string (widened from literal)
const y = 'y';      // inferred: 'y' (literal preserved)
```

## Type narrowing

Narrow types via conditions, guards, and control flow.

```typescript
// typeof guard
function padLeft(value: string, padding: string | number) {
  if (typeof padding === "number") return Array(padding + 1).join(" ") + value;
  if (typeof padding === "string") return padding + value;
  // padding is never here — exhaustiveness check
}

// instanceof narrowing (classes only, types erased at runtime)
class Dog { bark() {} }
class Cat { meow() {} }
function makeNoise(animal: Dog | Cat) {
  if (animal instanceof Dog) animal.bark(); // works because class exists at runtime
}

// Truthiness narrowing
function fn(val: string | "" | 0) {
  if (val) { /* val is string */ } else { /* val is "" | 0 */ }
}

// Equality narrowing
if (x === y) { ... } // narrows both x and y in block

// In operator narrowing
interface A { foo: number; }
interface B { bar: string; }
function test(a: A | B) {
  if ("foo" in a) return a.foo; // a is narrowed to A
}

// User-defined type guard
function isFish(pet: Fish | Bird): pet is Fish {
  return (pet as Fish).swim !== undefined;
}

// assert function
function assertIsNumber(val: unknown): asserts val is number {
  if (typeof val !== "number") throw new Error("Not a number");
}

// switch-true for exhaustive narrowing
type Shape = { kind: 'circle'; radius: number } | { kind: 'square'; side: number };
function area(s: Shape) {
  switch (true) {
    case s.kind === 'circle': return Math.PI * s.radius ** 2; // s narrowed to circle
    case s.kind === 'square': return s.side ** 2;             // s narrowed to square
    default: { const _exhaustive: never = s; return _exhaustive; } // exhaustiveness check
  }
}

// Non-null assertion (bypasses null/undefined) — use sparingly
person!.name;

// Optional chaining + nullish coalescing
const city = person?.address?.city ?? "Unknown";
```

## Discriminated unions

Tagged union pattern. Runtime value distinguishes types at compile time.

```typescript
interface Circle { kind: 'circle'; radius: number; }
interface Square { kind: 'square'; sideLength: number; }
type Shape = Circle | Square;

function area(s: Shape): number {
  switch (s.kind) {
    case 'circle': return Math.PI * s.radius ** 2; // TS narrows to Circle
    case 'square': return s.sideLength ** 2;       // TS narrows to Square
    default: { const _exhaustiveCheck: never = s; return _exhaustiveCheck; }
  }
}

// if/else also works
function describe(s: Shape) {
  if (s.kind === 'circle') console.log(`radius ${s.radius}`); // narrowed to Circle
}
```

## Interfaces vs type aliases

| | `interface` | `type` |
|---|---|---|
| Declaration merging | Yes | No |
| Extends | `extends`, multiple | `&` (intersection) |
| Implements | `class implements` | class can implement a type alias |
| Union/intersection | No | Yes (`A \| B`, `A & B`) |
| Mapped types | No | Yes |
| Conditional types | No | Yes |
| Index signatures | Yes | Yes |

Use `interface` for public APIs and things that may merge. Use `type` for unions, intersections, mapped/conditional types.

```typescript
// Interface declaration merging (useful for augmentation)
interface Window { title: string; }   // merges with existing Window
interface Window { subtitle: number; }

// Type alias — more flexible
type ID = string | number;           // union
type Point3D = Point & { z: number }; // intersection
```

## Enums

Enums create named constants. Numeric enums auto-increment. String enums require literals.

```typescript
// Numeric enum (auto-increment, reverse mapping enabled)
enum Direction { Up, Down, Left, Right }  // 0,1,2,3
Direction[0] === "Up"   // true — reverse mapping

// String enum (no reverse mapping)
enum Status { Active = 'active', Inactive = 'inactive' }

// const enum (inlined at compile — no runtime object)
const enum Color { Red, Green, Blue }
let c = Color.Red;  // compiles to: let c = 0;

// Computed members break reverse mapping for subsequent values
enum X { A = 1 << 1, B = 2 }   // A=2, B=2 — reverse mapping broken after computed
```

Enums comparable with numbers. Different enum types not comparable with each other.

## Generics

Reusable across functions, classes, interfaces, type params.

```typescript
// Generic function
function identity<T>(arg: T): T { return arg; }
let result = identity<string>("hello");   // explicit
let result2 = identity("hello");          // inferred from usage

// Generic constraint — `extends` limits the set
interface HasId { id: number; }
function logId<T extends HasId>(item: T): void { console.log(item.id); }

// keyof + generics for indexing
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// this parameter typing (for fluent APIs)
interface Config { set(key: string, val: unknown): this; get<K extends keyof this>(key: K): this[K]; }

// Generic contextual narrowing — TS narrows based on type guard in same scope
function validate<T>(value: T | null, predicate: (v: T) => boolean): T {
  if (!value || !predicate(value)) throw new Error("invalid");
  return value; // narrowed to T without assertion
}

// Const generic parameters (TS 5.0+)
function createTuple<const T extends readonly unknown[]>(...args: T): T { return args; }
```

## Utility types

Built-in type transformers. All work with `keyof`, mapped types, and conditionals.

```typescript
type User = { id: number; name: string; email: string };

Partial<User>       // all props optional: { id?: number; name?: string; email?: string }
Required<User>      // all props required (removes ?)
Readonly<User>      // all props readonly
Pick<User, 'id' | 'name'>    // subset: { id: number; name: string }
Omit<User, 'email'>          // exclude keys: { id: number; name: string }

Exclude<'a'|'b'|'c', 'a'|'c'>  // set difference: 'b'
Extract<'a'|'b'|'c', 'a'|'d'>  // set intersection: 'a'

NonNullable<string \| number \| null \| undefined>  // string | number
Parameters<(x: number, y: string) => void>          // [number, string]
ReturnType<typeof fn>                                 // return type of function
InstanceType<typeof MyClass>                          // instance type (not constructor)

Awaited<Promise<string>>                              // unwrap Promise<T> → T
ThisParameterType<f> / OmitThisParameter<f>           // extract/remove this param
ThisType<{foo: string}>                               // marker for enclosing object context

Uppercase<"hello">     // "HELLO" (template literal compile-time)
Lowercase<"Hello">     // "hello"
Capitalize<"hello">    // "Hello"
Uncapitalize<"Hello">  // "hello"

NoInfer<T>              // prevent inference at use site: function foo(x: NoInfer<T>) {}
```

## Mapped types

Transform existing types by iterating keys.

```typescript
// Basic mapped type
type Readonly<T> = { readonly [K in keyof T]: T[K] };
type Optional<T> = { [K in keyof T]?: T[K] };

// With modifier: -readonly adds back, ? adds optional
type Mutable<T> = { -readonly [K in keyof T]: T[K] };

// Key remapping (TS 4.1+)
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K}`]: () => T[K]
};

// Conditional mapped types
type IfString<T, Y, N> = T extends string ? Y : N;
type StringKeys<T> = {
  [K in keyof T as T[K] extends string ? K : never]: T[K]
};
```

## Conditional types

Types that depend on conditions. Distributive by default (unions get distributed).

```typescript
// Basic conditional type
type IsString<T> = T extends string ? true : false;
type A = IsString<"hello">;  // true
type B = IsString<42>;       // false

// Non-distributive: wrap in tuple [T] to prevent distribution
type NotDistributed<T> = [T] extends [string] ? true : false;
type C = NotDistributed<string | number>; // false (not distributed)

// infer — extract type from conditional pattern
type ElementType<T> = T extends (infer U)[] ? U : T;
type E = ElementType<number[]>;  // number

// Recursive conditional types for complex transforms
type Flatten<T> = T extends (infer U)[] ? Flatten<U> : T;
type Nested = [1, [2, [3]]];
type Flat = Flatten<Nested>; // 1 | 2 | 3

// Predefined: Partial, Required, Pick, Omit, Record, etc. are all conditional types internally
```

## Template literal types

String types computed at compile time.

```typescript
type EventName = `on${Capitalize<string>}`;   // "onClick" | "onHover" | ...
type Status = 'pending' | 'success' | 'error';
type StatusHandler = `handle_${Status}`;       // "handle_pending" | "handle_success" | "handle_error"

// Combined with union expansion
type Id<T extends string> = `${T}_id`;
type DeptId = Id<'engineering' | 'hr'>;  // "engineering_id" | "hr_id"

// Template String Pattern Index Signatures (TS 5.0+)
type Paths = `components/${string}/index.ts`;
```

## The satisfies operator

Validate expression against type without changing the resulting type.

```typescript
interface ButtonConfig { label: string; onClick: () => void; variant?: 'primary' | 'secondary'; }

// Without satisfies — loses specific literal types, gets widened to interface
const config1 = { label: "Submit", onClick: () => {}, variant: "primary" } as ButtonConfig;
// config1.variant is string (widened), not 'primary'

// With satisfies — validates shape but keeps original type
const config2 = { label: "Submit", onClick: () => {}, variant: "primary" } satisfies ButtonConfig;
// config2.variant is 'primary' (literal preserved) + validated against interface

// Prevent excess properties while preserving narrowest type
type Color = { r: number; g: number; b: number };
const c = { r: 1, g: 2, b: 3, a: 4 } satisfies Color; // Error: 'a' not in Color
```

## Structural typing rules (key gotchas)

- Functions bivariant by default (parameters accept supertypes AND subtypes). Safe for callbacks but relaxes checking.
- Return types must be compatible (source return assignable to target return).
- Function parameters compared structurally, not by name: `(a:number)=>void` matches `(x:number)=>void`.
- Extra optional params are fine. Discarding params is OK (`[1,2].map((_, i) => i)`).
- Rest parameter = infinite optional params.
- Private/protected members must come from same inheritance chain.
- Generics compared by final structure after applying type args.

```typescript
// Bivariance example — works but unsafe for non-callbacks
type Fn = (x: Animal) => void;
let f1: Fn = (a: Dog) => {};   // OK (bivariant)
let f2: Fn = (a: Cat) => {};   // OK (bivariant)

// Fix with function types in strict mode or manual contravariance for args
```

## Classes

```typescript
class Animal {
  constructor(public name: string, private age: number) {}  // parameter properties

  protected sound(): string { return "..."; }               // accessible in subclass

  get fullInfo() { return `${this.name} (${this.age})`; }   // getter
  set fullInfo(val: string) { /* setter */ }                // setter

  static create(name: string) { return new Animal(name, 1); } // static method

  abstract speak(): void;                                    // abstract (requires abstract class)
}

// Access modifiers: public (default), private, protected
// Auto-accessors (TS 4.9+): accessor name: string — compiles to private get/set with #private field
class Cat extends Animal {
  accessor meowVolume = 10;   // auto-accessor

  speak() { console.log(this.sound()); }  // can access protected

  constructor(name: string, age: number) {
    super(name, age);
  }
}

// Private/protected constructors — singleton or factory pattern
class Singleton {
  private static instance?: Singleton;
  private constructor() {}
  static getInstance(): Singleton { return this.instance ??= new Singleton(); }
}
```

## Decorators (TS 5.0+ standard)

Experimental but standardized in TS 5+. Use `@experimentalDecorators` for pre-5 code.

```typescript
// Class decorator — receives constructor + context, returns modified class or void
function LogConstructor(
  target: Function,
  context: ClassDecoratorContext
) {
  return class extends target {
    constructor(...args: any[]) {
      super(...args);
      console.log(`Created ${String(context.name)}`);
    }
  };
}

// Method decorator — wraps method with pre/post logic
function LogMethod(
  target: Function,
  context: ClassMethodDecoratorContext
) {
  const methodName = String(context.name);
  return function (this: any, ...args: any[]) {
    console.log(`Entering ${methodName}`);
    const result = target.call(this, ...args);
    console.log(`Exiting ${methodName}`);
    return result;
  };
}

// Property decorator — replaces property with getter/setter
function UpperCase(
  _target: unknown,
  context: ClassFieldDecoratorContext<string>
) {
  return function (this: any, value: string) {
    return value.toUpperCase();
  };
}
```

## Type-only imports/exports (TS 3.8+)

```typescript
import type { User } from './types';           // type-only import
import { type User } from './types';            // inline type modifier
export type { User, Config };                    // type-only re-export
```

Ensures types erased in output — no runtime import for purely-typed imports.

## Optional chaining & nullish coalescing

```typescript
// Optional chaining — short-circuits on null/undefined, returns undefined
const city = user?.address?.city;
const first = arr?.[0];
const val = obj.method?.();  // calls method only if it exists

// Nullish coalescing — only for null|undefined (not falsy values like 0, '', false)
const name = input ?? "default";   // uses default only if null/undefined
const count = value ?? 0;          // preserves 0 and '' as valid values

// Combined
const title = config?.ui?.title ?? "Untitled";
```

## Advanced patterns

### Exhaustiveness checking with `never`

```typescript
type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

function parseJson(value: unknown): Json {
  switch (typeof value) {
    case 'string': case 'number': case 'boolean': return value;
    case 'object':
      if (value === null) return null;
      if (Array.isArray(value)) return value.map(parseJson);
      return Object.fromEntries(Object.entries(value as object).map(([k, v]) => [k, parseJson(v)]));
    default: {
      const _check: never = value;  // compile error if new variant added to Json
      return _check;
    }
  }
}
```

### Recursive types (trees, nested data)

```typescript
type TreeNode<T> = { value: T; children: TreeNode<T>[] };
type ListNode<T> = { data: T; next: ListNode<T> | null };
type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

// Recursive conditional types for type transforms
type DeepReadonly<T> = { readonly [K in keyof T]: T[K] extends object ? DeepReadonly<T[K]> : T[K] };
```

### Mixin classes

```typescript
function Timestamped<TBase extends new (...args: any[]) => {}>(Base: TBase) {
  return class extends Base {
    readonly timestamp = Date.now();
  };
}

function Activatable<TBase extends new (...args: any[]) => {}>(Base: TBase) {
  return class extends Base {
    isActive = true;
  };
}

class User { constructor(public name: string) {} }
const TimestampedUser = Timestamped(User);
const ActiveTimestampedUser = Activatable(TimestampedUser);
```

### Variadic tuple types (TS 4.0+)

```typescript
function concat<T extends any[]>(...arrays: [...T[]]): T { /* ... */ }
type FirstElement<T extends any[]> = T extends [infer F, ...any[]] ? F : never;
type RestElements<T extends any[]> = T extends [any, ...infer R] ? R : [];

// Tuple destructuring with rest
function headTail<T extends any[]>(arr: T): [FirstElement<T>, RestElements<T>] {
  return [arr[0], arr.slice(1) as any];
}
```

## ES modules in Node.js (TS 4.7+)

```typescript
// tsconfig.json
{ "compilerOptions": { "module": "nodenext", /* or "node16" */ } }

// File extensions
import x from './mod.mjs';   // .mts → .mjs (ESM)
import y from './mod.cjs';   // .cts  → .cjs (CommonJS)

// package.json: "type": "module" for ESM project by default
```

## Key gotchas & best practices

- Types erased at runtime. `instanceof` only works with classes, not type aliases or interfaces. Use tagged unions.
- `any` disables checking. Prefer `unknown`. Narrow before use.
- `void` is not assignable to/from anything except `any`. `null`/`undefined` treated like `never` when strictNullChecks on.
- Excess property check only fires on object literals assigned directly or passed as arguments. Variable assignments skip it.
- Generic functions bivariant by default for parameters (callback safety). Use explicit types to tighten.
- `as const` preserves literal types and makes properties readonly.
- `satisfies` validates without widening — use when you want both checks AND narrowest type.
- `skipLibCheck: true` speeds up compile significantly. Safe to enable.
- Enums create runtime objects. Use `const enum` for inlining or string literals + union types for zero-cost alternatives.
- Mapped types with `keyof T` iterate only public keys, not private/protected ones.
- Conditional types distribute over unions by default. Wrap in `[T]` to prevent distribution.

## Migration checklist (JS → TS)

1. Add `tsconfig.json` with `allowJs: true`, `noImplicitAny: false`.
2. Add `// @ts-check` at top of `.js` files for incremental checking.
3. Install `@types/*` packages from DefinitelyTyped: `npm i -D @types/package-name`.
4. Migrate bottom-up (leaves first — no dependents). Use `madge` for dependency graph.
5. Generate types from specs (Swagger, GraphQL) when available. Avoid generating from raw data.
6. Enable `noImplicitAny: true`. Fix remaining issues.
7. Remove `@ts-check`, rename `.js` → `.ts`.
8. Set `noEmitOnError: false` during migration to keep emitting JS despite errors.
