# Quality Rubric — Visual Scoring 0-10

Use this rubric to evaluate playable ad screenshots. Score each category independently. Overall = average of all 5 categories.

## Atmosphere (0-10)
Depth and visual richness of the scene background.

| Score | What You See |
|-------|-------------|
| 1-3   | Solid color background. No depth. Flat, empty scene |
| 4-6   | Sky gradient present, but no clouds/particles. Static background |
| 7-8   | Gradient + parallax clouds (2+ layers). Shadows on objects |
| 9-10  | Multi-layer parallax (3+ layers), particles in air, dynamic shadows, living world feel |

## UI Polish (0-10)
Quality of non-game UI elements: progress bar, hints, buttons.

| Score | What You See |
|-------|-------------|
| 1-3   | Text and progress drawn on canvas. No CSS styling |
| 4-6   | HTML elements but no gradient/shadow. Basic flat styles |
| 7-8   | CSS gradient progress bar, box-shadow on buttons, readable fonts |
| 9-10  | Glossy progress bar (::before highlight), multi-layer shadows, CSS transitions on hover/active |

## Physics (0-10)
Realism of interactive objects and particles.

| Score | What You See |
|-------|-------------|
| 1-3   | Tool/object rigidly follows finger. No particles |
| 4-6   | Basic particles (no gravity). Tool follows with slight delay |
| 7-8   | Verlet physics (15+ segments), particles with gravity and fade |
| 9-10  | 20+ segments, adaptive damping, varied particle speed/size, secondary effects (drops, splashes) |

## Animations (0-10)
CSS and JS animations: transitions, victory sequence, CTA effects.

| Score | What You See |
|-------|-------------|
| 1-3   | Instant transitions. No CSS @keyframes |
| 4-6   | Basic fade-in/out. One or two @keyframes |
| 7-8   | Victory sequence with setTimeout chain. Pulse + shimmer on CTA. Smooth transitions |
| 9-10  | Choreographed victory (3+ stages), bounce with cubic-bezier, shimmer + pulse + appear on CTA, every UI element animated |

## Completeness (0-10)
All game states work, all assets visible, no broken elements.

| Score | What You See |
|-------|-------------|
| 1-3   | Missing assets, placeholders visible. Not all states work |
| 4-6   | All assets present, but some states broken (victory doesn't trigger) |
| 7-8   | All states work. MRAID integrated. Touch handling correct |
| 9-10  | All states + edge cases (double tap, resize). Platform detection. Perfect state navigation |

## How to Use

1. Score each category independently based on what you SEE in the screenshots
2. Be specific about what's missing — "no clouds" is better than "low atmosphere"
3. Priority = categories with lowest scores first (biggest impact)
4. One improvement per iteration — don't try to fix everything at once
5. Overall = (atmosphere + ui + physics + animations + completeness) / 5
