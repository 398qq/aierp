import { describe, expect, it } from "vitest";

import { getProductOptionLabel } from "../pages/sales/salesUi";
import type { Product } from "../types";

const product = (overrides: Partial<Product>): Product => ({
  id: 1,
  sku: null,
  name: "STM32F103C8T6",
  brand_id: null,
  brand_name: null,
  category: null,
  package_type: null,
  specs: null,
  unit: null,
  notes: null,
  image_url: null,
  created_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

describe("sales product select", () => {
  it("uses the global product name as the option label", () => {
    expect(getProductOptionLabel(product({
      sku: "MCU-001",
      brand_name: "ST",
      package_type: "LQFP-48",
    }))).toBe("STM32F103C8T6");
  });

  it("keeps product names visible when optional fields are empty", () => {
    expect(getProductOptionLabel(product({ name: "无品牌物料" }))).toBe("无品牌物料");
  });
});
