import { describe, expect, it } from "vitest";
import routeSource from "../routes/AppRoutes.tsx?raw";

describe("brand routes", () => {
  it("registers the brand dashboard before the dynamic brand detail route", () => {
    const dashboardRoute = routeSource.indexOf('path: "/brands/stats"');
    const detailRoute = routeSource.indexOf('path: "/brands/:id"');

    expect(dashboardRoute).toBeGreaterThan(-1);
    expect(detailRoute).toBeGreaterThan(-1);
    expect(dashboardRoute).toBeLessThan(detailRoute);
    expect(routeSource).toContain('import("../pages/brands/BrandDashboard")');
  });
});
