import { describe, expect, it } from "vitest";

import {
  findNavigationTarget,
  getMenuItemTarget,
  resolveSelectedNavigationKey,
  searchableNavigationItems,
} from "../navigation/appNavigation";
import { appRoutes } from "../routes/AppRoutes";

describe("application navigation", () => {
  it("selects the most specific menu route for detail pages", () => {
    expect(resolveSelectedNavigationKey("/customers/follow-ups/42")).toBe("/customers/follow-ups");
    expect(resolveSelectedNavigationKey("/sales/orders/42/edit")).toBe("/sales/orders");
  });

  it("finds navigation targets by display name or path", () => {
    expect(findNavigationTarget("记账凭证")).toBe("/finance/journal-entries");
    expect(findNavigationTarget("warehouse/inventory")).toBe("/warehouse/inventory-ledger");
    expect(findNavigationTarget("   ")).toBeUndefined();
  });

  it("does not navigate group headings", () => {
    expect(getMenuItemTarget({ key: "_domain_sales" })).toBeUndefined();
    expect(getMenuItemTarget({ key: "/sales/orders" })).toBe("/sales/orders");
  });

  it("keeps every navigable menu item backed by a registered route", () => {
    const registeredPaths = new Set(
      appRoutes.flatMap((route) => [
        ...(route.path ? [route.path] : []),
        ...(route.children ?? []).flatMap((child) => (child.path ? [child.path] : [])),
      ]),
    );

    expect(
      searchableNavigationItems.map((item) => item.key).filter((key) => !registeredPaths.has(key)),
    ).toEqual([]);
  });
});
