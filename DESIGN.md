---
version: alpha
name: Stripi-design-analysis
description: An inspired interpretation of Stripi's design language — a financial-infrastructure brand built on a deep navy ink, an electric indigo primary, and a recurring atmospheric gradient mesh that occupies the upper third of nearly every marketing page. The system pairs the proprietary Sohne family at thin (300) weights with negative letter-spacing for editorial-density display headlines, and uses tabular-figure body type where money and numerics matter. Buttons are tight-radius pills, cards live on near-white surfaces, and the dashboard track flips polarity to a familiar dark-app shell.

colors:
  primary: "#533afd"
  primary-deep: "#4434d4"
  primary-press: "#2e2b8c"
  primary-soft: "#665efd"
  primary-bg-subdued-hover: "#b9b9f9"
  brand-dark-900: "#1c1e54"
  ink: "#0d253d"
  ink-secondary: "#273951"
  ink-mute: "#64748d"
  ink-mute-2: "#61718a"
  on-primary: "#ffffff"
  canvas: "#ffffff"
  canvas-soft: "#f6f9fc"
  canvas-cream: "#f5e9d4"
  hairline: "#e3e8ee"
  hairline-input: "#a8c3de"
  ruby: "#ea2261"
  magenta: "#f96bee"
  lemon: "#9b6829"
  shadow-blue: "#003770"

typography:
  display-xxl:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 56px
    fontWeight: 300
    lineHeight: 1.03
    letterSpacing: -1.4px
    fontFeature: ss01
  display-xl:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 48px
    fontWeight: 300
    lineHeight: 1.15
    letterSpacing: -0.96px
    fontFeature: ss01
  display-lg:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 32px
    fontWeight: 300
    lineHeight: 1.1
    letterSpacing: -0.64px
    fontFeature: ss01
  display-md:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 26px
    fontWeight: 300
    lineHeight: 1.12
    letterSpacing: -0.26px
    fontFeature: ss01
  heading-lg:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 22px
    fontWeight: 300
    lineHeight: 1.1
    letterSpacing: -0.22px
    fontFeature: ss01
  heading-md:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 20px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: -0.2px
    fontFeature: ss01
  heading-sm:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 18px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: 0
    fontFeature: ss01
  body-lg:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 16px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: 0
    fontFeature: ss01
  body-md:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 15px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: 0
    fontFeature: ss01
  body-tabular:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: -0.42px
    fontFeature: tnum
  button-md:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: 0
    fontFeature: ss01
  button-sm:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: 0
    fontFeature: ss01
  caption:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: -0.39px
    fontFeature: tnum
  micro:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 11px
    fontWeight: 300
    lineHeight: 1.4
    letterSpacing: 0
    fontFeature: ss01
  micro-cap:
    fontFamily: "sohne-var, 'SF Pro Display', system-ui, -apple-system, sans-serif"
    fontSize: 10px
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: 0.1px
    fontFeature: ss01

rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px

spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 32px
  huge: 64px

components:
  button-primary-pill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: 8px 16px
  button-primary-pill-pressed:
    backgroundColor: "{colors.primary-press}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: 8px 16px
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: 8px 16px
  button-on-dark:
    backgroundColor: "{colors.brand-dark-900}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: 8px 16px
  text-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 8px 12px
  text-input-focused:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 8px 12px
  card-feature-light:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: 32px
  card-pricing:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: 32px
  card-pricing-featured:
    backgroundColor: "{colors.brand-dark-900}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: 32px
  card-cream-band:
    backgroundColor: "{colors.canvas-cream}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: 32px
  card-dashboard-mockup:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-tabular}"
    rounded: "{rounded.lg}"
    padding: 24px
  pill-tag-soft:
    backgroundColor: "{colors.primary-bg-subdued-hover}"
    textColor: "{colors.primary-deep}"
    typography: "{typography.micro-cap}"
    rounded: "{rounded.pill}"
    padding: 4px 8px
  nav-bar-on-mesh:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xs}"
    padding: 16px 24px
  link-on-light:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.xs}"
    padding: 0px
  footer-light:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-mute}"
    typography: "{typography.caption}"
    rounded: "{rounded.xs}"
    padding: 64px 24px
---

## Overview

Stripi's design language opens with the gradient mesh. A wide horizontal band of pastel cream, sherbet orange, lavender, electric indigo, and ruby pink occupies the upper third of nearly every marketing page — the brand's instantly-recognizable atmospheric backdrop. Type and product UI mockups float above it on `{colors.canvas}` (white), with the gradient acting as both decoration and visual anchor. The lower portion of the page returns to white, with feature explanations on `{colors.canvas-soft}` (a barely-tinted cool off-white) and dashboard product mockups composited as faux IDE/console panels in deep navy.

The color system has two primary roles. **Indigo** (`{colors.primary}` — `#533afd`) is the brand's signature CTA color, used sparingly: one filled pill per band. **Deep navy** (`{colors.ink}` — `#0d253d`) is the universal body text color and the fill of dashboard mockups, the featured pricing tier, and the dark-app surfaces on the dashboard track. Ruby (`{colors.ruby}`) and magenta (`{colors.magenta}`) appear inside the gradient mesh and as accent dots in product UI mockups; they are not used as button colors.

Typography is built around **Sohne** at weight 300 with negative letter-spacing — the brand's editorial-density display signature. Display sizes (32–56px) use -1.4px to -0.64px tracking; body sizes use 0; tabular caption sizes (where money and numerics matter) use the OpenType `tnum` feature plus a tightening -0.36 to -0.42px tracking. The `ss01` stylistic set is enabled across all roles.

**Key Characteristics:**
- Gradient-mesh backdrop on every marketing hero — cream/orange/lavender/indigo/ruby horizontally washed across the upper third of the page.
- Single-indigo CTA hierarchy: filled `{colors.primary}` pill is the only filled button on marketing surfaces.
- Sohne thin (weight 300) display tier with negative tracking from -1.4px to -0.2px depending on size.
- Tabular-figure body type (`tnum`) for any cell containing money or numerics — the brand's quiet financial-data signal.
- Dark-app dashboard track: deep navy product UI mockups sit composited above the white canvas, frequently with rendered code or dashboard tables inside.
- Pill-shaped buttons (`{rounded.pill}` 9999px) with tight `8px 16px` padding — short, decisive, transactional.
- Cream-band feature cards (`{colors.canvas-cream}`) introduce a warm interlude between blue/white sections without breaking the brand's chromatic logic.

## Colors

> **Source pages:** home (`/`), `/payments`, `/pricing`, `dashboard.stripe.com/register/payments`.

### Brand & Accent
- **Indigo** (`{colors.primary}` — `#533afd`): The brand's signature CTA color. Filled-pill button, link emphasis, gradient anchor.
- **Indigo Deep** (`{colors.primary-deep}` — `#4434d4`): A deeper indigo used in gradient mid-stops and as the press-state warmer alternative.
- **Indigo Press** (`{colors.primary-press}` — `#2e2b8c`): Pressed-state lift of the primary.
- **Indigo Soft** (`{colors.primary-soft}` — `#665efd`): A lighter indigo used in product-UI accents and chart highlights.
- **Indigo Subdued** (`{colors.primary-bg-subdued-hover}` — `#b9b9f9`): Pale indigo fill used as soft tag background.
- **Brand Dark 900** (`{colors.brand-dark-900}` — `#1c1e54`): The deep navy used on the featured pricing tier and dashboard chrome.
- **Ruby** (`{colors.ruby}` — `#ea2261`): Gradient accent and chart highlight; never a button.
- **Magenta** (`{colors.magenta}` — `#f96bee`): Brighter pink stop in gradient meshes.
- **Lemon** (`{colors.lemon}` — `#9b6829`): Warm sherbet stop in gradient backdrops.

### Surface
- **Canvas** (`{colors.canvas}` — `#ffffff`): Default page background.
- **Canvas Soft** (`{colors.canvas-soft}` — `#f6f9fc`): Cool-tinted off-white used on feature bands beneath the gradient hero.
- **Canvas Cream** (`{colors.canvas-cream}` — `#f5e9d4`): Warm cream used as a feature-band fill — the brand's chromatic interlude.
- **Hairline** (`{colors.hairline}` — `#e3e8ee`): 1px borders on cards and tables.
- **Hairline Input** (`{colors.hairline-input}` — `#a8c3de`): Slightly cooler hairline used on form inputs.

### Text
- **Ink** (`{colors.ink}` — `#0d253d`): Default body text color across the brand. Deep navy, never pure black.
- **Ink Secondary** (`{colors.ink-secondary}` — `#273951`): Secondary text on white.
- **Ink Mute** (`{colors.ink-mute}` — `#64748d`): Helper text, captions, table labels.
- **Ink Mute 2** (`{colors.ink-mute-2}` — `#61718a`): Near-equivalent to ink-mute used in nav.
- **On Primary** (`{colors.on-primary}` — `#ffffff`): Text on indigo / dark-navy surfaces.

### Semantic
The brand does not use a separate semantic color palette in the marketing system — error / success states live in dashboard-product UI specifically.

## Typography

### Font Family

The display and UI tier is **Sohne** (proprietary, licensed from Klim Type Foundry) at weights 300 (thin) and 400 (regular). The variable font (`sohne-var`) is loaded with `font-feature-settings: "ss01"` enabled globally — the stylistic set substitutes a single-story `a` and other character variants that are part of the brand's typographic signature.

When Sohne is unavailable, fall back to **SF Pro Display** at thin weights, then system-ui. For maximum brand fidelity, **Inter** (open-source) at weight 300 with `font-feature-settings: "ss01"` and `letter-spacing: -1.4px` on display sizes approximates the rhythm closely.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-xxl}` | 56px | 300 | 1.03 | -1.4px | Hero headline |
| `{typography.display-xl}` | 48px | 300 | 1.15 | -0.96px | Section opener |
| `{typography.display-lg}` | 32px | 300 | 1.1 | -0.64px | Card title / sub-section |
| `{typography.display-md}` | 26px | 300 | 1.12 | -0.26px | Compact card title |
| `{typography.heading-lg}` | 22px | 300 | 1.1 | -0.22px | Pricing tier name |
| `{typography.heading-md}` | 20px | 300 | 1.4 | -0.2px | Section sub-heading |
| `{typography.heading-sm}` | 18px | 300 | 1.4 | 0 | Mini-section label |
| `{typography.body-lg}` | 16px | 300 | 1.4 | 0 | Marketing body lead |
| `{typography.body-md}` | 15px | 300 | 1.4 | 0 | Default UI body |
| `{typography.body-tabular}` | 14px | 300 | 1.4 | -0.42px | Money / numeric tables (uses `tnum`) |
| `{typography.button-md}` | 16px | 400 | 1.0 | 0 | Pill button label |
| `{typography.button-sm}` | 14px | 400 | 1.0 | 0 | Compact pill label |
| `{typography.caption}` | 13px | 400 | 1.4 | -0.39px | Helper, table labels |
| `{typography.micro}` | 11px | 300 | 1.4 | 0 | Fine print |
| `{typography.micro-cap}` | 10px | 400 | 1.15 | 0.1px | All-caps eyebrow |

### Principles
- **Thin weight is the brand.** Display tiers always render at weight 300. Bumping to 400+ removes the brand's editorial air.
- **Negative tracking on display.** -1.4px at 56px, scaling proportionally down to -0.2px at 20px. The negative tracking is the brand's typographic signature.
- **Tabular figures for money.** Any cell rendering currency, transaction amounts, or numeric counts uses `font-feature-settings: "tnum"` plus a tightening tracking. The brand quietly signals its financial DNA through this micro-detail.
- **`ss01` globally.** Apply `font-feature-settings: "ss01"` to the body element so the stylistic-set substitution is on for every text role.

### Note on Font Substitutes
Sohne is proprietary. Use **Inter** (open-source via Google Fonts) at weight 300 with `letter-spacing: -1.4px` and `font-feature-settings: "ss01"` for display tiers — Inter is the closest open-source analogue. For body sizes, Inter at 300 weight with `font-feature-settings: "tnum"` (where applicable) is the canonical substitute. Avoid Helvetica or system-ui defaults — they're heavier than the brand needs.

## Layout

### Spacing System
- **Base unit**: 8px (with 2 / 4 / 12 sub-tokens for fine work).
- **Tokens**: `{spacing.xxs}` 2px · `{spacing.xs}` 4px · `{spacing.sm}` 8px · `{spacing.md}` 12px · `{spacing.lg}` 16px · `{spacing.xl}` 24px · `{spacing.xxl}` 32px · `{spacing.huge}` 64px.
- **Section padding**: 64–96px on marketing surfaces; 32–48px on dashboard / product surfaces.
- **Card internal padding**: 32px on feature cards; 24px on dashboard mockups.

### Grid & Container
- Marketing pages center in a ~1200px container with the gradient mesh extending edge-to-edge above.
- Pricing collapses 4-up → 2-up → 1-up at 1024 / 768 breakpoints.
- Dashboard product mockups use their own internal grids (12-col tables, 3-col card grids) rendered as static composites.

### Whitespace Philosophy
The gradient mesh occupies the upper third of the page; the white canvas below is generously padded. Section gaps tend toward 96px, with content tightening to 32px on dashboard / pricing pages where users compare and act.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| 0 | Flat | Default surface |
| 1 | `box-shadow: rgba(0,55,112,0.08) 0 1px 3px` | Card lift on white |
| 2 | `box-shadow: rgba(0,55,112,0.08) 0 8px 24px, rgba(0,55,112,0.04) 0 2px 6px` | Floating panels, dashboard mockup chrome |
| 3 | Gradient mesh backdrop | The brand's primary depth medium — atmospheric color rather than literal shadow |

### Decorative Depth
The gradient mesh IS the depth system. Implemented as a layered SVG or large background image rather than CSS gradients (the actual mesh has organic blob shapes that aren't CSS-renderable). The mesh provides the brand's signature lift; literal shadows are reserved for product-UI mockups and stay subtle.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.xs}` | 4px | Hairline tags, table chrome |
| `{rounded.sm}` | 6px | Form inputs |
| `{rounded.md}` | 8px | Compact cards, alerts |
| `{rounded.lg}` | 12px | Pricing cards, feature cards |
| `{rounded.xl}` | 16px | Dashboard product mockup chrome |
| `{rounded.pill}` | 9999px | All buttons, tag pills |

### Photography Geometry
The brand uses **product UI mockups** more than photography. Dashboard composites render as faux IDE/terminal/dashboard chrome inside `{rounded.lg}` 12px containers with a subtle `box-shadow`. Real photography appears in customer logo strips and the rare case-study card; treated as inset 4:3 with no shadow.

## Components

### Buttons

**`button-primary-pill`** — the dominant CTA system-wide.
- Background `{colors.primary}`, text `{colors.on-primary}`, type `{typography.button-md}`, padding `{spacing.sm} {spacing.lg}` (8px 16px), rounded `{rounded.pill}` 9999px.
- Pressed state `button-primary-pill-pressed` shifts background to `{colors.primary-press}`.

**`button-secondary`** — outline-style alternative.
- Background `{colors.canvas}`, text `{colors.primary}`, 1px solid `{colors.primary}` border, same pill geometry.

**`button-on-dark`** — used on dashboard / dark surfaces.
- Background `{colors.brand-dark-900}`, text `{colors.on-primary}`, same pill geometry.

### Cards & Containers

**`card-feature-light`** — feature explanation card on white.
- Background `{colors.canvas}`, padding `{spacing.xxl}`, rounded `{rounded.lg}` 12px, 1px `{colors.hairline}` border, optional Level 1 shadow.

**`card-pricing`** — standard pricing tier.
- Background `{colors.canvas}`, padding `{spacing.xxl}`, rounded `{rounded.lg}`, 1px `{colors.hairline}` border. Title `{typography.heading-lg}`, price `{typography.display-md}`, body `{typography.body-md}`, CTA pinned bottom as `button-primary-pill`.

**`card-pricing-featured`** — the inverted dark featured tier.
- Background `{colors.brand-dark-900}`, text `{colors.on-primary}`, otherwise identical structure to `card-pricing`. The deep-navy fill is the brand's distinctive featured-tier choice.

**`card-cream-band`** — warm interlude card.
- Background `{colors.canvas-cream}`, text `{colors.ink}`, padding `{spacing.xxl}`, rounded `{rounded.lg}`. Used to break up the indigo / white rhythm with warmth.

**`card-dashboard-mockup`** — composited dashboard / product UI screenshot.
- Background `{colors.canvas}`, type `{typography.body-tabular}` (with `tnum`), padding `{spacing.xl}` 24px, rounded `{rounded.lg}` 12px, Level 2 shadow. Often contains nested mini-mockups: code preview + dashboard table + chart card.

### Inputs & Forms

**`text-input`** — standard form field.
- Background `{colors.canvas}`, text `{colors.ink}`, type `{typography.body-md}`, padding `{spacing.sm} {spacing.md}` (8px 12px), rounded `{rounded.sm}` 6px, 1px `{colors.hairline-input}` border.
- Focus state `text-input-focused`: border swaps to `{colors.primary}`.

### Navigation

**`nav-bar-on-mesh`** — top nav floating over the gradient hero.
- Background `{colors.canvas}` (or transparent depending on scroll), text `{colors.ink}`, padding `{spacing.lg} {spacing.xl}`. Logo wordmark on the left, primary nav center, sign-in + filled `button-primary-pill` on the right.

### Pills, Tags, and Chips

**`pill-tag-soft`** — subdued indigo tag.
- Background `{colors.primary-bg-subdued-hover}`, text `{colors.primary-deep}`, type `{typography.micro-cap}`, padding `4px 8px`, rounded `{rounded.pill}`.

### Signature Components

**Gradient Mesh Backdrop** — pastel cream → sherbet orange → lavender → indigo → ruby pink stops blurred horizontally across the upper third of the page. Implemented as SVG or a large background image — not a flat CSS gradient (the real mesh has organic blob shapes).

**Composited Dashboard Mockup** — multi-layer faux-product-UI compositions: an IDE panel on the left, a dashboard table center, a chart card on the right, all rendered at small scale inside `{rounded.lg}` containers with subtle Level 2 shadows. The composite is the brand's most-photographed feature.

**Tabular-Figure Money Type** — every number rendering money, count, or transaction value uses `font-feature-settings: "tnum"`. The brand's quiet signal that it's a financial-infrastructure platform.

**`link-on-light`** — inline links on light surfaces.
- Text `{colors.primary}` rendered in `{typography.body-md}`, no underline by default.

**`footer-light`** — site-wide footer.
- Background `{colors.canvas}`, text `{colors.ink-mute}`, type `{typography.caption}`, padding `{spacing.huge} {spacing.xl}` (64px 24px). Holds 4–6 columns of link groups, social icons, and a small legal row.

## Do's and Don'ts

### Do
- Reserve `{colors.primary}` for filled CTAs and inline link emphasis — it should appear sparingly, one filled button per band.
- Apply the gradient mesh to every marketing hero; bare-canvas heroes feel off-brand.
- Render display tiers at weight 300 with negative letter-spacing — the thin tracking is the typographic signature.
- Use `font-feature-settings: "tnum"` on every money / numeric cell.
- Apply `font-feature-settings: "ss01"` globally on the body element.
- Pair every feature explanation with a composited product UI mockup; the brand's argument is "look at the actual product."

### Don't
- Don't bump display weight above 300 — at 400 the brand's editorial air collapses.
- Don't add new accent colors outside the documented gradient stops (cream / orange / lavender / indigo / ruby / magenta).
- Don't use the indigo `{colors.primary}` as a body-text color — it's a CTA and link color, not a type color at body size.
- Don't shrink button padding below `8px 16px` — the tight pill is part of the brand's transactional feel.
- Don't render money cells without `tnum` — it breaks the quiet financial-data signature.
- Don't replace the pill shape with rounded-rectangles for buttons.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Wide | ≥ 1440px | Full gradient mesh edge-to-edge; dashboard composite at full scale |
| Desktop | 1024–1440px | Default content max-width; pricing 4-up |
| Tablet | 768–1023px | Pricing 2-up; dashboard composite simplifies to 2 panels |
| Mobile | < 768px | Pricing 1-up; hamburger nav; display drops 56 → 36px |

### Touch Targets
- Pill buttons hit ≥ 40×40px on mobile via padding scaling. On smaller screens, buttons size up to 44×44px to maintain WCAG AAA.
- Form fields stay at 40px minimum height.

### Collapsing Strategy
- Display tiers stair-step 56 → 48 → 32 → 26 → 22px through the breakpoints.
- Gradient mesh re-tiles on mobile to preserve the wash without disappearing.
- Dashboard composites simplify to single-panel mockups on mobile; the multi-layer composition only renders at desktop+.
- Pricing tiers stair-step 4-up → 2-up → 1-up.

### Image Behavior
Product UI composites use `srcset` with art-direction crops at major breakpoints. Mobile crops focus on the most actionable inner panel; desktop crops show the full multi-layer composition.

## Iteration Guide

1. Focus on ONE component at a time.
2. Reference component names and tokens directly (`{colors.primary}`, `{button-primary-pill}-pressed`, `{rounded.pill}`).
3. Run `npx @google/design.md lint DESIGN.md` after edits.
4. Add new variants as separate entries.
5. Default body to `{typography.body-md}` (15px); use `{typography.body-tabular}` for any money / numeric cell.
6. Apply `ss01` globally on the body; apply `tnum` per-element on numeric content.
7. The gradient mesh is non-negotiable on marketing heroes — bare-canvas heroes break the brand.

---

## ERP Operational Screens (App Shell, Not Marketing)

The marketing design above is for landing pages, public inquiry portal, and the `brands/` showcase. The **operational app** (customers, sales, inventory, finance, procurement, reports) follows a different rule set: dense, scan-friendly, fast to operate under time pressure.

> When in doubt, mimic Linear / Notion data tables / Stripe Dashboard, not Stripe Marketing.

### Page Skeleton (every operational page)

```
┌─ Breadcrumb ──────────────────────────────────────────────────┐
│  销售 / 销售订单 / SO-2026-0421                                │
├───────────────────────────────────────────────────────────────┤
│  <PageHeader title="销售订单" description="..." actions={...} />│
├───────────────────────────────────────────────────────────────┤
│  <SearchBar filters={...} onReset={...} /> [+ 新建] [导入]    │
├───────────────────────────────────────────────────────────────┤
│  <Table rowSelection columns={...} dataSource={rows} />        │
│  Batch actions bar appears when ≥ 1 row selected               │
├───────────────────────────────────────────────────────────────┤
│  <Pagination total={N} current={page} pageSize={size} />       │
└───────────────────────────────────────────────────────────────┘
```

**No hero sections, no gradient mesh, no display-xxl.** The app shell is plain `#ffffff` canvas on a `#f6f9fc` workspace background. Brand color is reserved for primary CTAs only.

### Layout Tokens (operational screens)

| Token | Value | Use |
|---|---|---|
| `app.canvas` | `#ffffff` | Card / panel background |
| `app.workspace` | `#f6f9fc` | Page background (the "off-white behind cards") |
| `app.sider` | `#1c1e54` | Left navigation (dark navy, brand-dark-900) |
| `app.header` | `#ffffff` | Top bar (h=56px, hairline bottom) |
| `app.content.maxWidth` | `1440px` | Centered on wide monitors |
| `app.content.padding` | `24px` | Breathing room around content |
| `app.card.padding` | `16px` | Inside cards / panels |
| `app.row.height` | `44px` | Default table row height |
| `app.row.height.compact` | `36px` | For ≥ 10 rows visible without scroll |
| `app.row.height.comfort` | `52px` | For forms in Drawer |

### Typography (operational screens override the marketing tiers)

- **Page title**: 20px / weight 600 (handled by `<PageHeader>`)
- **Section title**: 16px / weight 600
- **Body / table cell**: 14px / weight 400
- **Helper / caption**: 12px / weight 400, `ink-mute` color
- **Money / quantity / date**: 14px, **`font-feature-settings: "tnum"`** mandatory
- **NO thin (300) weight on operational UI** — that breaks the editorial "marketing" mood and hurts scan speed.

### Color Usage (operational)

- **Primary CTA** (filled button): `colors.primary` `#533afd` — max 1 per page band
- **Status tags**: semantic only (`<StatusTag tone="success|warning|danger|info|processing|neutral">`)
- **Money positive**: `#10b981` (green-500)
- **Money negative / loss / overdue**: `#ef4444` (red-500)
- **Frozen / disabled**: `ink-mute` + opacity 0.5
- **Hairline / divider**: `colors.hairline` `#e3e8ee` — 1px borders, never thicker
- **Hover background**: `colors.canvas-soft` `#f6f9fc`
- **Selected row**: `primary` at 8% opacity

### Component Patterns (operational)

#### 1. Data Table (most-used pattern)

```tsx
<Table<T>
  rowKey="id"
  size="middle"            // 44px row height
  rowSelection={{ ... }}   // batch actions
  scroll={{ x: 1200 }}     // horizontal scroll on narrow viewports
  sticky
  columns={[
    { title: '名称', dataIndex: 'name', fixed: 'left', width: 200 },
    { title: '金额', dataIndex: 'amount', align: 'right',
      render: (v) => <MoneyCell value={v} /> },
    { title: '状态', dataIndex: 'status', width: 100,
      render: (v) => <StatusTag status={v} /> },
    { title: '操作', width: 120, fixed: 'right',
      render: (_, row) => <RowActions row={row} /> },
  ]}
  pagination={{ ... }}
/>
```

Rules:
- 数量、金额、日期列必须 `align: 'right'`，等宽数字字体
- 操作列固定在右侧，宽度 ≤ 140px
- 名称列固定在左侧
- 状态列宽 100px，使用 `<StatusTag>`
- 行高 44px（`size="middle"`）
- ≥ 100 行启用虚拟滚动（antd v5 自带）

#### 2. Filter Bar

```tsx
<SearchBar
  fields={[
    { name: 'name', label: '客户名称', type: 'input' },
    { name: 'status', label: '状态', type: 'select', options: [...] },
    { name: 'dateRange', label: '创建时间', type: 'dateRange' },
    { name: 'owner', label: '负责人', type: 'userSelect' },
  ]}
  onSearch={...}
  onReset={...}
/>
```

- 字段数 ≤ 4 一行；超过则第 5+ 折叠到"更多"抽屉
- 默认显示"重置"和"搜索"按钮；按 Enter 触发搜索

#### 3. Drawer Form (新建 / 编辑)

```tsx
<Drawer
  title={isEdit ? '编辑客户' : '新建客户'}
  open={open}
  width={isEdit ? 720 : 560}
  onClose={onClose}
  footer={<FormFooter onCancel={onClose} onSubmit={form.submit} loading={saving} />}
>
  <Form layout="vertical" form={form} onFinish={onSubmit}>
    {/* 字段 */}
  </Form>
</Drawer>
```

Rules:
- ≤ 4 字段用 Modal
- 5–15 字段用 Drawer，width 560 (新建) / 720 (编辑)
- > 15 字段或分步骤用 Steps + Drawer
- 提交按钮始终固定在 Drawer 底部 footer
- 必填字段加 `*`，不靠 placeholder 区分

#### 4. Detail Page Tabs

```tsx
<Tabs
  items={[
    { key: 'basic', label: '基本信息', children: <BasicInfo data={customer} /> },
    { key: 'contacts', label: `联系人 (${contacts.length})`, children: <ContactsList /> },
    { key: 'orders', label: `订单 (${ordersCount})`, children: <OrdersTab customerId={id} /> },
    { key: 'followups', label: '跟进记录', children: <FollowUpsTab /> },
    { key: 'audit', label: '操作日志', children: <AuditLog entityType="customer" entityId={id} /> },
  ]}
/>
```

Rules:
- 默认 Tab = 基本信息
- 关系型 Tab 标题后跟数量 `(N)`，> 0 时高亮
- 操作日志 Tab 放最后
- 每个 Tab 都是独立 lazy-loaded 模块

#### 5. Money Cell (强制统一)

```tsx
<MoneyCell value={amount} currency="CNY" signed />
// ¥ 1,234.56      (正)
// -¥ 1,234.56     (负，红色)
```

- 总是右对齐
- 总是 `tnum`
- 负数必须红色（`<Typography.Text type="danger">` 或 `style={{ color: '#ef4444' }}`）
- 货币符号前置，无空格
- 0 显示 `¥ 0.00`，不显示 `—`（避免和空数据混淆）

#### 6. Status Tag (统一语义)

| 业务语义 | tone | 颜色 |
|---|---|---|
| 完成、已支付、已签收 | `success` | green |
| 进行中、待处理 | `processing` | gold |
| 警告、即将到期 | `warning` | orange |
| 失败、已取消、已拒绝、超期 | `danger` | red |
| 草稿、待提交 | `info` | blue |
| 归档、停用 | `neutral` | default |

不要用 raw `color="purple"` 这种自由发挥。

#### 7. Empty / Loading / Error

- **Loading**: `<Spin size="small" />` 居中卡片内，或骨架屏（> 3 行表格用）
- **Empty**: `<EmptyState title="还没有客户" description="新建第一个客户开始" action={<Button type="primary" onClick={onNew}>+ 新建客户</Button>} />`
- **Error**: 卡片内 `<Result status="error" title="加载失败" extra={<Button onClick={retry}>重试</Button>} />`
- 任意状态切换都要有过渡，不要直接闪烁

#### 8. Batch Operations

选中行 ≥ 1 时，表格上方出现批量操作栏：

```tsx
<Affix offsetTop={56}>
  <Alert
    banner
    message={`已选 ${selected.length} 项`}
    type="info"
    showIcon
    action={
      <Space>
        <Button onClick={batchAssign}>批量分配</Button>
        <Button onClick={batchTag}>批量打标签</Button>
        <Button onClick={batchExport}>导出</Button>
        <Button danger onClick={batchDelete}>删除</Button>
        <Button type="text" onClick={clearSelection}>取消</Button>
      </Space>
    }
  />
</Affix>
```

#### 9. Permission-Gated Button

```tsx
<Authorized permission="customer.delete">
  <Button danger onClick={onDelete}>删除</Button>
</Authorized>
```

没有权限 → 不渲染。后端必须 re-check。

#### 10. Status Flow Visualization (商机/订单看板)

- 列 = 阶段（潜在 → 询价 → 报价 → 谈判 → 成单 / 丢单）
- 卡片 = 商机
- 拖拽切换阶段，调用 `PATCH /opportunities/{id}` 触发状态机校验
- 失败的拖拽回弹并 toast 显示不允许的转移

### Spacing Scale (atomic, use these only)

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`

Padding / margin / gap: 禁止 5 / 7 / 13 / 17。

### Border Radius (semantic, not free)

| 形状 | 值 | 用在 |
|---|---|---|
| pill | 999 | 按钮、tag |
| card | 8 | 卡片、Drawer、Modal |
| input | 6 | Input、Select、DatePicker |
| tag | 4 | 小标签、徽章 |
| none | 0 | 表格内单元格 |

### Don'ts (operational screens)

- 不要 hero section / 全屏渐变背景
- 不要 thin (300) 字重
- 不要超过 3 个填充主色按钮
- 不要 modal 装 8+ 字段
- 不要 inline `<input>`，必须 `<Form.Item>`
- 不要硬编码 `#1890ff` `#52c41a` `#f5222d` —— 用 token
- 不要在表格里渲染 markdown / 富文本
- 不要给操作列加 icon-only 按钮（无障碍 + 难发现），图标 + 文字

### Implementation

- Tokens 在 `frontend/src/design-tokens.ts`（与 antd `ConfigProvider.theme` 合并）
- 全局样式在 `frontend/src/styles/globals.css`（reset + 字体 feature）
- 复杂组件在 `frontend/src/ui/`（每个文件 < 100 行）
- 业务组件在 `frontend/src/components/<domain>/`
- 页面在 `frontend/src/pages/<domain>/<Page>.tsx`，按需拆出 `_components/` 子目录
