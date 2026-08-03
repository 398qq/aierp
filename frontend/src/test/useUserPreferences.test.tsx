/**
 * Tests for useUserPreferences hook contract.
 *
 * Pins:
 *  - GET /user-preferences/{scope} envelope is unwrapped
 *  - PUT and DELETE on /user-preferences/{scope}/{key}
 *  - Optimistic update on upsert; rollback on failure
 *  - Optimistic delete; rollback on failure
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

vi.mock("@/api/client", () => ({
  default: { get: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));
vi.mock("@/api", async () => {
  const actual = await vi.importActual<typeof import("@/api")>("@/api");
  return { ...actual, getApiErrorMessage: () => "fail" };
});

import client from "@/api/client";
import { useUserPreferences } from "@/lib/useUserPreferences";

const mockedClient = client as unknown as {
  get: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper };
}

const sampleList = (overrides: Record<string, unknown> = {}) => ({
  items: Object.entries(overrides).map(([key, value]) => ({
    scope: "products", key, value: JSON.stringify(value),
  })),
});

beforeEach(() => {
  vi.resetAllMocks();
});

describe("useUserPreferences (contract)", () => {
  it("loads the scope's items into values map (envelope unwrap)", async () => {
    mockedClient.get.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: sampleList({ column_visibility: { amount: false } }) },
    });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserPreferences("products"), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.values["column_visibility"]).toEqual({ amount: false });
  });

  it("upsert is optimistic and calls PUT with JSON-stringified value", async () => {
    mockedClient.get.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: { items: [] } },
    });
    mockedClient.put.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: { scope: "products", key: "k", value: "1" } },
    });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserPreferences("products"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.upsert("k", 1); });
    expect(mockedClient.put).toHaveBeenCalledWith(
      "/user-preferences/products/k",
      expect.objectContaining({ key: "k", value: "1" }),
    );
    expect(result.current.values["k"]).toBe(1);
  });

  it("remove is optimistic and calls DELETE on right key", async () => {
    mockedClient.get.mockResolvedValueOnce({
      data: {
        code: 0,
        msg: "ok",
        data: sampleList({ existing: "x" }),
      },
    });
    mockedClient.delete.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: { msg: "deleted" } },
    });
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserPreferences("products"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.values["existing"]).toBe("x");

    await act(async () => { await result.current.remove("existing"); });
    expect(mockedClient.delete).toHaveBeenCalledWith(
      "/user-preferences/products/existing",
      expect.anything(),
    );
    expect(result.current.values["existing"]).toBeUndefined();
  });

  it("rollback on upsert failure surfaces error", async () => {
    mockedClient.get.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: { items: [] } },
    });
    mockedClient.put.mockRejectedValueOnce(new Error("server 500"));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useUserPreferences("products"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      try { await result.current.upsert("k", 1); } catch { /* expected */ }
    });
    // optimistic set then rollback
    expect(result.current.values["k"]).toBeUndefined();
    expect(result.current.error).toBe("fail");
  });
});
