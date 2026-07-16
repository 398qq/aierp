import { describe, expect, it } from "vitest";

import { getSalesOrderStatusOptions } from "../pages/sales/salesOrderStatus";

const values = (status: string, isEdit = true) =>
  getSalesOrderStatusOptions(status, isEdit).map((option) => option.value);

describe("sales order status options", () => {
  it("does not allow a draft order to jump directly to shipped", () => {
    expect(values("draft")).toEqual(["draft", "confirmed", "cancelled"]);
    expect(values("draft")).not.toContain("shipped");
  });

  it("allows a confirmed order to move into shipment", () => {
    expect(values("confirmed")).toEqual([
      "confirmed",
      "partially_shipped",
      "shipped",
      "cancelled",
    ]);
  });

  it("creates new orders as pending", () => {
    expect(values("pending", false)).toEqual(["pending"]);
  });
});
