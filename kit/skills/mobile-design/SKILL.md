---
name: mobile-design
description: Mobile UX and performance rules for iOS, Android, React Native and Flutter; use before building any mobile app screen.
---

# Mobile Design System

> **Philosophy:** Touch-first. Battery-conscious. Platform-respectful. Offline-capable.
> **Core principle:** Mobile is NOT a small desktop. Think mobile constraints, ask the
> platform choice. Not for responsive web pages (use `{{SKILL:frontend-design}}`).

## 1. Read Before Working

Do not start development until you have read the files relevant to the task.

### Always

| File | Content |
| --- | --- |
| [mobile-design-thinking](references/mobile-design-thinking.md) | **Read first.** Forces context-based thinking instead of memorized defaults |
| [touch-psychology](references/touch-psychology.md) | Fitts' Law, gestures, haptics, thumb zone |
| [mobile-performance](references/mobile-performance.md) | React Native / Flutter performance, 60 fps, memory |
| [mobile-backend](references/mobile-backend.md) | Push notifications, offline sync, mobile APIs |
| [mobile-testing](references/mobile-testing.md) | Testing pyramid, E2E, platform-specific tests |
| [mobile-debugging](references/mobile-debugging.md) | Native vs JS debugging, DevTools, Logcat |

### As needed

| File | Content |
| --- | --- |
| [mobile-navigation](references/mobile-navigation.md) | Tab / stack / drawer, deep linking |
| [mobile-typography](references/mobile-typography.md) | System fonts, Dynamic Type, accessibility |
| [mobile-color-system](references/mobile-color-system.md) | OLED, dark mode, battery-aware color |
| [decision-trees](references/decision-trees.md) | Framework, state and storage selection |
| [quick-reference](references/quick-reference.md) | Platform matrix, thumb zone, RN/Flutter snippets, framework tree |

### Per platform

| Target | Read |
| --- | --- |
| iOS | [platform-ios](references/platform-ios.md) (HIG, SF Pro, SwiftUI) first |
| Android | [platform-android](references/platform-android.md) (Material Design 3, Roboto, Compose) first |
| Cross-platform (React Native, Flutter) | Both, and apply platform-conditional logic |

## 2. Ask Before Assuming

If the request is open-ended, do not default to your favorites. When these are not specified
(in the request, `spec.md`, `DESIGN.md` or `.redevkit/memory/tech.md`), follow the shared
question protocol (as a subagent, return the question to the caller):

| Aspect | Ask | Why |
| --- | --- | --- |
| **Platform** | iOS, Android, or both? | Affects every design decision |
| **Framework** | React Native, Flutter, or native? | Determines patterns and tools |
| **Navigation** | Tab bar, drawer, or stack-based? | Core UX decision |
| **State** | Zustand / Redux / Riverpod / BLoC? | Architecture foundation |
| **Offline** | Must it work offline? | Data strategy |
| **Target devices** | Phone only, or tablets too? | Layout complexity |

## 3. Banned Anti-Patterns

### Performance

| ❌ Never | Why it's wrong | ✅ Always |
| --- | --- | --- |
| `ScrollView` for long lists | Renders all items, memory explodes | `FlatList` / `FlashList` / `ListView.builder` |
| Inline `renderItem` function | New function every render | `useCallback` + `React.memo` |
| Missing `keyExtractor` / index keys | Bugs on reorder | Stable unique ID from data |
| Skipping `getItemLayout` | Janky scroll | Provide it for fixed-height items |
| `setState()` everywhere (Flutter) | Unneeded rebuilds | Targeted state, `const` constructors |
| `useNativeDriver: false` | Animations blocked by the JS thread | `useNativeDriver: true` where supported |
| `console.log` in production | Slows the JS thread | Strip it from release builds |
| No `React.memo` / `const` | Every item re-renders | Memoize list items |

### Touch and UX

| ❌ Never | Why it's wrong | ✅ Always |
| --- | --- | --- |
| Touch target < 44 pt / 48 dp | Hard to tap | 44 pt (iOS) / 48 dp (Android) minimum |
| < 8 px between targets | Accidental taps | 8-12 px gap |
| Gesture-only interactions | Excludes motor-impaired users | Visible button alternative |
| No loading state | User thinks the app crashed | Always show loading feedback |
| No error state | No recovery path | Error message with retry |
| No offline handling | Crash or block without network | Graceful degradation, cached data |
| Ignoring platform conventions | Breaks muscle memory | iOS feels iOS, Android feels Android |

### Security

| ❌ Never | Why it's wrong | ✅ Always |
| --- | --- | --- |
| Tokens in `AsyncStorage` | Readable on rooted devices | `SecureStore` / Keychain / `EncryptedSharedPreferences` |
| Hard-coded API keys | Extracted from the APK/IPA | Server-side secrets, short-lived tokens |
| No certificate pinning for sensitive APIs | MITM possible | Pin certificates in production |
| Logging sensitive data | Logs can be extracted | Never log tokens, passwords, PII |

### Architecture

| ❌ Never | Why it's wrong | ✅ Always |
| --- | --- | --- |
| Business logic in UI | Untestable | Service layer |
| Global state for everything | Re-renders, complexity | Local state first, lift when needed |
| Deep linking as an afterthought | Notifications and shares break | Plan deep links from day one |
| Skipping dispose/cleanup | Leaks, zombie listeners | Clean up subscriptions and timers |

## 4. Checkpoint (before writing mobile code)

```text
CHECKPOINT
Platform:   [ iOS / Android / Both ]
Framework:  [ React Native / Flutter / SwiftUI / Kotlin ]
Files read: [ list the reference files you read ]

3 principles I will apply:
1. ...
2. ...
3. ...

Anti-patterns I will avoid:
1. ...
2. ...
```

Example: "Platform: iOS + Android. Framework: React Native + Expo. Files read:
touch-psychology, mobile-performance, platform-ios, platform-android. Principles: FlatList
with `React.memo` + `useCallback`; 48 dp targets with primary CTAs in the thumb zone;
platform-specific back navigation. Avoid: ScrollView lists, inline `renderItem`, tokens in
AsyncStorage."

If you cannot fill the checkpoint, go back and read the reference files.

## 5. Automated Audit

In the verify command's audit step (not during implementation), when its orchestrator did not already run it, run `.redevkit/audits/mobile_audit.py <project_path>` (add `--json` for machine output) with
the Python interpreter detected per `.redevkit/audits/README.md`. It checks touch targets,
list performance patterns, animation drivers, cleanup, `console.log` and navigation rules.
Without Python, record `SKIPPED (no Python)` and walk the checklists below by hand, plus the
project's lint and test commands.

## 6. Checklists

### Before starting a mobile project

- [ ] Platform confirmed (iOS / Android / both)
- [ ] Framework chosen (React Native / Flutter / native)
- [ ] Navigation pattern decided (tabs / stack / drawer)
- [ ] State management selected
- [ ] Offline requirements known
- [ ] Deep linking planned from day one
- [ ] Target devices defined (phone / tablet / both)

### Before every screen

- [ ] Touch targets >= 44 pt / 48 dp
- [ ] Primary CTA in the thumb zone
- [ ] Loading state exists
- [ ] Error state with retry exists
- [ ] Offline handling considered
- [ ] Platform conventions followed

### Before release

- [ ] `console.log` removed
- [ ] Secure storage for sensitive data
- [ ] Certificate pinning where required
- [ ] Lists optimized (memo, stable keys)
- [ ] Cleanup on unmount
- [ ] Tested on low-end devices
- [ ] Accessibility labels on all interactive elements

> **Remember:** mobile users are impatient, interrupted and using imprecise fingers on small
> screens. Design for the worst conditions: bad network, one hand, bright sun, low battery.
