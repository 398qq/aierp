import { describe, expect, it } from "vitest";

import { getProductOptionLabel } from "../pages/sales/salesUi";
import type { Product } from "../types";

const product = (overrides: Partial<Product>): Product => ({
  id: 1,
  sku: null,
  name: "STM32F103C8T6",
  mpn: null,
  barcode: null,
  hs_code: null,
  origin_country: null,
  brand_id: null,
  brand_name: null,
  category: null,
  package_type: null,
  package_case: null,
  pin_count: null,
  voltage_rating: null,
  tolerance_pct: null,
  temperature_range: null,
  power_rating: null,
  specs: null,
  unit: null,
  length_mm: null,
  width_mm: null,
  height_mm: null,
  gross_weight_g: null,
  net_weight_g: null,
  tax_rate: null,
  currency: "CNY",
  standard_cost: null,
  list_price: null,
  wholesale_price: null,
  lifecycle_status: null,
  eol_date: null,
  alternative_mpn: null,
  rohs_compliant: true,
  reach_compliant: false,
  esd_sensitive: false,
  msl_level: null,
  datasheet_url: null,
  rohs_cert_url: null,
  reach_cert_url: null,
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
