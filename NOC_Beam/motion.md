# Motion

NOC_Beam is a working tool. Animations exist to communicate state changes, not to decorate. Every motion in the product falls into one of four categories below; anything outside this menu needs explicit justification.

## Principles

1. **Fast by default.** 80–240ms is the working range. Anything longer interrupts the user; anything shorter doesn't read as motion.
2. **Ease out, almost always.** Things come to rest. `cubic-bezier(0.2, 0, 0, 1)` is the house curve.
3. **No motion when motion would lie.** SIP trace lines do not animate in — the wire didn't animate. The trace is a verbatim mirror.
4. **Honour `prefers-reduced-motion`.** Pulses become static dots; slide-ins become opacity-only fades; nothing exceeds 80ms.

## The four categories

### 1. Feedback (80ms)

Direct response to a user input. Used on hover, focus, press.

| What | Token | Curve | Properties |
| --- | --- | --- | --- |
| Hover tint | `--dur-fast` (80ms) | `--ease-out` | `background`, `color` |
| Focus ring | `--dur-fast` | `--ease-out` | `box-shadow` |
| Press | `--dur-fast` | `--ease-out` | `background`, `transform: scale(0.97)` — keypads only |

Hover/focus apply everywhere. **Press scale is reserved for tappable keypads** (the dialer's 1-9 keys). Don't shrink chrome — buttons in the title bar, rail buttons, list rows don't scale.

### 2. Transition (160ms)

Switching state inside a view. Tab change, segmented-control change, view-body content swap.

| What | Token | Curve | Properties |
| --- | --- | --- | --- |
| Tab/segment swap | `--dur-base` (160ms) | `--ease-out` | `opacity` (crossfade); content swaps at midpoint |
| Toggle switch knob | `--dur-fast` | `--ease-out` | `transform: translateX`, `background` |
| Slider knob | `--dur-fast` | `--ease-out` | `left`, `transform` |

### 3. Reveal (240ms)

Something arrives or departs. Drawer, toast, modal.

| What | Token | Curve | Properties | Notes |
| --- | --- | --- | --- | --- |
| Drawer slide | `--dur-slow` (240ms) | `--ease-out` | `transform: translateX(360px → 0)` | grid-template-columns also transitions |
| Toast slide-in | `--dur-slow` | `--ease-out` | `transform: translateY(20px → 0)`, `opacity 0 → 1` |
| Modal | `--dur-base` backdrop, `--dur-slow` dialog | `--ease-out` | backdrop `opacity`, dialog `transform: scale(0.96 → 1)` + `opacity` | dialog scale is the only non-feedback scale we allow |
| Menu / popover | `--dur-base` | `--ease-out` | `opacity`, `transform: translateY(-4px → 0)` |

### 4. Status (looping)

Indicates an ongoing live state. Used sparingly — at most one per view.

| What | Duration | Curve | Properties |
| --- | --- | --- | --- |
| `● LIVE` dot pulse | 1400ms loop | `ease-in-out` | `opacity 1 → 0.35 → 1` |
| Incoming-call ring | 1600ms loop, two rings 600ms offset | `ease-out` | `transform: scale(0.85 → 1.35)`, `opacity 0.6 → 0` |
| Blinking cursor (deck only) | 1050ms steps(2) | — | `opacity` |

## What does NOT animate

- **The trace.** New SIP messages append without enter animation. The trace is the wire; the wire doesn't fade.
- **Number/timer increments.** Call duration counters tick at 1Hz with no easing — they read as a clock.
- **Rail badges.** Count changes (e.g. unread → 3) are instant.
- **Account registration dot.** Goes green/red instantly when state changes.

## Reduced motion

`@media (prefers-reduced-motion: reduce)` rules:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 80ms !important;
  }
  .incoming-card .ring::before,
  .incoming-card .ring::after,
  .drawer-head .live .dot {
    animation: none;
    opacity: 1;
  }
}
```

The incoming-call ring is the only motion the user might *miss* under reduced motion — but the colour, label, and audible ringtone are sufficient signals.

## Tokens (from `colors_and_type.css`)

```
--dur-fast:    80ms
--dur-base:    160ms
--dur-slow:    240ms
--ease-out:    cubic-bezier(0.2, 0, 0, 1)
--ease-in:     cubic-bezier(0.4, 0, 1, 1)
```

If you need a curve outside `--ease-out`, push back on the requirement first. If you really need it, document the exception in the component file.
