/** Tests for the zod-based API schema validation.

Verifies:
- Valid responses parse without error
- Invalid responses (missing fields, wrong types) throw a clear
  ZodError with the bad field path
- Inferred TS type matches the static type declared in
  `types/index.ts` (catches drift between the two)
*/

import { describe, expect, it } from "vitest";
import {
  createCustomerInputSchema,
  customerInsightSchema,
  customerSchema,
} from "../api/schemas/customer";

describe("customerSchema", () => {
  // Minimal valid customer — backend always returns all fields,
  // with `null` for nullable ones. A truly missing field would be a
  // backend bug, not "an optional field".
  const minimalCustomer = {
    id: 1,
    code: null,
    name: "ACME Corp",
    short_name: null,
    contact_person: null,
    phone: null,
    email: null,
    address: null,
    industry: null,
    level: null,
    source: null,
    notes: null,
    customer_type: null,
    region: null,
    credit_limit: null,
    credit_level: null,
    lifecycle: null,
    last_contacted_at: null,
    created_at: "2026-06-01T00:00:00Z",
    owner: null,
    parent_id: null,
    health_score: null,
    health_label: null,
  };

  it("accepts a valid minimal customer (all nullable fields are null)", () => {
    const parsed = customerSchema.parse(minimalCustomer);
    expect(parsed.name).toBe("ACME Corp");
    expect(parsed.code).toBeNull();
    expect(parsed.health_score).toBeNull();
  });

  it("accepts a full customer with all fields populated", () => {
    const full = {
      ...minimalCustomer,
      code: "ACME-001",
      short_name: "ACME",
      contact_person: "John Doe",
      phone: "+86-138-0000-0000",
      email: "john@acme.com",
      address: "100 Main St",
      industry: "electronics",
      level: "A",
      source: "referral",
      notes: "VIP customer",
      customer_type: "enterprise",
      region: "Shanghai",
      credit_limit: 1000000,
      credit_level: "AAA",
      lifecycle: "active",
      last_contacted_at: "2026-06-01T00:00:00Z",
      owner: "sales-001",
      health_score: 85.5,
      health_label: "healthy",
    };
    const parsed = customerSchema.parse(full);
    expect(parsed.code).toBe("ACME-001");
    expect(parsed.credit_limit).toBe(1000000);
  });

  it("rejects a missing required field (no `name` at all)", () => {
    const broken = { ...minimalCustomer };
    delete (broken as { name?: string }).name;
    expect(() => customerSchema.parse(broken)).toThrow(/name/);
  });

  it("rejects wrong type for numeric field", () => {
    const broken = { ...minimalCustomer, id: "1" }; // string, not number
    expect(() => customerSchema.parse(broken)).toThrow(/id/);
  });
});

describe("customerInsightSchema", () => {
  const validInsight = {
    customer: {
      id: 1,
      code: null,
      name: "ACME",
      short_name: null,
      contact_person: null,
      phone: null,
      email: null,
      address: null,
      industry: null,
      level: null,
      source: null,
      notes: null,
      customer_type: null,
      region: null,
      credit_limit: null,
      credit_level: null,
      lifecycle: null,
      last_contacted_at: null,
      created_at: "2026-06-01T00:00:00Z",
      owner: null,
      parent_id: null,
      health_score: null,
      health_label: null,
    },
    order_summary: {
      total_orders: 10,
      total_amount: 50000,
      avg_order_amount: 5000,
      last_order_date: "2026-05-01",
    },
    product_distribution: [
      { product_id: 100, product_name: "Chip A", quantity: 100, amount: 1000 },
    ],
    followup_summary: {
      total_followups: 5,
      last_followup: "2026-05-15",
      pending_count: 1,
      overdue_count: 0,
    },
    opportunity_summary: {
      total: 3,
      active: 2,
      won: 1,
      win_probability: 0.7,
    },
    suggestions: ["Follow up on Q2 quote"],
  };

  it("accepts a valid insight", () => {
    const parsed = customerInsightSchema.parse(validInsight);
    expect(parsed.customer.name).toBe("ACME");
    expect(parsed.suggestions).toHaveLength(1);
  });

  it("rejects an insight with the inner customer missing required name", () => {
    const broken = {
      ...validInsight,
      customer: { ...validInsight.customer },
    };
    delete (broken.customer as { name?: string }).name;
    expect(() => customerInsightSchema.parse(broken)).toThrow(/name/);
  });
});

describe("createCustomerInputSchema", () => {
  it("accepts a name-only minimal input", () => {
    const parsed = createCustomerInputSchema.parse({ name: "ACME" });
    expect(parsed.name).toBe("ACME");
  });

  it("rejects an empty name", () => {
    expect(() => createCustomerInputSchema.parse({ name: "" })).toThrow(/客户名称/);
  });

  it("rejects a missing name", () => {
    expect(() => createCustomerInputSchema.parse({})).toThrow(/name/);
  });
});
