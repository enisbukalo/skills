---
name: bevy
description: >
  Bevy 0.17+ Rust game engine cheat sheet. Covers ECS (entities, components, resources, queries, systems),
  app lifecycle, schedules (Startup/Update/FixedUpdate), states, assets, transform hierarchy, Cargo features
  (profiles, collections, individual), modules, plugin groups, common patterns (spawn, query, resource access,
  conditional systems). Trigger when writing/debugging Bevy code, configuring Cargo features, setting up assets/scenes/UI,
  perf tuning, or `/bevy`.
---

# Bevy — Rust Game Engine

Open-source modular game engine in Rust. ECS-based, data-driven. Focus: dev productivity + perf.

Version: 0.17+ | Crate: `bevy` | Docs: https://docs.rs/bevy/latest/bevy/

## Quick Start

```rust
use bevy::prelude::*;

fn main() {
    App::new()
        .add_systems(Update, hello_world)
        .run();
}

fn hello_world() {
    println!("hello world");
}
```

Cargo: `bevy = "0.17"` (default features = full engine: 2d + 3d + ui)

## Core Concepts

### App Lifecycle
- `App::new()` — create app
- `.add_plugins()` / `.add_systems()` — register plugins, systems
- `.run()` — start main loop

### ECS
- **Entities** — IDs, no data
- **Components** — data on entities (`#[derive(Component)]` structs)
- **Resources** — global singletons (`#[derive(Resource)]`)
- **Queries** — fetch components from matching entities
- **Systems** — funcs run each frame, take queries/resources via `SystemParam`

### Schedules & Phases
- `Startup` — once before main loop
- `Update` — every frame
- `FixedUpdate` — fixed timestep (physics)
- Custom via `.add_configs()` / `.add_systems()`

### States
App-wide finite state machines. Model game structure: paused, combat, loading.
```rust
#[derive(States, Debug, PartialEq, Eq, Hash, Default)]
enum GameState { Menu, Playing, Paused }

app.add_systems(OnEnter(GameState::Playing), start_game);
app.add_systems(Update, play_logic.run_if(in_state(GameState::Playing)));
```

### Assets
Loaded from disk, referenced by `Handle<T>`.
- Textures, models (glTF 2.0), sounds, music, scenes, scripts
- Asset server: `Res<AssetServer>` — `.load()`, `.get()`
- Types: `Image`, `Mesh`, `AudioStream`, `Scene`, `Shader`

### Transform Hierarchy
- `Transform` — translation, rotation, scale per entity
- `GlobalTransform` — computed world-space transform
- Parent-child via relationship components; hierarchy affects render order

## Cargo Features

### Profiles (high-level, use with `default-features = false`)
| Feature | Includes |
|---------|----------|
| `default` | 2d + 3d + ui |
| `2d` | Core, 2D, UI, scenes, audio, picking |
| `3d` | Core, 3D, UI, scenes, audio, picking |
| `ui` | Core, UI, scenes, audio, picking |

```toml
bevy = { version = "0.17", default-features = false, features = ["2d"] }
```

### Collections (mid-level, compose own profile)
| Feature | Purpose |
|---------|---------|
| `dev` | Hot-reloading, debug tools (skip for release) |
| `audio` | Audio support |
| `scene` | Scene composition |
| `picking` | Pointer interaction (hover, click, drag) |
| `default_app` | Core baseline — headless, servers, CLI |
| `default_platform` | OS, windowing, input backends |
| `common_api` | Scene defs without renderer |
| `2d_api` / `3d_api` / `ui_api` | API without render backend |
| `2d_bevy_render` / `3d_bevy_render` / `ui_bevy_render` | Built-in renderers |

### Key Individual Features
- `bevy_gltf` — glTF 2.0 loading
- `bevy_pbr` — PBR rendering
- `bevy_animation` — animation
- `bevy_remote` — remote protocol
- `bevy_solari` — raytraced lighting (experimental)
- `gltf_animation` — glTF animation
- `file_watcher` / `embedded_watcher` — asset hot-reload
- `trace_tracy` / `trace_chrome` — profiling
- `multi_threaded` — parallel execution (default on)
- `tonemapping_luts` — tonemapping textures (everything pink? enable this)

### Shader Formats
- `shader_format_glsl`, `shader_format_spirv`, `shader_format_wesl`
- `spirv_shader_passthrough` — Vulkan-only SPIR-V loading

## Modules

| Module | Purpose |
|--------|---------|
| `app` | App layer, lifecycle |
| `ecs` | ECS core |
| `asset` | Asset loading, handles, processors |
| `audio` | Audio playback |
| `camera` | Camera types, visibility, culling |
| `camera_controller` | Prebuilt cam controllers (free, pan) |
| `color` | Color spaces, conversions |
| `core_pipeline` | Render pipeline basics |
| `dev_tools` | Dev utilities, debug overlay |
| `diagnostic` | Perf monitoring |
| `gizmos` | Immediate-mode draw API for debug |
| `gltf` | glTF 2.0 loader |
| `input` / `input_focus` | Input, UI focus |
| `light` | Point, directional, spot lights |
| `log` | Logging, tracing |
| `math` | Math types (wraps `glam`) |
| `mesh` | Mesh format, primitives |
| `pbr` | Physically-based rendering |
| `picking` | Pointer interaction |
| `post_process` | DOF, bloom, chromatic aberration |
| `reflect` | Rust reflection runtime |
| `render` | Render backend (wgpu) |
| `scene` | Scene def, serialization |
| `shader` | Shader asset handles |
| `solari` | Raytraced lighting (experimental) |
| `sprite` / `sprite_render` | 2D sprites |
| `state` | Global state machines |
| `tasks` | Async task execution |
| `text` | Text positioning, rendering |
| `time` | Time mgmt, fixed timestep |
| `transform` | Transform hierarchy |
| `ui` / `ui_render` | ECS-driven UI (2D + 3D) |
| `window` | Platform-agnostic windowing |

## Plugin Groups

- `DefaultPlugins` — full feature set (rendering, audio, input)
- `MinimalPlugins` — minimal setup for headless/custom rendering

```rust
App::new().add_plugins(MinimalPlugins); // custom render pipeline
App::new().add_plugins(DefaultPlugins); // everything
```

## Patterns

### Spawn Entity with Components
```rust
commands.spawn((
    Name::new("player"),
    Transform::from_translation(Vec3::ZERO),
    Sprite::default(),
));
```

### Query Pattern
```rust
fn move_players(mut query: Query<&mut Transform, With<Player>>) {
    for mut transform in &mut query {
        transform.translation.x += 1.0;
    }
}
```

### Resource Access
```rust
fn show_time(time: Res<Time>) {
    println!("delta: {:.3}", time.delta_secs());
}
```

### Conditional Systems
```rust
app.add_systems(Update, game_logic.run_if(in_state(GameState::Playing)));
app.add_systems(Update, pause_menu.run_if(in_state(GameState::Paused)));
```

## Environment Variables (render)

Check `bevy_render` docs for GPU/backend control via env vars.

## When to Use

- Writing Bevy game code or systems
- Debugging ECS queries, component issues, render problems
- Configuring Cargo features for minimal builds
- Setting up asset pipelines, scenes, UI
- Perf tuning: tracing, diagnostics, multithreading
- `/bevy` trigger
