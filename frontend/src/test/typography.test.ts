import { describe, expect, it } from "vitest";

import { fontSize, lineHeight } from "../design-tokens";

describe("ERP typography standard", () => {
  it("keeps the operational hierarchy readable and compact", () => {
    expect(fontSize.headingLg).toBe(24);
    expect(fontSize.headingMd).toBe(20);
    expect(fontSize.section).toBe(16);
    expect(fontSize.body).toBe(14);
    expect(fontSize.table).toBe(13);
    expect(fontSize.tableHeader).toBe(12);
    expect(fontSize.caption).toBe(12);
    expect(fontSize.metric).toBe(24);
  });

  it("uses tighter line height for dense records than body copy", () => {
    expect(lineHeight.compact).toBeLessThan(lineHeight.body);
    expect(lineHeight.heading).toBeLessThan(lineHeight.compact);
  });
});
