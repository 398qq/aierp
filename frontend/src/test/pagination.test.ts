import { describe, expect, it } from "vitest";

import {
  ERP_PAGE_SIZE,
  ERP_PAGE_SIZE_OPTIONS,
  erpPagination,
} from "../ui/pagination";

describe("ERP pagination standard", () => {
  it("uses the shared page size, selector options and quick jumper", () => {
    const pagination = erpPagination();

    expect(ERP_PAGE_SIZE).toBe(20);
    expect(ERP_PAGE_SIZE_OPTIONS).toEqual([20, 50, 100]);
    expect(pagination.pageSize).toBe(20);
    expect(pagination.pageSizeOptions).toEqual([20, 50, 100]);
    expect(pagination.showSizeChanger).toBe(true);
    expect(pagination.showQuickJumper).toBe(true);
  });

  it("formats the visible range and total in Chinese ERP copy", () => {
    const pagination = erpPagination();

    expect(pagination.showTotal?.(118, [1, 20])).toBe(
      "第 1-20 条 / 共 118 条",
    );
    expect(pagination.locale).toMatchObject({
      items_per_page: "条/页",
      jump_to: "跳至",
      page: "页",
    });
  });

  it("allows controlled server pagination to override defaults", () => {
    const onChange = () => undefined;
    const pagination = erpPagination({
      current: 3,
      pageSize: 50,
      total: 230,
      onChange,
    });

    expect(pagination).toMatchObject({
      current: 3,
      pageSize: 50,
      total: 230,
      onChange,
    });
  });
});
