# v0.9.7-D Design Consultation B — Rendered Screenshot Critique (R1)

**Role:** senior product designer, design consultation B (screenshot critique of the first implementation)
**Date:** 2026-08-05 · **Run:** `v0.9.7-d-20260805-r1`
**Inputs read in full:** `docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md` (Status: APPROVED DRAFT — pending representative-page validation).
**Screenshots reviewed:** `en_1280x900_journey_design_system.png`, `zh_1280x900_journey_design_system.png`, `en_390x844_journey_design_system.png`, `zh_390x844_journey_design_system.png` (after); `verification/v0.9.7-c/v0.9.7-c-wu4-20260805-r1/screenshots/en_1280x900_journey_grouped.png` (before, v0.9.7-C).
**Corroborating read-only inspection:** `rendered_page_matrix_evidence.json`, `d1_browser_matrix.py`, `app/ui/pixel_art.py` (`DESIGN_TOKENS`, `PIXEL_CSS`, `PIXEL_COMPONENT_CSS`), `app/ui/components.py`, `app/ui/features/student/journey.py`, `locales/en.json`, `locales/zh_CN.json`. No production code, tests, or locales were modified; no git commands were run.
**Method:** UI/UX Pro Max rule categories (accessibility, interaction, layout/responsive, typography/color, navigation, professional-UI checks) applied to the renders; every visual claim below is backed by pixel-level measurement of the captures (exact colors and border widths, see §4) cross-checked against the token contracts.

---

## 1. Summary verdict

**Fix-before-freeze: the direction is right, the first implementation does not yet render the approved system.** The calm-ledger intent is already palpable against v0.9.7-C — the purpose block and learner block shed their heavy boxes, headings and the sidebar are sans in both scripts, and the quiet state vocabulary is reaching the DOM (`data-state`, tint fills, icon + label badges). But the representative-page validation has done exactly what it exists to do: it surfaced two systemic CSS defects that silently drop the design system's signature recipes — every `border: var(--px-border-*) solid var(--color)` composite is invalid CSS and is discarded (no 4px `--px-status-accent-*` accent bars on notices, no `--px-border-subtle` hairlines, borderless badges), and the global `.stApp span/div` text rule outranks the state classes so no `--px-status-on-*` label color ever renders (measured: the success badge text is ink `#1a1c2c`, not `#14532d`). On top of that, the Journey loading box is wired as a permanent element and sits above the fully loaded cycle card (visible in the zh desktop capture), and the evidence set itself cannot support a freeze decision: the 390px captures show the Streamlit sidebar overlay open with only a ~100px slice of content visible, and no capture shows anything below the fold — the cycle card body, all six stage items, the practice panel, the action rows, the next-step primary CTA, and the limitation notice have zero visual evidence. All four blockers are repairable inside the constraints: KB-01/KB-02/KB-07 are CSS-only in the shared token/component layer, KB-03 is presentation-only (no wording, ordering, grouping, or persistence change), and KB-04 is verification-harness-only. Recommendation: repair KB-01..KB-04, apply the high-value quieting passes KB-05..KB-08, re-capture with the corrected matrix (sidebar-collapsed mobile, full-scroll desktop, settled state), and only then move the design system from APPROVED DRAFT to FROZEN at D1.3.

---

## 2. Findings

### KB-01 — BLOCKING — Invalid CSS border composites silently delete the quiet state geometry

- **Aspect:** status legibility · aesthetic distinctiveness · design-system reuse potential
- **Screenshot/state:** `en_1280x900` (no rule under the "Learning Journey" page heading; learner context block renders with no border); `zh_1280x900` ("已完成" badge renders borderless); all four captures affected.
- **Component/token:** `PIXEL_COMPONENT_CSS` rules `.px-page-heading`, `.px-section-heading`, `.px-student-context` (border + row hairlines), `.px-status-badge`, `.px-notice-warning/-error/-success/-info` (4px accent bars), `.px-notice-dashed`, `.px-cycle-head`, `.px-stage-item` (+`[data-active="true"]`), `.px-empty`. Root cause: `--px-border-thick/thin/hairline` already embed `solid #1a1c2c`, so appending `solid var(--px-border-subtle)` / `solid var(--px-status-accent-*)` makes every composite declaration invalid; browsers drop it.
- **Recommended change:** emit width-only geometry companions from the same `DESIGN_TOKENS` geometry entries (e.g. `--px-border-thick-width: 4px`) and compose longhands — `border-left: var(--px-border-thick-width) solid var(--px-status-accent-warning)`; `border: var(--px-border-hairline-width) solid var(--px-border-subtle)`. Single token source preserved (§12); no literal values in components.
- **Reason:** the discarded declarations are the design system's signature: the 4px state accent bar (§3, §5, §6), the 1px accent border on badges (§9), the section-header and cycle-head hairlines (§9), the dashed `--px-status-accent-neutral` treatment for unavailable/legacy (§3), and the empty-state dashed border (§6) all currently render as either nothing or a fallback uniform ink border. Measured confirmation: no 4px rule under the page heading (rows scanned), no border pixels around the badge tint bbox (pure white on all four sides), no border on the learner block.
- **Expected benefit:** the approved quiet-tint + accent-bar + icon + label recipe actually appears; §14's "state borders ≥ 3:1" becomes true; one shared-layer fix propagates to all six Student pages at once.

### KB-02 — BLOCKING — Specificity inversion: `--px-status-on-*` label colors never render

- **Aspect:** color semantics · status legibility · typography
- **Screenshot/state:** `zh_1280x900` — the cycle-head success badge "✓ 已完成" measures ink `#1a1c2c` glyphs on the correct `#e6f6ec` tint; designed value is `--px-status-on-success` `#14532d`.
- **Component/token:** `PIXEL_CSS` global text rule `.stApp p, …, .stApp span:not([data-testid="stIconMaterial"]), .stApp div, .stApp a { color: var(--px-text) }` (specificity 0,2,1 for spans / 0,1,1 for divs) outranks `.px-status-badge[data-state="success"]` (0,2,0) and `.px-notice-warning` etc. (0,1,0). Tokens affected: `--px-status-on-success/-warning/-error/-info/-neutral`.
- **Recommended change:** raise the state rules above the global rule, e.g. scope them as `.stApp .px-status-badge[data-state="success"] { color: var(--px-status-on-success) }` / `.stApp .px-notice-warning { color: var(--px-status-on-warning) }`, or exclude `.px-*` components from the global color declaration. While touching this cascade, re-audit `.px-field-error` (it sets `color: var(--px-status-error)` — the *tint* `#fdeaef` on white — and is currently saved from invisibility only by this same accident).
- **Reason:** the §3 contract table (7.53:1 / 8.14:1 / 7.99:1 / 6.78:1 / 7.92:1 measured pairs) is not what renders; every state surface falls back to ink text, so state differentiation currently rests on tint + icon alone with the accent bar already missing (KB-01).
- **Expected benefit:** the documented tonal label colors appear, restoring the intended quiet-but-readable state voices and the measured AA pairs; status families become distinguishable at a glance in both locales.

### KB-03 — BLOCKING — Loading state is permanent and co-visible with loaded content

- **Aspect:** status legibility · cycle separation · information density
- **Screenshot/state:** `zh_1280x900` — "正在加载学习旅程……" (`.px-loading`) renders immediately above the fully populated "写作循环 cycle-37" card; `en_1280x900` — "Loading learning journey?" occupies the fold while content exists beneath it. DOM confirms both states coexist (evidence JSON: `cycle_cards: 1`, `stage_items: 6` in the same render).
- **Component/token:** `loading_box` / `.px-loading`; call site `render_learning_journey_page` renders it unconditionally before `api_client.get_journey(...)` and nothing clears it.
- **Recommended change:** render the loading box into a placeholder (e.g. `st.empty()`) that is emptied once the read resolves (or render it only while the request is in flight); extend the browser matrix to assert `[data-testid="px-loading"]` is absent in the settled state. Presentation-only: no wording, grouping, ordering, state-vocabulary, navigation, or persistence change. (The stray "?" in the EN string is the deferred O1 copy item — see KB-13, not this fix.)
- **Reason:** §8's state model is one state per region; a permanent "loading" indicator above finished content contradicts the loaded state and teaches learners to distrust what they read — the exact opposite of the product direction.
- **Expected benefit:** loading reads as a transient indicator; the contradiction disappears from every capture; above-fold density improves (~90px reclaimed) because the box stops consuming permanent vertical space.

### KB-04 — BLOCKING — Evidence set cannot support freeze: mobile content hidden, below-fold composition never captured

- **Aspect:** mobile functional integrity · cycle separation · stage relationships · action prominence · card nesting
- **Screenshot/state:** `en_390x844` / `zh_390x844` — the Streamlit sidebar overlay is open; only a ~100px vertical slice of content is visible, clipped mid-word ("…lidated,", "…es not", "…riting,", "…ut"); the app bar itself is clipped ("eploy"). All four captures are exactly viewport-height despite `full_page=True` (Streamlit scrolls an inner container, so there is nothing to stitch) — no stage item, notice, action, next-step CTA, or limitation notice is visible anywhere in the set.
- **Component/token:** verification harness (`d1_browser_matrix.py` + shared harness `close_sidebar`): the close attempt targets `stSidebarCollapsedControl` / `stExpandSidebarButton` — the *expand* controls — never `stSidebarCollapseButton`, so the overlay stayed open at capture. Not a production-code issue.
- **Recommended change:** re-capture with (a) sidebar collapsed at 390px — assert `[data-testid="stSidebar"]` `aria-expanded="false"` before shooting; (b) full-page evidence via scroll-container capture or scroll-and-stitch (or a tall desktop viewport, e.g. 1280×3200); (c) settled-state timing after KB-03; (d) a two-cycle learner so the 24px inter-cycle rhythm (`--px-space-6` on `.px-cycle-card`) is demonstrated; (e) a below-fold checklist in the evidence JSON: stage-item badges in context, practice state panel, stage secondary actions, the focused panel (4px ink + `--px-shadow-md` + one primary), the "stable transfer" limitation notice.
- **Reason:** the design system's status is "APPROVED DRAFT — pending representative-page validation"; the current set validates the header zone only. Mobile DOM assertions passed (`overflow: false`, ≥44px targets) but nothing in the set *shows* the reflowed 390px content or the L2→L3 nesting the system exists to prove.
- **Expected benefit:** the D1.3 freeze decision rests on complete visual evidence; regressions in the stage composition become reviewable instead of assertion-only.

### KB-05 — HIGH-VALUE — Header disclaimer bypasses the notice recipe and is the loudest block on the page

- **Aspect:** visual hierarchy · color semantics · academic credibility
- **Screenshot/state:** `en_1280x900` / `zh_1280x900` — the prototype disclaimer renders as a native `st.warning` (`.stAlert`): measured 4px full `#1a1c2c` border on all sides, fill `#ffffe7` (Streamlit-native yellow, **not** `--px-status-warning` `#fdf6d8`), no local SVG icon, no `--px-status-accent-warning` bar.
- **Component/token:** `.stAlert` rule in `PIXEL_CSS` (`border: var(--px-border-thick) !important`); §3/§9 notice recipe (`tint + 4px accent bar + icon + body`); §5 reserves 4px for accent bars / focused panel / structural rules.
- **Recommended change:** route `app_prototype_warning` through the shared notice core (`warning_box`/`notice(state="warning")`) — wording byte-identical — or restyle `.stAlert` to the token recipe (2px border + 4px `--px-status-accent-warning` left bar + `--px-status-warning` fill). At freeze, also resolve the §3-vs-§10 conflict in writing: §10 says "disclaimer notice (quiet info)", §3 allows neutral or warning tint; recommend keeping warning tint and amending §10.
- **Reason:** "quiet by default, loud by exception" (§2) and "one loud thing per view" are violated when the heaviest geometry on the page belongs to standing boilerplate; a native-theme yellow also sits outside the token palette.
- **Expected benefit:** the disclaimer stays prominent *enough* through tint and position while the border-weight hierarchy returns to content; one recipe covers all state surfaces, which is what makes the system teachable and reusable.

### KB-06 — HIGH-VALUE — Purpose block carries an off-vocabulary 4px ink bar

- **Aspect:** visual hierarchy · spacing rhythm · aesthetic distinctiveness
- **Screenshot/state:** `en_1280x900` / `zh_1280x900` — `.px-student-purpose` renders with a measured 4px `#1a1c2c` left bar on a `#f4f4f4` wash.
- **Component/token:** `.px-student-purpose { border-left: var(--px-border-thick) }`; §6 defines the purpose block as L1 ("surface, 1px border-subtle or none"); state accents are colored (`--px-status-accent-*`), neutral is `#6b6b7b` — an ink bar exists nowhere in the vocabulary.
- **Recommended change:** drop the bar for a pure L1 block, or use `1px solid var(--px-border-subtle)` on all sides; if a bar is kept as identity, use `--px-status-accent-neutral`, never ink.
- **Reason:** the ink bar makes descriptive prose the second-loudest element on every Student page and spends the "structural 4px" signal that §5 reserves; it also visually rhymes with an error/alert bar.
- **Expected benefit:** the header zone calms further; 4px ink regains its reserved meaning (focused panel, structural rules); one shared-component line improves all six pages.

### KB-07 — HIGH-VALUE — Cycle card and stage items render as native 1px containers; the L2/L3 recipes are dead CSS

- **Aspect:** card nesting · cycle separation · stage relationships · design-system reuse potential
- **Screenshot/state:** `zh_1280x900` — the cycle card's border measures 1px `#d1d2d5` (Streamlit default), no hard shadow, default padding; same for stage-item containers.
- **Component/token:** `journey.py` uses `st.container(border=True)` with inner `.px-stage-head` divs; the specified `.px-cycle-card` (L2: 2px ink, `--px-shadow-sm`, `--px-density-student-card-pad` 20px) and `.px-stage-item` (L3: 1px `--px-border-subtle`, pad 12/16, no shadow) exist in `PIXEL_COMPONENT_CSS` but are never applied to these surfaces. Related: `.px-student-action` (focused panel) uses `--px-shadow-sm`; §6 specifies `--px-shadow-md` — verify on re-capture.
- **Recommended change:** bind the existing recipes to the keyed containers via their stable `st-key-journey_cycle_*` / `st-key-journey_stage_*` classes (the same mechanism the harness already selects), or emit the component divs; correct the `.px-student-action` shadow token to `--px-shadow-md`.
- **Reason:** §6's surface hierarchy is the structural core of "calm ledger". Today the border-weight hierarchy is inverted: chrome (disclaimer 4px, loading 4px, nav radios 4px) outweighs the primary content cards (1px light gray), so cycle separation and nesting depth are under-signaled even where visible.
- **Expected benefit:** cycles read as solid primary records with quiet inset stages; the pixel identity (hard offset shadow) lands on the content where it carries meaning; the L2→L3 rule "no shadows on nested levels" becomes visible and reusable.

### KB-08 — HIGH-VALUE — Sidebar radio options use reserved 4px ink borders

- **Aspect:** visual hierarchy · spacing rhythm
- **Screenshot/state:** all captures — every Language/View/Navigation option is a 4px-ink-bordered box (measured x=30–33 on EN); six stacked heavy boxes make the shell louder than the content column.
- **Component/token:** `[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] { border: var(--px-border-thick) !important }`; §5 assigns 2px to controls and reserves 4px.
- **Recommended change:** set the option border to `var(--px-border-thin)` (2px), keeping padding, `--px-control-height`, and the selected mark unchanged.
- **Reason:** repeated chrome should not carry the reserved structural weight; this is also the largest single loudness contributor after the disclaimer.
- **Expected benefit:** the shell recedes; the "one loud thing per view" principle becomes achievable on content pages. Note: shared shell — the Research sidebar inherits; re-run Research smoke after the change.

### KB-09 — OPTIONAL — Learner context value is sans and reads visually centered

- **Aspect:** typography · information density
- **Screenshot/state:** `en_1280x900` / `zh_1280x900` — the `V097D-D1-E*` learner ID renders in sans, starting after the `minmax(120px, 0.45fr)` label column, so it sits near the optical center of the block.
- **Component/token:** `.px-student-context` (`dt`/`dd` grid); §4 assigns IDs to the mono technical role (`--px-font-mono`, 0.875rem) as on the `cycle-37` chip and record references.
- **Recommended change:** render the value through the `.px-mono` role inside `student_context_block` (or consciously accept sans and note it at freeze); optionally tighten the label column toward content width.
- **Reason:** the identifier is a technical value; sans + central placement reads as prose and slightly blurs the metadata row's scan pattern.
- **Expected benefit:** sharper technical register consistent with the cycle chip; faster label→value scanning in both scripts.

### KB-10 — OPTIONAL — Badge icon is 14px against the 16px spec; re-verify baseline after KB-01

- **Aspect:** status legibility · typography
- **Screenshot/state:** `zh_1280x900` — the "✓ 已完成" badge icon measures 14px; §9 specifies a 16px badge icon.
- **Component/token:** `status_badge_html` calls `icon(..., size=14)`; spec: `.px-status-badge` = 16px icon + label; geometry tokens `--px-icon-sm` (16px).
- **Recommended change:** use `size=16` (`--px-icon-sm`) for badges; after KB-01 restores the 1px accent border, re-check the badge's baseline alignment inside `.px-cycle-head` / `.px-stage-head` (`align-items: baseline`, flex-wrap) in both locales.
- **Reason:** small spec drift in the system's most-repeated state element; baseline drift becomes visible once the border returns.
- **Expected benefit:** spec-exact badge geometry; steadier header rows for en and zh.

### KB-11 — OPTIONAL — Navigation selected state rests on a single 15×15px mark

- **Aspect:** navigation · status legibility
- **Screenshot/state:** all captures — the selected option differs from unselected only by the small `#e00047` square (measured 15×15); background, border, and text weight are identical.
- **Component/token:** `[data-testid="stRadioOption"]` (+ `:has(:checked)`); existing vocabulary only: `--px-surface`, `--px-font-weight-bold`.
- **Recommended change:** within existing tokens, give the checked option a quiet secondary signal (e.g. `background: var(--px-surface)` and/or bold label via `:has(:checked)`), leaving the theme mark itself untouched (see KB-12).
- **Reason:** UI/UX Pro Max `nav-state-active`: current location must be unmistakably highlighted; one small mark is a weak signal, especially at 390px.
- **Expected benefit:** faster orientation without new tokens, new colors, or wording changes.

### KB-12 — REJECT — Do not recolor the red selection marks; document the exception at freeze

- **Aspect:** color semantics
- **Screenshot/state:** all captures — selected Language/View/Navigation radios show a filled `#e00047` square (measured).
- **Component/token:** Streamlit theme `primaryColor` (`#e00047`, config parity mandated by §12) vs §3 "red reserved for forward actions only (never nav selection…)".
- **Recommended change:** change nothing in code or theme; at D1.3 add one sentence to §3 recording native selection marks as an accepted exception (control-state affordance, not an action). Overriding the mark in CSS would fight a mandated-unchanged config for a native affordance.
- **Reason:** the two approved clauses conflict; the cheaper, risk-free resolution is documentation, not a theme war.
- **Expected benefit:** an honest frozen contract; no fragile overrides against Streamlit theming.

### KB-13 — DEFER-E — EN loading copy "?" and mobile type-scale compression

- **Aspect:** bilingual resilience · typography
- **Screenshot/state:** `en_1280x900` — "Loading learning journey?" (stray "?"); `390x844` — h2 compresses to 1.1rem against 1.0625rem card titles, flattening page-vs-card hierarchy at mobile widths.
- **Component/token:** locale key `journey_loading` (O1 copy touch — §15 deferred, needs separate approval); `.stApp h2` mobile rule vs `--px-font-size-card-title`.
- **Recommended change:** defer both to v0.9.7-E exactly as §15 prescribes: the copy item with the O1 approval, the mobile scale with the full mobile redesign. Do not touch wording in D.
- **Reason:** both cross the stated constraints (wording semantics; full mobile redesign).
- **Expected benefit:** D stays scoped to the design system; the items are recorded where they will be picked up.

### KB-14 — OPTIONAL — Loading box geometry claims the reserved 4px full border

- **Aspect:** visual hierarchy · status legibility
- **Screenshot/state:** `en_1280x900` / `zh_1280x900` — `.px-loading` renders with a measured 4px full `#1a1c2c` border on `#f4f4f4`.
- **Component/token:** `.px-loading { border: var(--px-border-thick) }`; §5 reserves 4px for accent bars / focused panel / structural rules; a transient state should use the neutral notice recipe (`--px-status-neutral` tint + `--px-status-accent-neutral` bar).
- **Recommended change:** after KB-03 makes the box transient, restyle it to the neutral notice recipe (or document `.px-loading` as a deliberate distinct pattern at freeze).
- **Reason:** a secondary transient state currently out-weights the primary content cards (KB-07) and equals the focused panel.
- **Expected benefit:** transient feedback quiets down; the reserved geometry keeps a single meaning.

**Aspect coverage:** visual hierarchy KB-05/06/08/14 · information density KB-03/09 · cycle separation KB-03/04/07 · stage relationships KB-04/07 · action prominence KB-04 (unevidenced; DOM-verified only) · status legibility KB-01/02/03/10/11/14 · color semantics KB-02/05/12 · typography KB-02/09/10/13 · spacing rhythm KB-06/08 · card nesting KB-07 · bilingual resilience KB-13 (+ §3 working-well) · academic credibility KB-05 (+ working-well 2) · aesthetic distinctiveness KB-01/06 · mobile functional integrity KB-04 · design-system reuse potential KB-01/07.

---

## 3. What is working well (max 6)

1. **The sans migration landed cleanly.** `--px-font-heading` re-pointed to the display sans works everywhere visible: en page title/section heading, zh headings render proper sans Chinese (no mono CJK), sidebar section labels and radio labels are sans (mono in the v0.9.7-C before shot), and the harness `heading_sans` assertion passes in all four combinations.
2. **The state content model is correct even with broken geometry.** The cycle badge pairs a local check icon with the localized "已完成" label on the right tint family (`data-state="success"` measured `#e6f6ec`); states are never color-alone; the forbidden-claims scan and raw-key scan are clean; both fixed disclaimer phrases are byte-identical.
3. **The calm-ledger direction is already perceptible against v0.9.7-C.** The purpose block lost its 3px boxed frame, the learner block lost its 2px ink box, and the sidebar typography quieted — the page reads calmer even before the recipes are repaired.
4. **Mobile fundamentals hold under assertion:** no horizontal overflow (`scrollWidth <= innerWidth`) in any combination, ≥44px touch targets verified for buttons and the student-ID input at 390px, and the sidebar controls fit the narrow width with bilingual labels wrapping cleanly.
5. **Token and identity discipline is intact:** one canonical `DESIGN_TOKENS` source feeding generated CSS, no literal hex in the component layer, zero remote requests in all renders, radius 0 and hard shadows preserved, motion disabled with the reduced-motion block in place.
6. **Journey read-only integrity is proven:** zero writes across all four renders, and the DOM contract (`px-cycle-head`, `px-stage-item`, `px-status-badge[data-state]`, `px-student-context`, `px-loading`) is present as specified — a solid skeleton for the repaired skin.

---

## 4. Measured evidence appendix (pixel samples from the R1 captures)

| Element (capture) | Measured | Token/spec expectation | Finding |
|---|---|---|---|
| Disclaimer box, `en_1280x900` | 4px `#1a1c2c` full border; fill `#ffffe7`; no icon | `.stAlert` → notice recipe: 2px + 4px `--px-status-accent-warning` bar, `--px-status-warning` `#fdf6d8`, 20px icon | KB-05 |
| Purpose block bar, en + zh | 4px `#1a1c2c` left bar on `#f4f4f4` | L1: 1px `--px-border-subtle` or none | KB-06 |
| Page heading rule, `en_1280x900` | absent (rows below text are white) | `.px-page-heading` structural rule (declaration invalid, dropped) | KB-01 |
| Learner block, `en_1280x900` | no border; fill `#f4f4f4`; value sans | 1px `--px-border-subtle`; mono ID role | KB-01, KB-09 |
| Loading box, en + zh | 4px `#1a1c2c` border, `#f4f4f4` fill, clock icon; persists beside loaded content | transient; neutral notice geometry | KB-03, KB-14 |
| Success badge, `zh_1280x900` | tint `#e6f6ec` present; **no border**; text/icon `#1a1c2c` | 1px `--px-status-accent-success` border; text `--px-status-on-success` `#14532d`; 16px icon | KB-01, KB-02, KB-10 |
| Cycle card, `zh_1280x900` | 1px `#d1d2d5` border, no shadow | L2 `.px-cycle-card`: 2px ink + `--px-shadow-sm` + 20px pad | KB-07 |
| Sidebar radio option, `en_1280x900` | 4px `#1a1c2c` border per option | 2px control geometry (§5) | KB-08 |
| Selected mark, `en_1280x900` | 15×15 `#e00047` filled square | theme parity (§12) vs §3 red reservation | KB-11, KB-12 |
| Mobile captures, 390×844 | sidebar overlay open; ~100px content slice; viewport-height images only | sidebar-collapsed, full-scroll captures | KB-04 |

## 5. Constraints respected in this critique

No recommendation changes business behavior or wording semantics (Journey grouping, raw events, ordering, states, navigation, persistence untouched; KB-03 is presentation-only; both fixed disclaimer phrases and the all-descriptive limitation stay byte-identical). No remote resources, no new features, no backend changes, no full mobile redesign (KB-13 deferred), no dark mode, no animation. The pixel identity (square corners, hard offset shadows) and the quiet tint + accent-bar + icon + label state recipe are preserved — KB-01/KB-02 exist precisely to restore them.
