# Pre-v0.9.4 Design Directions — Three Options for User Review

**Date:** 2026-08-01
**Scope:** design exploration only. No direction is approved; nothing is implemented.

This document reconciles the current Pixel Art system (see
`PRE_V0.9.4_UI_UX_AUDIT.md`) with ui-ux-pro-max evidence
(`verification/design/pre-v0.9.4/uiuxpro-results/`) and proposes exactly three
coherent directions.

## 0. Conflict analysis (feeds all three directions)

### Claymorphism vs Pixel Art

Claymorphism (ui-ux-pro-max's top design-system hit for "education learning
SaaS") relies on rounded surfaces, soft shadows, floating depth, gradients,
and playful motion — every one of which Pixel Art forbids. The skill output is
therefore **not adoptable as a surface treatment**. What can be translated
without violating Pixel Art:

- friendly color hierarchy (warm, inviting but solid colors);
- generous spacing around tasks;
- approachable illustration (pixel-style mascots/icons instead of clay blobs);
- clear task progression (step indicators, progress bars in pixel style).

### Swiss Modernism vs Pixel Art

Swiss Modernism 2.0 (grid, Helvetica/Inter, mathematical spacing, high contrast,
single accent) is the most compatible external system: hard edges, sharp
typography hierarchy, and reduced decoration align with Pixel Art's square
corners and hard shadows. The friction points:

- "single vibrant accent only" conflicts with the four-accent semantic status
  palette. Resolution: keep status semantics (red/green/blue/yellow) as semantic
  tokens; designate one brand accent for primary actions.
- Swiss favors sans-serif reading type; Pixel Art mandates monospace. Resolution:
  allow a readable sans for body/reading content while keeping monospace for
  data, code-like identifiers, and pixel headings.

### Student vs Research visual language

Both roles should share design tokens, typography scale, status semantics,
accessibility rules, icon language, and responsive foundations, but differ in:

| Dimension | Student View | Research View |
|---|---|---|
| Density | spacious, one task at a time | denser, information-rich |
| Emphasis | next action, feedback, encouragement | evidence, audit, comparability |
| Layout | single column, large type, generous cards | grid, compact tables, side-by-side |
| Terminology | plain language (hidden IDs) | technical records exposed |
| Navigation | same sidebar, student pages | same sidebar, research pages |
| Visualization | simple pixel progress/illustrations | tabular/quantitative displays |

## 1. Direction A — Refined Pixel Art

**Design thesis:** keep the current identity intact; fix the craft. All audit
findings are resolved inside the existing constraint set: square corners, hard
shadows, solid colors, immediate states.

**Intended impression:** "the same distinctive product, but finished" — crisp,
consistent, accessible, and dense where it needs to be.

**Student View treatment:** current single-column layout refined with a strict
8px spacing scale, larger section rhythm, readable monospace tuning, and pixel
icons next to nav and buttons.

**Research View treatment:** replace `st.json` blobs with pixel tables
(px-table-wrap) and metric cards; keep the same tokens; add dense compact
variants of cards/table rows for Research only.

**Global navigation:** same sidebar; add icons to language/role/page options;
group pages visually; keep the hamburger on mobile but shorten the stack.

**Typography proposal:** keep monospace everywhere; adjust scale
(body 15–16px, 1.6–1.7 line-height; h2 28px; h3 20px; data 13px tabular).

**Color proposal:** keep the canonical palette; darken primary red to
`#d4003f` (white-on-red >=4.5:1) and disabled text to `#5a5a68`; keep status
semantics unchanged.

**Spacing scale:** 4/8/12/16/24/32/48; card padding 16; section gap 32.

**Border treatment:** unchanged (4px desktop / 2px mobile / 1px table hairlines).

**Shadow treatment:** unchanged hard offsets; reduce to 2px on dense research
rows.

**Icon system:** one SVG pixel-style family (outline glyphs, square caps),
used in sidebar, buttons, notices, and empty states; no emoji.

**Button hierarchy:** primary red (AA), secondary surface, destructive dark;
add loading spinners inside buttons (pixel-style, no animation beyond a 2-frame
blink guarded by reduced-motion).

**Form treatment:** keep square inputs; add helper text and inline validation
for required fields (writing prompt, essay text); 44px minimum touch height.

**Card/panel:** unchanged; interactive cards keep immediate hover movement.

**Table treatment:** px-table-wrap everywhere research data is displayed;
sticky header row, zebra rows, horizontal scroll inside the bordered container.

**Feedback treatment:** keep priority cards; larger evidence quotes with clear
quotation marks; add an explicit "Next step" call-to-action card.

**Evidence treatment:** quoted evidence with source line references in a
separate caption; never raw JSON in Student.

**Timeline treatment:** keep pixel timeline; add connecting vertical rule and
timestamps aligned to a grid.

**Empty-state treatment:** keep px-empty; add an action button inside the empty
state (ui-ux-pro-max: "Show helpful message and action").

**Loading/error:** spinner inside triggered buttons; errors keep the localized
role-split presentation; add inline field errors on the Writing form.

**Mobile:** hamburger sidebar with grouped sections; all controls >=44px;
tab bar internal scroll kept.

**Accessibility consequences:** fixes the two failing contrast pairs, touch
targets, and form validation; keeps focus ring and reduced-motion behavior.

**Streamlit feasibility:** high — CSS token changes in `pixel_art.py`,
component-level changes in `components.py`; no architecture change.

**Compatibility:** 100% with current Pixel Art rules; no behavior change.

**Estimated migration scope:** small-medium (tokens, component polish,
research table rendering, form validation UI).

**Major risks:** refinement may still feel "retro" to some users; raw JSON
replacement touches several research pages.

**Advantages:** lowest risk; keeps brand; directly fixes measured defects.

**Disadvantages:** does not address readability research suggesting sans body
type; visual distinctiveness unchanged (already distinctive).

Wireframe sketch (Research Data, proposed):

```text
+------------------------------------------------------------------+
| Research Data                                      [Export Run]  |
+------------------------------------------------------------------+
| [Export Preview] [Privacy Mode] [Filters] [PII] ...              |
+------------------------------------------------------------------+
| Export History (table, dense)                                    |
| EXP000001 2026-08-01  jsonl+csv  completed  [manifest]           |
| EXP000002 2026-08-01  jsonl      completed  [manifest]           |
+------------------------------------------------------------------+
```

## 2. Direction B — Hybrid Pixel System 2.0 (recommended candidate)

**Design thesis:** two role-tuned languages over one token system. Student View
becomes educational, approachable, spacious, task-focused — playful through
color and pixel illustration, never through rounded/soft surfaces. Research
View becomes Swiss-Modernism-inspired: grid-based, denser, analytical, with
restrained Pixel Art accents. Both share design tokens, status semantics,
accessibility rules, icon language, and responsive foundations.

**Intended impression:** "a friendly studio for learners, a precise
instrument for researchers — clearly the same product."

**Student View treatment:** single-column, max-width ~720px content column,
generous 24–48px section gaps, readable sans body (Atkinson Hyperlegible for
feedback/instructions), monospace only for IDs/codes, pixel headings retained,
friendly pixel illustrations in empty states, explicit next-step cards.

**Research View treatment:** 12-column grid, dense compact cards/table rows,
tabular data displays, Swiss-style section numbers or labels, high contrast,
one brand accent (blue) for actions, status colors kept semantic; Pixel Art
accents limited to headers, badges, and focus outlines.

**Global navigation:** same sidebar; icons + labels; role switcher restyled as
two clear modes; mobile bottom-sheet style not required — keep hamburger with
grouped sections.

**Typography proposal:** body Inter or Atkinson Hyperlegible 16px/1.6
(Student) and 14px/1.5 (Research); headings keep a pixel/mono accent for the
page header; data/labels monospace tabular.

**Color proposal:** shared tokens: dark `#1a1c2c`, white, surface `#f4f4f4`,
semantic status red/green/blue/yellow (red darkened for AA); Student gets warm
accent (yellow/amber) for encouragement; Research gets blue accent for actions;
both from one token set with role-scoped semantics.

**Spacing scale:** shared 4/8/12/16/24/32/48; Student uses 24–48 section
rhythm; Research uses 8–16 dense rhythm.

**Border treatment:** shared square borders (4px/2px/1px); Research rows may
use 1px hairlines inside bordered containers.

**Shadow treatment:** hard offsets only; Research uses smaller offsets (2px)
for density.

**Icon system:** one SVG family (square-corner pixel style, 2px strokes) shared
by both roles; icons on nav, buttons, notices, table headers.

**Button hierarchy:** shared semantics; primary Student = red, primary
Research = blue; destructive = dark; all >=44px on mobile, with loading state.

**Form treatment:** shared square inputs; inline validation; helper text;
44px touch height; Student forms single-column, Research forms inline/compact.

**Card/panel:** Student keeps px-cards (generous); Research uses flat bordered
panels with hairline dividers (no nested cards).

**Table treatment:** shared px-table-wrap; Research default density (13px,
4px cell padding), Student tables (if any) 14px, 8px padding.

**Feedback treatment:** Student: readable sans cards, quote + explanation +
revision guidance + practice link + next step. Research: same evidence in
compact table/audit form.

**Evidence treatment:** quotes in both roles; Student shows plain quotes with
source captions; Research shows quote + evidence IDs + confidence in table rows.

**Timeline treatment:** Student: spacious pixel timeline with illustration
markers; Research: same events as a compact chronological table.

**Empty-state treatment:** Student: illustration + message + action;
Research: message + action, no illustration.

**Loading/error:** shared spinner-in-button; errors localized and
role-split (existing model kept).

**Mobile:** Student single column; Research cards stack, tables scroll
horizontally inside containers; touch targets >=44px; tab bar internal scroll.

**Accessibility consequences:** AA contrast (darkened red), 44px targets,
readable sans for long text, preserved focus ring and reduced-motion.

**Streamlit feasibility:** high — token/component-layer work; role-scoped
theme via a `st.markdown` CSS scope per role or conditional class; no backend
changes.

**Compatibility:** keeps Pixel Art rules for Student identity; relaxes
monospace-body and single-accent rules in a controlled, documented way.

**Estimated migration scope:** medium (tokens + two component variants +
research page re-renders + form/validation UI).

**Major risks:** two visual languages can drift; needs a strict shared token
contract and an audit script; CSS scope per role adds complexity.

**Advantages:** addresses the two biggest measured problems (readability and
research scanability) while preserving brand distinctiveness; matches
ui-ux-pro-max product guidance (approachable learning UI + analytical
Swiss-style research UI); highest long-term product suitability.

**Disadvantages:** more work than A; the two-language system must be governed
carefully; slightly more CSS surface than a single system.

Wireframe sketch (Student Writing, proposed):

```text
------------------------------------------------------------------
 Home  Writing  Feedback  Revision  Practice  Journey   [EN|中文]
------------------------------------------------------------------
 Writing
 Student ID  [S02________]
 Task relationship  (o) New task  ( ) Revision
 Task information
   Writing prompt  [Should cities add more parks?_________]
   Genre           [argumentative essay        v]
 Essay text
 [ .................................................. ]
 [ .................................................. ]
 [ Submit and generate feedback                  ]
   (validates prompt + text inline before submit)
------------------------------------------------------------------
```

## 3. Direction C — Full Professional Redesign

**Design thesis:** replace the Pixel Art identity with a conventional
educational SaaS design system (rounded corners, soft shadows, sans-serif,
standard professional dashboard).

**Intended impression:** "a familiar, modern, professional product" — lowest
visual risk, highest visual sameness.

**Student View treatment:** standard SaaS learning dashboard: rounded cards,
soft shadows, Inter/Atkinson type, blue primary, friendly illustrations.

**Research View treatment:** standard admin/dashboard: sidebar + top bar,
dense tables, charts, filterable panels.

**Global navigation:** conventional left sidebar with icons, active state
pill, top bar for locale/role.

**Typography:** Inter or Atkinson Hyperlegible throughout (ui-ux-pro-max
typography matches: Academic/Research or Accessibility First).

**Color:** professional palette (ui-ux-pro-max LMS teal `#0D9488` or Academic
navy `#1E3A5F` + gold) with standard semantic tokens.

**Spacing/border/shadow:** standard 8px scale, 8–12px radius, soft shadows,
150–200ms transitions (reduced-motion guarded).

**Icons:** standard SVG family (Lucide/Phosphor).

**Buttons/forms/cards/tables/feedback/evidence/timeline/empty/loading/error:**
standard SaaS patterns; essentially the ui-ux-pro-max design system applied
as-is.

**Mobile:** standard responsive dashboard with bottom nav option.

**Accessibility consequences:** likely AA if tokens chosen carefully; standard
patterns make a11y easier; risk of introducing unverified contrast pairs.

**Streamlit feasibility:** medium — Streamlit components have their own
styling; a full conventional redesign fights the framework more than pixel CSS
does (rounded corners require overriding `border-radius: 0 !important`
globals).

**Compatibility:** low — replaces the Pixel Art system, invalidates
`docs/UI_DESIGN.md`, `PIXEL_ART_DESIGN_SYSTEM.md`, token references, and the
pixel verification scripts; every component changes.

**Estimated migration scope:** large (all components, all pages, tokens,
docs, verification, screenshots).

**Major risks:** total loss of the distinctive identity built and verified in
v0.9.2; generic look; large regression surface; contradicts the project's
documented brand decision without a human product decision.

**Advantages:** familiarity; conventional patterns; easiest to hand off to
standard UI frameworks later.

**Disadvantages:** destroys the current brand equity; highest migration cost;
unnecessary for the measured problems (contrast, touch, type, tables can all
be fixed inside A or B).

## 4. Summary comparison

| | A Refined Pixel Art | B Hybrid Pixel 2.0 | C Full Redesign |
|---|---|---|---|
| Brand preservation | High | High | Low |
| Readability fix | Partial (mono kept) | Full (sans body) | Full |
| Research scanability | Good (tables) | Best (dense grid+table) | Good |
| Migration effort | Small | Medium | Large |
| Risk | Low | Medium | High |
| Distinctiveness | Kept | Kept + role-tuned | Lost |
| Streamlit fit | Native | Native | Fights framework |

Detailed scoring and the recommendation are in `PRE_V0.9.4_DECISION_MATRIX.md`.
