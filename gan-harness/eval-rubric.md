# GAN Design Evaluation Rubric — Neo-Brutalist Inventory

## Design Quality (weight: 0.35)

| Score | Criteria |
|-------|----------|
| 0-3 | Generic Ant Design with black borders slapped on. Not brutalist — just ugly. No design system. |
| 4-6 | Some brutalist elements but inconsistent. A few hard borders, some bold text, but still reads as "default table with CSS tweaks." |
| 7-8 | Strong neo-brutalist execution. Consistent hard borders, hard shadows, bold typography throughout. Color blocks create clear information hierarchy. Every element feels intentional. |
| 9-10 | Museum-worthy. The brutalist language enhances data comprehension — the hardness makes inventory feel tangible. Every pixel feels placed. You'd show this in a design conference talk. |

### Sub-criteria:
- Does the brutalist aesthetic improve data scanning or just decorate?
- Are hard borders and shadows used consistently (same border width, same shadow offset)?
- Do color blocks serve semantic purpose (yellow=KPI, red=alert, blue=info)?
- Is text readable against all colored blocks (sufficient contrast)?
- Do interactive elements (buttons, rows, modals) have clear brutalist hover/focus states?

## Originality (weight: 0.30)

| Score | Criteria |
|-------|----------|
| 0-3 | Direct copy of a "neo-brutalism CSS tutorial" — yellow cards, black borders, nothing specific to inventory or AIERP. |
| 4-6 | Standard brutalist patterns with minor customization. Recognizable as "a brutalist page" but not "the AIERP brutalist inventory page." |
| 7-8 | Distinctive choices — unexpected color blocking, creative table treatment, layout that breaks grid in smart ways. Feels designed for THIS product. |
| 9-10 | Breakthrough. Combines brutalist rawness with something unexpected — maybe the table becomes a visual statement, maybe the KPI cards have a unique treatment, maybe the typography does something bold. Memorable and unmistakably AIERP. |

### Sub-criteria:
- Would you remember this inventory page among 10 other brutalist designs?
- Is there at least one "whoa" moment — a design choice that surprises and delights?
- Does it avoid brutalist clichés (just yellow+black, just thick borders)?
- Does the design reference industrial/warehouse aesthetics in creative ways?
- Is the page title treatment bold and memorable?

## Craft (weight: 0.25)

| Score | Criteria |
|-------|----------|
| 0-3 | Sloppy execution — broken borders, misaligned shadows, text overflow, broken layouts. |
| 4-6 | Clean execution but standard. Brutalist effects work but no refinement. |
| 7-8 | Polished execution. Perfect border alignment, consistent shadow offsets, proper spacing rhythm. Animations (hover states) feel intentional. The "rawness" is clearly designed, not accidental. |
| 9-10 | Pixel-perfect. Every hard shadow aligns, every border meets at clean corners, every color block has proper padding. Hover/focus/active states designed. Loading/empty states styled. TypeScript clean. |

### Sub-criteria:
- Border treatment: do hard borders meet cleanly at corners (no gaps)?
- Shadows: consistent offset, no blur, correct stacking?
- Typography: proper tabular-nums, consistent weights, no orphan text?
- Spacing: generous and rhythmic — hard borders need breathing room?
- Code quality: CSS in co-located file, custom properties for tokens, no inline styles?
- Responsive: does the brutalist aesthetic hold at 1024px?
- Loading/empty/error states designed in brutalist style?

## Functionality (weight: 0.10)

| Score | Criteria |
|-------|----------|
| 0-3 | Broken — table doesn't render, data doesn't load, modals fail, export broken. |
| 4-6 | Mostly works but some features missing or broken (batch select, adjust modal, etc.). |
| 7-8 | All features functional: KPI cards, restock/DEAD stock lists, inventory table with row selection, batch operations, CSV export, 3 modals, demand forecast. All API calls work. |
| 9-10 | Everything works perfectly. TypeScript clean, no console errors. All states (loading, empty, error) handled. Existing behavior preserved exactly. |

### Sub-criteria:
- All existing API calls still work (getInventory, getInventoryOverview, adjustInventory, batchAdjustInventory, getDemandForecast, createPOFromRestock, getSuppliers)?
- Inventory table row selection + batch operations functional?
- CSV export works (both selected and all)?
- Adjust modal works (single product)?
- Restock modal works (supplier select + quantity edit)?
- Demand forecast table renders?
- TypeScript compiles without errors?
- No runtime errors?

---

## Scoring Formula

```
final_score = (design_quality * 0.35) + (originality * 0.30) + (craft * 0.25) + (functionality * 0.10)
```

**Pass threshold: 7.5** — higher than gan-build because design mode prioritizes visual excellence.

**Evaluator mindset**: "Would this win a design award for enterprise SaaS?" The brutalist aesthetic must be intentional, consistent, and enhance the data — not just a CSS gimmick. If it reads as "trying too hard" or "just ugly," push the score lower and provide specific feedback.

**To the Generator**: Your PRIMARY goal is visual excellence. A stunning neo-brutalist half-finished app beats a functional but safe Ant Design page. Push for creative leaps — unexpected color blocking, custom table treatments, bold typographic statements. The data serves the design, not the other way around.
