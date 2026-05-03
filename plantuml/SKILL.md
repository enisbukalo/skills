---
name: plantuml
description: >
  Apply when writing or editing PlantUML (.puml, .plantuml, .pu) files or generating diagrams from text.
  Covers type selection, syntax, modern styling, preprocessing, abstraction level, anti-patterns.
  Project conventions override these defaults.
---

# PlantUML Diagramming

Match project conventions. Check existing `.puml` files first — naming, layout, theme, abstraction. Check for shared `!include` or theme file. Defaults below apply only if no project convention exists.

## Never rules

Unconditional. Break = broken or unreadable diagram.

- **Never omit `@startuml`/`@enduml`** — PlantUML fails silent without them. Every file needs delimiters (or type equivalent: `@startmindmap`/`@endmindmap`, `@startgantt`/`@endgantt`).

- **Never use cryptic abbreviations as labels** — plain English. `AuthSvc` means nothing to PM; `Authentication Service` does. Labels for humans, not compilers.

- **Never make >15 elements without grouping** — overcrowded = useless. Group with `package`, `rectangle`, `node`, `cloud`, `together`. Cannot group? Split file.

- **Never use legacy `skinparam` when `<style>` works** — `skinparam` deprecated. Use `<style>` blocks. Exception: properties `<style>` does not yet support (e.g. activity stereotypes still need `skinparam activity {}`).

- **Never hardcode inline colors on elements** — use stereotypes + `skinparam`/`<style>`. Inline `#FF0000` after `;` causes activity diagram syntax errors and drift.

- **Never mix arrow direction (`-up->`, `-down->`) with layout hacks** — let auto-layout work first. Direction hints only when auto-layout broken. Multiple overrides fight each other.

- **Never use `autonumber` without format** — bare `autonumber` = noise. Format string: `autonumber "<b>[000]"` or `autonumber 1 10 "<b>[00]"`.

- **Never omit participant declarations in sequence diagrams** — undeclared = source-order render = unstable layout. Declare all participants top, in display order.

- **Never write diagrams without `title`** — diagram without title = screenshot without caption.

## Audience and abstraction

**Default high-level, business-friendly.** Audience is non-technical team and new joiners. Plain labels, simple relationships, no jargon.

- Full words: "Payment Service" not "PaySvc"
- System boundaries + data flow, not internals
- Arrow labels = business actions: "submits order", "sends notification"
- Skip method signatures, DB columns, class internals unless asked

**Detailed/technical only when asked** (class diagrams with methods, DB schemas, detailed state machines). When unsure, ask.

## Diagram type selection

| Scenario | Type | Why |
|----------|------|-----|
| System interaction over time | Sequence | Temporal order + message flow |
| High-level architecture / boundaries | Component | Parts + relationships, no time |
| Infra and deployment | Deployment | Physical/cloud nodes |
| Business process with decisions | Activity | Branches, parallel paths, swimlanes |
| Object relationships (technical) | Class | Inheritance, composition |
| Lifecycle of single entity | State | Transitions for one stateful object |
| Feature scope / user goals | Use Case | Actors + capabilities at glance |
| Brainstorm / knowledge | Mindmap | Non-linear, fast |
| Project timeline | Gantt | Schedule, milestones, critical path |
| Work breakdown | WBS | Hierarchical decomposition |
| Data relationships (technical) | ER | Entities, attributes, cardinality |

## Sequence diagrams

Most common type. Show component interaction over time.

### Participants

Declare top, in display order. Right stereotype per role:

```plantuml
@startuml
title Order Placement Flow

actor Customer as C
participant "Web App" as Web
participant "Order Service" as Orders
database "Order Database" as DB
queue "Event Bus" as Events

C -> Web: Places order
Web -> Orders: Create order request
Orders -> DB: Store order
Orders -> Events: Publish "Order Created"
Orders --> Web: Order confirmation
Web --> C: Display confirmation

@enduml
```

**Types:** `actor` (human), `participant` (service), `boundary` (API gateway), `control` (orchestrator), `entity` (domain object), `database` (store), `queue` (broker), `collections` (grouped).

### Arrows

| Syntax | Meaning |
|--------|---------|
| `->` | Sync request (solid, filled) |
| `-->` | Sync response (dashed, filled) |
| `->>` | Async message (solid, open) |
| `-->>` | Async response (dashed, open) |
| `->x` | Lost message |
| `<->` | Bidirectional |

### Activation

`activate`/`deactivate` or shorthand `++`/`--`:

```plantuml
Web -> Orders ++: Create order
Orders -> DB ++: INSERT order
DB --> Orders --: OK
Orders --> Web --: Order ID
```

### Grouping

```plantuml
alt Payment succeeds
    Orders -> Payments: Charge card
    Payments --> Orders: Success
else Payment fails
    Payments --> Orders: Declined
    Orders --> Web: Payment failed
end

opt Customer has loyalty account
    Orders -> Loyalty: Award points
end

loop For each item in cart
    Orders -> Inventory: Reserve stock
end

par Parallel notifications
    Orders ->> Email: Send confirmation
    Orders ->> SMS: Send text
end
```

### Notes, dividers, delays

```plantuml
note right of Orders: Validates inventory\nbefore charging
note over Web, Orders: All communication over HTTPS

== Fulfillment Phase ==

...Warehouse picks and packs order...

Shipping -> Customer: Delivery notification
```

## Component and deployment diagrams

High-level architecture. Boundaries + data flow, not internals.

### Component

```plantuml
@startuml
title E-Commerce Platform Overview

package "Frontend" {
    [Web Application] as Web
    [Mobile App] as Mobile
}

package "API Gateway" {
    [Gateway] as GW
}

package "Backend Services" {
    [Order Service] as Orders
    [Payment Service] as Payments
    [Inventory Service] as Inventory
}

package "Data Layer" {
    database "Orders DB" as ODB
    database "Products DB" as PDB
    queue "Event Bus" as Events
}

Web --> GW: REST/HTTPS
Mobile --> GW: REST/HTTPS
GW --> Orders
GW --> Payments
GW --> Inventory
Orders --> ODB
Inventory --> PDB
Orders --> Events: Publishes events
Payments --> Events: Publishes events

@enduml
```

### Deployment

```plantuml
@startuml
title Production Deployment

cloud "CDN" as cdn

node "AWS Region us-east-1" {
    node "EKS Cluster" {
        [API Gateway] as gw
        [Order Service] as orders
        [Payment Service] as payments
    }
    database "RDS PostgreSQL" as db
    queue "SQS" as sqs
}

cloud "Stripe" as stripe

cdn --> gw: HTTPS
gw --> orders
gw --> payments
orders --> db
orders --> sqs
payments --> stripe: Payment processing

@enduml
```

**Containers:** `node` (server/VM), `cloud` (external), `database` (store), `package` (logical group), `rectangle` (generic), `frame` (subsystem).

`interface` or `()` for ports:

```plantuml
() "REST API" as api
[Order Service] - api
```

## Activity diagrams

Business processes, workflows, decision flows. Swimlanes show responsibility.

```plantuml
@startuml
title Order Processing Workflow

start

:Customer submits order;

if (Payment valid?) then (yes)
    :Charge payment method;
    if (Inventory available?) then (yes)
        fork
            :Reserve inventory;
        fork again
            :Send confirmation email;
        end fork
        :Ship order;
    else (no)
        :Notify customer of backorder;
        :Add to waitlist;
    endif
else (no)
    :Reject order;
    :Notify customer;
    stop
endif

:Update order status to "Complete";

stop

@enduml
```

### Swimlanes

```plantuml
@startuml
title Support Ticket Resolution

|Customer|
start
:Submit support ticket;

|Support Agent|
:Review ticket;
if (Can resolve immediately?) then (yes)
    :Provide solution;
else (no)
    |Engineering|
    :Investigate issue;
    :Implement fix;
    |Support Agent|
    :Communicate resolution;
endif

|Customer|
:Confirm resolution;
stop

@enduml
```

**Syntax:** `start`/`stop`, `:action;`, `if (cond?) then (yes) else (no) endif`, `fork`/`fork again`/`end fork`, `|Swimlane|`, `floating note right: text`.

### Coloring with stereotypes

Highlight paths (desired/error/regen) via **stereotypes + skinparam**. Inline `#color` after `;` breaks activity diagrams.

```plantuml
@startuml
skinparam activity {
  BackgroundColor #F5F5F5
  BorderColor #333333
}

skinparam activity {
  BackgroundColor<<desired>> #E3F2E7
  BorderColor<<desired>> #7BAA87
  FontColor<<desired>> #000000

  BackgroundColor<<error>> #FDE2E2
  BorderColor<<error>> #C77C7C
  FontColor<<error>> #000000
}

title Example Flow

start
:Normal step;
:Desired step; <<desired>>
:Error step; <<error>>
stop

legend right
  |= Color |= Meaning |
  |<#E3F2E7>| Desired flow |
  |<#FDE2E2>| Error path |
endlegend
@enduml
```

**Rules:**
- Stereotype colors in `skinparam activity {}` block top
- Apply via `<<stereotype>>` after `;`
- Color legend table for meaning
- Common: `<<desired>>`, `<<error>>`, `<<regen>>`, `<<newgen>>`, `<<fallback>>`
- `elseif` always needs `then` — omitting breaks downstream

## Class diagrams

**Technical only.** Use when explicitly asked for technical/detailed showing object relationships, inheritance, data modeling.

### Relationships

| Syntax | Meaning | Use When |
|--------|---------|----------|
| `<\|--` | Inheritance | "is a" |
| `*--` | Composition | Part dies with whole |
| `o--` | Aggregation | Part lives independently |
| `-->` | Dependency | Uses temporarily |
| `--` | Association | General |
| `..\|>` | Implements | Realizes interface |

### Example

```plantuml
@startuml
title Domain Model

class Order {
    - id: UUID
    - status: OrderStatus
    - createdAt: DateTime
    + addItem(product: Product, qty: int)
    + calculateTotal(): Money
}

class OrderItem {
    - quantity: int
    - unitPrice: Money
}

class Product {
    - name: String
    - sku: String
    - price: Money
}

enum OrderStatus {
    PENDING
    CONFIRMED
    SHIPPED
    DELIVERED
    CANCELLED
}

Order *-- "1..*" OrderItem: contains
OrderItem --> Product: references
Order --> OrderStatus: has

@enduml
```

**Visibility:** `-` private, `+` public, `#` protected, `~` package.

**Stereotypes:** `<<interface>>`, `<<abstract>>`, `<<enum>>`, `<<service>>`, `<<entity>>`.

**Packages** group classes:

```plantuml
package "Orders Domain" {
    class Order
    class OrderItem
}
```

## State diagrams

Lifecycle of single entity — orders, tickets, accounts, deployments.

```plantuml
@startuml
title Order Lifecycle

[*] --> Pending: Order created

state Pending {
    [*] --> AwaitingPayment
    AwaitingPayment --> PaymentReceived: Payment confirmed
    AwaitingPayment --> [*]: Payment timeout
}

Pending --> Confirmed: Payment succeeds
Pending --> Cancelled: Payment fails

Confirmed --> Shipped: Carrier picks up
Shipped --> Delivered: Delivery confirmed
Shipped --> Returned: Customer returns

Delivered --> [*]
Cancelled --> [*]
Returned --> Refunded: Refund processed
Refunded --> [*]

@enduml
```

### Syntax

- `[*]` = initial/final pseudo-state
- `state Name { }` = composite/nested
- `state "Long Name" as alias` = alias
- `state fork_point <<fork>>` / `<<join>>` = concurrent fork/join
- `state choice_point <<choice>>` = decision

### Concurrent regions

```plantuml
state Processing {
    state "Verify Payment" as vp
    state "Check Inventory" as ci
    [*] --> vp
    [*] --> ci
    vp --> [*]
    ci --> [*]
    --
    state "Send Notification" as sn
    [*] --> sn
    sn --> [*]
}
```

## Other types

### Use case

Feature scope + actor interactions:

```plantuml
@startuml
title Customer Portal Features

left to right direction

actor Customer as C
actor "Support Agent" as SA

rectangle "Customer Portal" {
    usecase "View Orders" as UC1
    usecase "Track Shipment" as UC2
    usecase "Request Return" as UC3
    usecase "Chat with Support" as UC4
    usecase "Manage Returns" as UC5
}

C --> UC1
C --> UC2
C --> UC3
C --> UC4
SA --> UC4
SA --> UC5

@enduml
```

### Mindmap

Brainstorm / knowledge tree:

```plantuml
@startmindmap
title Project Architecture Decisions
* Architecture
** Frontend
*** React SPA
*** Server-Side Rendering
** Backend
*** Microservices
*** Monolith
** Data
*** PostgreSQL
*** Redis Cache
@endmindmap
```

### Gantt

Timeline + dependencies:

```plantuml
@startgantt
title Q1 Release Plan
project starts 2026-01-05

[Design Phase] lasts 10 days
[Backend Development] lasts 15 days
[Frontend Development] lasts 15 days
[Testing] lasts 10 days
[Deployment] lasts 3 days

[Backend Development] starts at [Design Phase]'s end
[Frontend Development] starts at [Design Phase]'s end
[Testing] starts at [Backend Development]'s end
[Deployment] starts at [Testing]'s end

[Design Phase] is colored in LightBlue
[Deployment] is colored in LightGreen

@endgantt
```

### WBS

Deliverable hierarchy:

```plantuml
@startwbs
title Product Launch
* Product Launch
** Research
*** User Interviews
*** Competitive Analysis
** Development
*** Backend API
*** Frontend UI
*** Mobile App
** Launch
*** Marketing Campaign
*** Documentation
*** Training
@endwbs
```

### ER (class syntax)

```plantuml
@startuml
title Database Schema

entity "users" {
    * id : UUID <<PK>>
    --
    * email : VARCHAR(255)
    * name : VARCHAR(100)
    created_at : TIMESTAMP
}

entity "orders" {
    * id : UUID <<PK>>
    --
    * user_id : UUID <<FK>>
    * status : VARCHAR(20)
    * total : DECIMAL(10,2)
    created_at : TIMESTAMP
}

users ||--o{ orders : places

@enduml
```

### JSON / YAML

```plantuml
@startjson
title API Response Structure
{
    "order": {
        "id": "abc-123",
        "status": "confirmed",
        "items": [
            {"product": "Widget", "qty": 2},
            {"product": "Gadget", "qty": 1}
        ]
    }
}
@endjson
```

## Styling

### `<style>` blocks (preferred)

CSS-like, replaces legacy `skinparam`. Place after `@startuml`:

```plantuml
@startuml
title Styled Sequence Diagram

<style>
    sequenceDiagram {
        actor {
            BackgroundColor #E8F5E9
            BorderColor #2E7D32
        }
        participant {
            BackgroundColor #E3F2FD
            BorderColor #1565C0
        }
        arrow {
            LineColor #333333
        }
        note {
            BackgroundColor #FFF9C4
            BorderColor #F9A825
        }
    }
</style>

actor Customer
participant "Order Service" as OS
...
@enduml
```

### Built-in themes

`!theme` applies one:

```plantuml
@startuml
!theme cerulean
title Themed Diagram
...
@enduml
```

Common: `cerulean`, `plain`, `sketchy-outline`, `aws-orange`, `mars`, `minty`. Preview before commit.

### Color formats

- Named: `Red`, `LightBlue`, `DarkGreen`
- Hex: `#FF5733`, `#2196F3`
- Gradient: `#White/#LightBlue` (top to bottom)

### Layout direction

Default top-to-bottom. Wide diagrams:

```plantuml
left to right direction
```

After `@startuml`, before any element.

## Preprocessing

### !procedure

Reusable fragments:

```plantuml
!procedure $service($name, $alias)
    participant "$name" as $alias
!endprocedure

$service("Order Service", OS)
$service("Payment Service", PS)
```

### !function

Reusable computed values:

```plantuml
!function $endpoint($service, $path)
    !return $service + " " + $path
!endfunction
```

### Variables

```plantuml
!$primary_color = "#1565C0"
!$secondary_color = "#2E7D32"
```

### Conditionals + loops

```plantuml
!if (%getenv("DETAIL_LEVEL") == "high")
    class Order {
        - id: UUID
        - status: OrderStatus
        + addItem(product: Product, qty: int)
    }
!else
    rectangle "Order Service"
!endif

!$i = 0
!while ($i < 3)
    node "Worker $i"
    !$i = $i + 1
!endwhile
```

## Anti-patterns

- **Overcrowded without grouping** — >15 ungrouped = unreadable. Split or group.
- **Tech jargon in business diagrams** — `POST /api/v2/orders` belongs in API docs. Use "Creates order".
- **Mixing styling approaches** — inline + `skinparam` + `<style>` in one file = conflicts. Pick one. Prefer `<style>`.
- **Deep nesting >3 levels in component diagrams** — tiny illegible boxes. Flatten or split.
- **Missing titles + legends** — useless in multi-diagram docs. `title` always, `legend` when relationships need explaining.
- **Class diagrams when simpler works** — `Order -> PaymentService` as class relationship when component or sequence says it clearer. Pick simplest type.
- **Copy-paste instead of `!include`** — duplicated participants drift. Extract shared defs.
- **Direction keywords everywhere** — sprinkling `-up->`, `-left->`, `-right->` fights layout engine, makes worse. Sparingly only.
- **Bare `autonumber`** — plain integers add noise. Format or omit.
- **Undeclared participants** — source-order render = unstable when adding messages.
