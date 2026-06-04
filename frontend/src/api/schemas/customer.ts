/** Zod schemas for customer-domain API responses.

Pilot (v6.3): the highest-leverage type — `Customer` — is
defined here. The `Customer` type is the most-called domain
type in the codebase (6+ endpoints import it), and historically
was relied on as a static type without runtime validation.

Adding more types: copy the `customerSchema` shape, change
field types as needed, export. No new patterns to learn.

**Why not just keep the TypeScript interface?**

The audit's pain point was the `Record<string, unknown>` escape
hatch and the lack of runtime validation. A backend bug that
returns a missing `name` field would TypeScript-check fine
(TS trusts the declared type) and only crash at the render
step with a confusing error. With zod:

- TypeScript still infers the correct shape via `z.infer`
- Runtime: malformed responses throw a clear validation error
  with the exact field path
- The `z.string().nullable()` syntax makes the `null` /
  `string` / `string | null` decision explicit per-field,
  which the static `T | null` declaration doesn't
*/

import { z } from "zod";

// ---------------------------------------------------------------------------
// Customer (the most-called domain type)
// ---------------------------------------------------------------------------

export const customerSchema = z.object({
  id: z.number(),
  code: z.string().nullable(),
  name: z.string(),
  short_name: z.string().nullable(),
  contact_person: z.string().nullable(),
  phone: z.string().nullable(),
  email: z.string().nullable(),
  address: z.string().nullable(),
  industry: z.string().nullable(),
  level: z.string().nullable(),
  source: z.string().nullable(),
  notes: z.string().nullable(),
  customer_type: z.string().nullable(),
  region: z.string().nullable(),
  credit_limit: z.number().nullable(),
  credit_level: z.string().nullable(),
  lifecycle: z.string().nullable(),
  last_contacted_at: z.string().nullable(),
  created_at: z.string(),
  owner: z.string().nullable(),
  parent_id: z.number().nullable(),
  health_score: z.number().nullable(),
  health_label: z.string().nullable(),
});

/** Inferred TS type — should match the existing `Customer` interface
 * in `types/index.ts`. If they diverge, the `schemaMatchesType`
 * test in `src/test/zod.test.ts` will fail.
 */
export type CustomerZ = z.infer<typeof customerSchema>;

// ---------------------------------------------------------------------------
// CustomerInsight — the worst `Record<string, unknown>` offender
// (was: `customer: Record<string, unknown>` in the static type).
// The backend's `customer` payload is the same shape as `Customer`
// with `id` + `name` guaranteed.
// ---------------------------------------------------------------------------

export const customerInsightSchema = z.object({
  customer: customerSchema,
  order_summary: z.object({
    total_orders: z.number(),
    total_amount: z.number(),
    avg_order_amount: z.number(),
    last_order_date: z.string().nullable(),
  }),
  product_distribution: z.array(
    z.object({
      product_id: z.number(),
      product_name: z.string(),
      quantity: z.number(),
      amount: z.number(),
    }),
  ),
  followup_summary: z.object({
    total_followups: z.number(),
    last_followup: z.string().nullable(),
    pending_count: z.number(),
    overdue_count: z.number(),
  }),
  opportunity_summary: z.object({
    total: z.number(),
    active: z.number(),
    won: z.number(),
    win_probability: z.number(),
  }),
  suggestions: z.array(z.string()),
});

export type CustomerInsightZ = z.infer<typeof customerInsightSchema>;

// ---------------------------------------------------------------------------
// Customer Create / Update input
// ---------------------------------------------------------------------------

/** Required fields for a new customer. Everything else is optional
 * and can be set later via update. The schema intentionally does
 * NOT validate business rules (e.g. unique `name`) — that's the
 * backend's job, the frontend just sends what the user typed. */
export const createCustomerInputSchema = z.object({
  name: z.string().min(1, "客户名称不能为空"),
  code: z.string().nullable().optional(),
  short_name: z.string().nullable().optional(),
  contact_person: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  address: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
  level: z.string().nullable().optional(),
  source: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  customer_type: z.string().nullable().optional(),
  region: z.string().nullable().optional(),
  credit_limit: z.number().nullable().optional(),
  credit_level: z.string().nullable().optional(),
});

export type CreateCustomerInputZ = z.infer<typeof createCustomerInputSchema>;
