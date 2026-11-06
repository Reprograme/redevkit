---
name: game-development
description: Game development principles and routing to platform, 2D/3D, design, network, art and audio refs. Use for game work.
---

# Game Development

> Core principles for every game, plus routing to the platform, dimension and specialty
> references. Persona: `game-developer`.

---

## When to Use This Skill

You are working on a game development project. This skill teaches the PRINCIPLES of game
development and directs you to the right reference based on context. When `{{CMD:redevkit-new}}`
sets up a game project, use these principles to propose constitution constraints (engine,
target FPS, platforms).

---

## Reference Routing

Read only the references that match the project. Combine a platform reference with a
dimension reference, then add specialty references as needed.

### Platform Selection

| If the game targets... | Read reference |
|------------------------|---------------|
| Web browsers (HTML5, WebGL) | [web-games](references/web-games.md) |
| Mobile (iOS, Android) | [mobile-games](references/mobile-games.md) |
| PC (Steam, Desktop) | [pc-games](references/pc-games.md) |
| VR/AR headsets | [vr-ar](references/vr-ar.md) |

### Dimension Selection

| If the game is... | Read reference |
|-------------------|---------------|
| 2D (sprites, tilemaps) | [2d-games](references/2d-games.md) |
| 3D (meshes, shaders) | [3d-games](references/3d-games.md) |

### Specialty Areas

| If you need... | Read reference |
|----------------|---------------|
| GDD, balancing, player psychology | [game-design](references/game-design.md) |
| Multiplayer, networking | [multiplayer](references/multiplayer.md) |
| Visual style, asset pipeline, animation | [game-art](references/game-art.md) |
| Sound design, music, adaptive audio | [game-audio](references/game-audio.md) |

---

## Core Principles (All Platforms)

### 1. The Game Loop

Every game, regardless of platform, follows this pattern:

```text
INPUT  → Read player actions
UPDATE → Process game logic (fixed timestep)
RENDER → Draw the frame (interpolated)
```

**Fixed Timestep Rule:**

- Physics/logic: Fixed rate (e.g., 50Hz)
- Rendering: As fast as possible
- Interpolate between states for smooth visuals

---

### 2. Pattern Selection Matrix

| Pattern | Use When | Example |
|---------|----------|---------|
| **State Machine** | 3-5 discrete states | Player: Idle→Walk→Jump |
| **Object Pooling** | Frequent spawn/destroy | Bullets, particles |
| **Observer/Events** | Cross-system communication | Health→UI updates |
| **ECS** | Thousands of similar entities | RTS units, particles |
| **Command** | Undo, replay, networking | Input recording |
| **Behavior Tree** | Complex AI decisions | Enemy AI |

**Decision Rule:** Start with State Machine. Add ECS only when performance demands.

---

### 3. Input Abstraction

Abstract input into ACTIONS, not raw keys:

```text
"jump"  → Space, Gamepad A, Touch tap
"move"  → WASD, Left stick, Virtual joystick
```

**Why:** Enables multi-platform, rebindable controls.

---

### 4. Performance Budget (60 FPS = 16.67ms)

| System | Budget |
|--------|--------|
| Input | 1ms |
| Physics | 3ms |
| AI | 2ms |
| Game Logic | 4ms |
| Rendering | 5ms |
| Buffer | 1.67ms |

**Optimization Priority:**

1. Algorithm (O(n²) → O(n log n))
2. Batching (reduce draw calls)
3. Pooling (avoid GC spikes)
4. LOD (detail by distance)
5. Culling (skip invisible)

---

### 5. AI Selection by Complexity

| AI Type | Complexity | Use When |
|---------|------------|----------|
| **FSM** | Simple | 3-5 states, predictable behavior |
| **Behavior Tree** | Medium | Modular, designer-friendly |
| **GOAP** | High | Emergent, planning-based |
| **Utility AI** | High | Scoring-based decisions |

---

### 6. Collision Strategy

| Type | Best For |
|------|----------|
| **AABB** | Rectangles, fast checks |
| **Circle** | Round objects, cheap |
| **Spatial Hash** | Many similar-sized objects |
| **Quadtree** | Large worlds, varying sizes |

---

## Anti-Patterns (Universal)

| Don't | Do |
|-------|-----|
| Update everything every frame | Use events, dirty flags |
| Create objects in hot loops | Object pooling |
| Cache nothing | Cache references |
| Optimize without profiling | Profile first |
| Mix input with logic | Abstract input layer |

---

## Routing Examples

### Example 1: "I want to make a browser-based 2D platformer"

→ Start with [web-games](references/web-games.md) for framework selection
→ Then [2d-games](references/2d-games.md) for sprite/tilemap patterns
→ Reference [game-design](references/game-design.md) for level design

### Example 2: "Mobile puzzle game for iOS and Android"

→ Start with [mobile-games](references/mobile-games.md) for touch input and stores
→ Use [game-design](references/game-design.md) for puzzle balancing

### Example 3: "Multiplayer VR shooter"

→ [vr-ar](references/vr-ar.md) for comfort and immersion
→ [3d-games](references/3d-games.md) for rendering
→ [multiplayer](references/multiplayer.md) for networking

---

> **Remember:** Great games come from iteration, not perfection. Prototype fast, then polish.
