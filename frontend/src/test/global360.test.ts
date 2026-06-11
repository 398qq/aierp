import { describe, expect, it } from "vitest";

import { normalizeGlobal360 } from "../api/ai";
import type { Global360 } from "../types";

describe("normalizeGlobal360", () => {
  it("flattens the new insights response for dashboard consumers", () => {
    const payload = {
      scanned_at: "2026-06-10T00:00:00Z",
      enterprise_health_score: 0,
      executive_summary: "",
      top_opportunities: [],
      top_risks: [],
      cross_domain_correlations: [],
      strategic_recommendations: [],
      kpi_health: [],
      focus_areas: [],
      ai_available: false,
      insights: {
        enterprise_health_score: 72,
        executive_summary: "经营总体稳定",
        top_opportunities: [],
        top_risks: [],
        cross_domain_correlations: [],
        strategic_recommendations: [],
        kpi_health: [],
        focus_areas: ["回款"],
      },
    } satisfies Global360;

    const result = normalizeGlobal360(payload);

    expect(result.enterprise_health_score).toBe(72);
    expect(result.executive_summary).toBe("经营总体稳定");
    expect(result.focus_areas).toEqual(["回款"]);
    expect(result.ai_available).toBe(false);
  });
});
