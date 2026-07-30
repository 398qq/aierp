/**
 * Tests for src/lib/queries — useApiQuery / useApiMutation.
 * Twenty list pages depend on these hooks; this guards the contract:
 *  - useApiQuery unwraps the backend {code,msg,data} envelope
 *  - useApiQuery returns the parsed inner body on success
 *  - useApiMutation auto-invalidates the given keys on success
 *  - useApiMutation does NOT invalidate on failure
 *  - useApiMutation URL fn receives variables, builds final path
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useApiQuery, useApiMutation } from "@/lib/queries";

vi.mock("@/api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import client from "@/api/client";
const mockedClient = client as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.resetAllMocks();
});

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, qc };
}

describe("useApiQuery envelope unwrap", () => {
  it("returns inner data on success (unwraps envelope)", async () => {
    const inner = { list: [{ id: 1 }], total: 1 };
    mockedClient.get.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: inner },
    });

    const { wrapper } = makeWrapper();
    const { result } = renderHook(
      () =>
        useApiQuery<typeof inner>(
          ["demo"],
          "/demo",
          { foo: "bar" },
        ),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Caller sees the inner body — not the envelope
    expect(result.current.data).toEqual(inner);
    expect(result.current.data?.list).toHaveLength(1);
  });

  it("forwards error state when the request rejects", async () => {
    mockedClient.get.mockRejectedValueOnce(new Error("boom"));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useApiQuery(["demo"], "/demo"), { wrapper });
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
