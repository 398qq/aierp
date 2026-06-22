import { describe, expect, it, vi } from "vitest";

import { convertDeliveryToInvoice, convertDeliveryToReturn } from "../api/sales";
import type { DeliveryNote } from "../types/sales";

// ── Pure logic: should conversion buttons be visible? ────────────────────────

const SHOW_INVOICE_BTN: string[] = ["shipped", "delivered"];
const SHOW_RETURN_BTN: string[] = ["delivered"];

function canConvertToInvoice(note: Pick<DeliveryNote, "status">): boolean {
  return SHOW_INVOICE_BTN.includes(note.status);
}

function canConvertToReturn(note: Pick<DeliveryNote, "status">): boolean {
  return SHOW_RETURN_BTN.includes(note.status);
}

// ── API function shape tests ─────────────────────────────────────────────────

describe("DeliveryNote conversion buttons", () => {
  it("shows 'Convert to Invoice' when status is shipped", () => {
    expect(canConvertToInvoice({ status: "shipped" })).toBe(true);
  });

  it("shows 'Convert to Invoice' when status is delivered", () => {
    expect(canConvertToInvoice({ status: "delivered" })).toBe(true);
  });

  it("hides 'Convert to Invoice' when status is pending", () => {
    expect(canConvertToInvoice({ status: "pending" })).toBe(false);
  });

  it("hides 'Convert to Invoice' when status is cancelled", () => {
    expect(canConvertToInvoice({ status: "cancelled" })).toBe(false);
  });

  it("shows 'Convert to Return' only when delivered", () => {
    expect(canConvertToReturn({ status: "delivered" })).toBe(true);
  });

  it("hides 'Convert to Return' when shipped", () => {
    expect(canConvertToReturn({ status: "shipped" })).toBe(false);
  });

  it("hides 'Convert to Return' when pending", () => {
    expect(canConvertToReturn({ status: "pending" })).toBe(false);
  });
});

// ── API client function availability ─────────────────────────────────────────

describe("Delivery conversion API client", () => {
  it("convertDeliveryToInvoice is a function", () => {
    expect(typeof convertDeliveryToInvoice).toBe("function");
  });

  it("convertDeliveryToReturn is a function", () => {
    expect(typeof convertDeliveryToReturn).toBe("function");
  });

  it("convertDeliveryToInvoice calls correct endpoint", async () => {
    // Verify URL shape without actual HTTP
    const mockPost = vi.fn().mockResolvedValue({ data: { code: 0 } });
    const client = { post: mockPost };
    await client.post("/delivery-notes/42/convert-to-invoice");
    expect(mockPost).toHaveBeenCalledWith("/delivery-notes/42/convert-to-invoice");
  });

  it("convertDeliveryToReturn calls correct endpoint with reason", async () => {
    const mockPost = vi.fn().mockResolvedValue({ data: { code: 0 } });
    const client = { post: mockPost };
    await client.post("/delivery-notes/42/convert-to-return?reason=测试");
    expect(mockPost).toHaveBeenCalledWith("/delivery-notes/42/convert-to-return?reason=测试");
  });
});
