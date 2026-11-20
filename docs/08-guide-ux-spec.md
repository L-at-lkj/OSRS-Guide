# 08: Interactive guide UX spec (templates/guide.html)

**One self-contained HTML file per guide.** It works offline (fonts fall back to Georgia), on a phone, and in print.

## Always visible
- A **NOT RELEASED** banner unless QA approved this exact content hash.
- A Hardcore Worlds chip, a "facts verified" date and a "game updates checked to" date.
- A sticky control bar: **route** (Safest / Balanced / Fastest), **danger cap** (Cautious 24 / Standard 44 / Bold 64), **my level or XP**, hide-done, theme.
- Tiles: total time, time left (from your XP), actions, worst residual danger, steps above your cap, progress.
- A **route timeline bar**: each segment's width is its share of the XP, its colour is its residual danger tier, and a marker shows your position.

## Tabs
1. **Route**: step cards. Each card has: levels, method and location; a danger badge (residual, with raw in small text); stats (XP/action, XP/h, actions, time, supplies, bonus XP); requirements ✔/✖ against your profile; instructions; warnings; tips; a "New in the last 12 months" ribbon; an "above your cap" ribbon; a collapsible **danger assessment** (HW death rule, flags, 8 factor bars raw→residual with rationale and fact links, mitigations, pre-start checklist, stop conditions, bail-out plan); and the why-this-step and why-not-faster notes.
2. **Level by level**: every level with total XP, XP to next, actions to next, time to next, method, danger and elapsed time. Your current level is highlighted.
3. **Quests & unlocks**: rewards, requirements, death rule and bail-out. Recent quests are marked NEW.
4. **Danger register**: how scoring works, the tier legend, every step ranked by residual DS, and the red-team findings and resolutions.
5. **What's new**: the Patch Sentinel's relevant updates in the window, plus upcoming content.
6. **Supplies**: totals for the selected route, bonus XP, assumptions.
7. **Sources**: every fact with its status, caveat and revision-pinned links. Fact chips anywhere in the guide jump here.
8. **Audit trail**: release status, integrity cross-check, per-agent activity, provenance per artifact, and the full ledger with hashes.

## Behaviour
- Progress (done steps, route, cap, XP, tab, theme) is saved per guide and content hash in localStorage. If storage is blocked, the page still works.
- Token resolution: `{{step.actions}}` and similar tokens resolve against the selected route's calculations, so the prose always matches the numbers.
- Accessibility: semantic buttons, keyboard-reachable controls, colour plus text for every danger tier, and no meaning carried by colour alone.
- Design: parchment and stone with gold accents and Cinzel headings. No Jagex art or logos. Not affiliated with Jagex.

## Tests
`node tools/browser_check.mjs <guide.html> --shots <dir>`: no script errors; every tab renders; route switching works; the level input highlights a row; progress persists; no horizontal scroll at 390px.
