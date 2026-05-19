import { describe, expect, it } from "vitest";

import { generateCustomerShortName } from "../pages/customers/CustomerForm";
import { getDefaultCustomerOwner } from "../pages/customers/CustomerNew";

describe("generateCustomerShortName", () => {
  it("removes common company suffixes from customer names", () => {
    expect(generateCustomerShortName("深圳市星河电子有限公司")).toBe("深圳市星河电子");
    expect(generateCustomerShortName("上海星河电子股份有限公司")).toBe("上海星河电子");
  });

  it("normalizes spaces and bracketed notes before generating", () => {
    expect(generateCustomerShortName("  深圳市 星河电子（华南办）有限公司  ")).toBe("深圳市星河电子");
  });

  it("keeps plain names usable as short names", () => {
    expect(generateCustomerShortName("星河电子")).toBe("星河电子");
  });
});

describe("getDefaultCustomerOwner", () => {
  it("uses the current logged-in username as the default owner", () => {
    expect(getDefaultCustomerOwner(" sales01 ")).toBe("sales01");
  });

  it("does not produce an owner when the user is unavailable", () => {
    expect(getDefaultCustomerOwner(null)).toBe("");
    expect(getDefaultCustomerOwner("")).toBe("");
  });
});
