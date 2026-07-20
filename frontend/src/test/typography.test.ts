import { describe, expect, it } from "vitest";

import { fontSize, lineHeight, typography } from "../design-tokens";

describe("ERP typography standard", () => {
  it("keeps the operational hierarchy readable and compact", () => {
    expect(fontSize.headingLg).toBe(24);
    expect(fontSize.headingMd).toBe(20);
    expect(fontSize.section).toBe(16);
    expect(fontSize.body).toBe(14);
    expect(fontSize.table).toBe(14);
    expect(fontSize.tableHeader).toBe(13);
    expect(fontSize.caption).toBe(12);
    expect(fontSize.metric).toBe(24);
  });

  it("defines a complete role instead of a standalone font size", () => {
    expect(typography.pageTitle).toEqual({ fontSize: 20, lineHeight: 28, fontWeight: 700 });
    expect(typography.body).toEqual({ fontSize: 14, lineHeight: 22, fontWeight: 400 });
    expect(typography.table).toEqual({ fontSize: 14, lineHeight: 20, fontWeight: 400 });
    expect(typography.supporting).toEqual({ fontSize: 13, lineHeight: 20, fontWeight: 400 });
    expect(typography.caption.fontSize).toBe(12);
  });

  it("uses tighter line height for dense records than body copy", () => {
    expect(lineHeight.compact).toBeLessThan(lineHeight.body);
    expect(lineHeight.heading).toBeLessThan(lineHeight.compact);
  });
});
