/**
 * Tests for src/lib/queries — useApiQuery / useApiMutation.
 * Twenty list pages depend on these hooks; this guards the contract:
 *  - useApiQuery returns the parsed body on success
 *  - useApiMutation auto-invalidates the given keys on success
 *  - useApiMutation does NOT invalidate on failure
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useApiQuery, useApiMutation } from "@/lib/queries";

// Mock the axios client that queries.ts wraps. Only the methods we use are stubbed.
vi.mock("@/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import client from "@/api/client";
const mockedClient = client as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, qc };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("useApiQuery", () => {
  it("returns resp.data on success", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { list: [{ id: 1 }], total: 1 } });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(
      () => useApiQuery<{ list: { id: number }[]; total: number }>(
        ["demo"],
        "/demo",
        { foo: "bar" },
      ),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ list: [{ id: 1 }], total: 1 });
    expect(mockedClient.get).toHaveBeenCalledWith(
      "/demo",
      expect.objectContaining({ params: { foo: "bar" } }),
    );
  });

  it("surfaces error state when the request rejects", async () => {
    mockedClient.get.mockRejectedValueOnce(new Error("boom"));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(
      () => useApiQuery(["demo"], "/demo"),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });
});

describe("useApiMutation", () => {
  it("invalidates the given keys on success", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { id: 9 } });
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(
      () =>
        useApiMutation<unknown, { name: string }>("post", "/things", {
          invalidateKeys: [["things"], ["things", "list"]],
        }),
      { wrapper },
    );

    await result.current.mutateAsync({ name: "x" });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["things"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["things", "list"] });
  });

  it("does NOT invalidate on failure", async () => {
    mockedClient.post.mockRejectedValueOnce(new Error("boom"));
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(
      () =>
        useApiMutation("post", "/things", {
          invalidateKeys: [["things"]],
          onError: () => undefined,
        }),
      { wrapper },
    );

    await expect(result.current.mutateAsync({})).rejects.toThrow("boom");
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("supports a URL function that receives the variables", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { id: 42 } });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(
      () =>
        useApiMutation<unknown, { id: number }>(
          "post",
          (vars) => `/things/${vars.id}/approve`,
        ),
      { wrapper },
    );

    await result.current.mutateAsync({ id: 42 });
    expect(mockedClient.post).toHaveBeenCalledWith(
      "/things/42/approve",
      expect.objectContaining({ id: 42 }),
    );
  });
});