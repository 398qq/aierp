# Neo-Brutalist Inventory Management — AIERP

## Vision

Redesign the AIERP inventory management page as a **neo-brutalist command center** — hard shadows, heavy borders, bold typography, and raw color blocks that make inventory data feel tangible and urgent. No frosted glass, no soft gradients — this is inventory management as industrial design.

## Target Page

`frontend/src/pages/inventory/index.tsx` — replace the current standard Ant Design layout with a neo-brutalist design. The page is already lazy-loaded in `App.tsx`.

## Design Direction

**Neo-Brutalism + Industrial** — not just ugly-cute for aesthetics; the raw visual language should communicate urgency and clarity for warehouse operations.

### Visual Language

1. **Hard Borders**: `border: 3px solid #000` (or `var(--color-border-hard)`). Every card, table, button — no border-radius (border-radius: 0) or max 4px. Panels are defined by their hard edges.
2. **Hard Shadows**: `box-shadow: 6px 6px 0 #000` (or `var(--color-shadow-hard)`). Offset shadows with NO blur. Creates genuine depth through layering, not soft gradients.
3. **Bold Typography**: Oversized headings (clamp(2rem, 4vw, 3.5rem) for the page title). Monospace or geometric sans-serif for data. Font-weight 700+ for labels, 900 for KPIs. Numbers in tabular-nums.
4. **Color Blocks**: Solid background colors on cards — mustard yellow (#FFD700 or similar warm yellow), off-white (#F5F5F0), raw red (#FF4444), electric blue (#3366FF). No gradients. Cards are solid colored blocks with hard borders.
5. **Raw Aesthetic**: Deliberately unpolished feel — visible grid lines, raw table borders, chunky buttons. Think Swiss design meets punk zine. But the data must be perfectly readable — the "rawness" is a design choice, not sloppiness.
6. **Typography**: Primary font — a bold grotesk (system stack: Inter/Helvetica Neue/Arial Black). Monospace for SKUs, quantities, IDs. All-caps labels for section headers.
7. **Negative Space**: Generous padding inside cards. The hard borders need breathing room. Compact tables but spacious containers.

### Color Palette (Neo-Brutalist)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#F5F5F0` (warm off-white) | Page background |
| `--color-border-hard` | `#1A1A1A` (near-black) | All borders |
| `--color-shadow-hard` | `#1A1A1A` | Hard shadows |
| `--color-card-kpi` | `#FFD700` (yellow) | KPI cards |
| `--color-card-alert` | `#FF4444` (raw red) | Low stock / dead stock cards |
| `--color-card-info` | `#3366FF` (electric blue) | Restock / forecast cards |
| `--color-card-neutral` | `#FFFFFF` (white) | Table / list cards |
| `--color-card-success` | `#00CC66` (vibrant green) | Normal stock indicator |
| `--color-accent` | `#FF6B35` (orange) | Action buttons / highlights |
| `--color-text` | `#1A1A1A` | Primary text |
| `--color-text-muted` | `#666666` | Secondary text |

## Data Sections (all use real API data, same endpoints as current page)

### Page Header
- Massive page title "库存管理" in bold grotesk, HUGE (clamp 3rem to 5rem)
- Subtitle in monospace: "INVENTORY CONTROL" with a hard yellow underline block
- Quick action group: 3 chunky hard-shadow buttons (Adjust, Restock, Export)
- No soft top bar — the header IS the statement

### KPI Band (4 cards in a row)
- **Total Stock**: Yellow block, massive number, "TOTAL QTY" label in all-caps monospace
- **Low Stock**: Red block if >0, yellow otherwise — with a warning triangle icon, bold count
- **Dead Stock**: Gray/red block, "DEAD STOCK" label
- **Restock Suggestions**: Electric blue block, count + chunky "补货" button inline
- Each card: hard border (3px), hard shadow (6px offset), NO border-radius
- Hover: shadow offset increases (8px → 12px), card shifts -2px translateY

### Main Content (asymmetrical layout)

**Top priority: Restock Suggestions & Dead Stock** (side by side when both present)
- Bold colored cards with list items
- Each list item: monospace SKU, hard-bordered status tags
- Urgency tags use actual colored blocks (red block for 紧急, yellow for 建议)

**Inventory Table** (full width below)
- Hard-bordered Ant Table with styled overrides
- Table header: black background, white text, all-caps
- Row borders: 2px solid, alternating row backgrounds (white / light yellow #FFFBE6)
- Status column: colored block tags (no border-radius, hard edges)
- Stock level: chunky progress bars (solid color, hard edges, no rounded caps)
- Row hover: hard shadow on the row + slight translateX

**Demand Forecast** (full width below table)
- Electric blue header block
- Monospace data, hard-bordered tags for trends
- Confidence: colored blocks (green/yellow/red squares)

### Modals (Adjust / Restock / Batch)
- White background, hard 4px black border, hard shadow (10px offset)
- Modal header: all-caps, heavy weight, black background with white text
- Buttons: chunky, hard-bordered, hard-shadow, uppercase text
- Form fields: hard-bordered inputs, no border-radius, monospace values

## Technical Constraints

- **MUST use existing API endpoints** — no new backend code
- **MUST use existing types** from `frontend/src/types/`
- **MUST keep ALL existing functionality**: KPI overview, restock suggestions, dead stock, inventory table with row selection, batch operations, CSV export, adjust modals, restock modal, demand forecast
- **Recharts** available if needed (not required — current page doesn't use charts)
- **Ant Design 6** primitives for Table, Modal, InputNumber, Select, Progress — style them aggressively via CSS overrides
- **Pure CSS** for neo-brutalist effects — no new npm dependencies
- **Use CSS custom properties** for the brutalist tokens
- **Responsive**: primary at 1440px, hard borders and shadows hold up at 1024px
- **Keep file under 800 lines** — extract sub-components or CSS if needed
- **Dark/light**: primary design is light (warm off-white), dark mode can invert

## What NOT to Do

- Don't change API calls or data fetching logic
- Don't remove existing functionality (adjust, batch, export, restock, forecast)
- Don't add new npm dependencies
- Don't use inline styles — extract to a co-located CSS file (`inventory/styles.css` or similar)
- Don't make it clean or refined — the rawness is the point
- Don't use rounded corners, soft shadows, or gradients
- Don't use glassmorphism effects

## Success Looks Like

A page that makes someone say "this looks like a high-end streetwear brand designed an ERP" — bold, confrontational, impossible to ignore. The hard borders and raw typography make inventory data feel important and urgent. Every number lands with weight. The design communicates: "this is real inventory, real money, pay attention."
