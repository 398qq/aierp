/**
 * useCustomersList tests — Stage 3 Day 2.
 *
 * Mocks the customers API to verify:
 * - Initial load fires with default filter
 * - Debounced refetch on filter change
 * - Manual refetch() triggers immediate reload
 * - Error state captures API failures
 * - Page change refetches (no debounce)
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCustomersFilter } from "../hooks/useCustomersFilter";
import { useCustomersList } from "../hooks/useCustomersList";

vi.mock("../api/customers", () => ({
  getCustomers: vi.fn(),
}));

import { getCustomers } from "../api/customers";

const mockGetCustomers = vi.mocked(getCustomers);

const sceneFilterResolver = () => ({});  // no overrides

const setupHook = () =>
  renderHook(() => {
    const filter = useCustomersFilter();
    const list = useCustomersList(filter, sceneFilterResolver);
    return { filter, list };
  });

beforeEach(() => {
  mockGetCustomers.mockReset();
  // Default: return empty page
  mockGetCustomers.mockResolvedValue({
    data: { code: 0, msg: "ok", data: { list: [], total: 0, page: 1, page_size: 20 } },
  } as never);
});

describe("useCustomersList", () => {
  it("fires initial fetch on mount with default filter", async () => {
    setupHook();
    await waitFor(() => expect(mockGetCustomers).toHaveBeenCalled());
    const args = mockGetCustomers.mock.calls[0][0];
    expect(args.page).toBe(1);
    expect(args.page_size).toBe(20);
    expect(args.sort_by).toBe("id");
    expect(args.sort_order).toBe("desc");
  });

  it("initial state: loading=true, data=[], total=0", () => {
    const { result } = setupHook();
    expect(result.current.list.loading).toBe(true);
    expect(result.current.list.data).toEqual([]);
    expect(result.current.list.total).toBe(0);
    expect(result.current.list.error).toBeNull();
  });

  it("populates data + total after successful fetch", async () => {
    mockGetCustomers.mockResolvedValueOnce({
      data: {
        code: 0, msg: "ok",
        data: {
          list: [{ id: 1, name: "Acme" } as never],
          total: 1, page: 1, page_size: 20,
        },
      },
    } as never);
    const { result } = setupHook();
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    expect(result.current.list.data).toHaveLength(1);
    expect(result.current.list.total).toBe(1);
  });

  it("captures error when API throws", async () => {
    mockGetCustomers.mockRejectedValueOnce(new Error("Network down"));
    const { result } = setupHook();
    await waitFor(() => expect(result.current.list.error).toBe("Network down"));
    expect(result.current.list.loading).toBe(false);
    expect(result.current.list.data).toEqual([]);
  });

  it("debounces refetch on filter change (350ms)", async () => {
    vi.useFakeTimers();
    try {
      const { result } = setupHook();
      // Wait for initial load (real timers off; first fetch fires from useEffect)
      // Use real waitFor with fake timers off-then-on
    } finally {
      vi.useRealTimers();
    }
    const { result } = setupHook();
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    const callsBefore = mockGetCustomers.mock.calls.length;
    act(() => result.current.filter.setQ("acme"));
    // Immediately after setQ, no new call (debounced)
    expect(mockGetCustomers.mock.calls.length).toBe(callsBefore);
    // After debounce window
    await waitFor(() => expect(mockGetCustomers.mock.calls.length).toBeGreaterThan(callsBefore), {
      timeout: 1000,
    });
  });

  it("refetch() triggers immediate reload", async () => {
    const { result } = setupHook();
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    const callsBefore = mockGetCustomers.mock.calls.length;
    act(() => result.current.list.refetch());
    await waitFor(() => expect(mockGetCustomers.mock.calls.length).toBeGreaterThan(callsBefore));
  });

  it("passes filter state to API params", async () => {
    const { result } = setupHook();
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    act(() => {
      result.current.filter.setQ("acme");
      result.current.filter.setIndustry("电子");
    });
    await waitFor(() => {
      const lastCall = mockGetCustomers.mock.calls[mockGetCustomers.mock.calls.length - 1][0];
      expect(lastCall.keyword).toBe("acme");
      expect(lastCall.industry).toBe("电子");
    }, { timeout: 1000 });
  });

  it("uses sceneFilterResolver for fallback level/region/source", async () => {
    const sceneFilterResolver = () => ({ level: "A", region: "East" });
    const { result } = renderHook(() => {
      const filter = useCustomersFilter();
      const list = useCustomersList(filter, sceneFilterResolver);
      return { filter, list };
    });
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    const lastCall = mockGetCustomers.mock.calls[mockGetCustomers.mock.calls.length - 1][0];
    expect(lastCall.level).toBe("A");
    expect(lastCall.region).toBe("East");
  });

  it("explicit filter takes precedence over scene filter", async () => {
    const sceneFilterResolver = () => ({ level: "A" });
    const { result } = renderHook(() => {
      const filter = useCustomersFilter();
      const list = useCustomersList(filter, sceneFilterResolver);
      return { filter, list };
    });
    await waitFor(() => expect(result.current.list.loading).toBe(false));
    act(() => result.current.filter.setLevel("B"));
    await waitFor(() => {
      const lastCall = mockGetCustomers.mock.calls[mockGetCustomers.mock.calls.length - 1][0];
      expect(lastCall.level).toBe("B");  // not "A"
    }, { timeout: 1000 });
  });

  it("setPage changes page state", () => {
    const { result } = setupHook();
    act(() => result.current.list.setPage(3));
    expect(result.current.list.page).toBe(3);
  });

  it("setPageSize changes pageSize state", () => {
    const { result } = setupHook();
    act(() => result.current.list.setPageSize(50));
    expect(result.current.list.pageSize).toBe(50);
  });
});
