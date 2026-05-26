import { describe, expect, it } from "vitest";
import appSource from "../App.tsx?raw";

describe("brand routes", () => {
  it("registers the brand dashboard before the dynamic brand detail route", () => {
    const dashboardRoute = appSource.indexOf('path="/brands/stats"');
    const detailRoute = appSource.indexOf('path="/brands/:id"');

    expect(dashboardRoute).toBeGreaterThan(-1);
    expect(detailRoute).toBeGreaterThan(-1);
    expect(dashboardRoute).toBeLessThan(detailRoute);
    expect(appSource).toContain('import("./pages/brands/BrandDashboard")');
  });
});
