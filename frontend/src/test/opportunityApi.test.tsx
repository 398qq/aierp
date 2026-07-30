/**
 * Contract tests for the opportunity list API helper + useApiQuery
 * envelope-unwrap pattern (consistency with followUpApi.test.tsx).
 *
 * Spec: docs/frontend/opportunity-list-design.md §6.1, §6.4
 *
 * - getOpportunities serializes params correctly (kanban/view/ai)
 * - response shape: list / total / counts.{count,amount,...} / ai|null
 * - useApiQuery unwraps the API envelope so query.data is the
 *   inner OpportunityListResp
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

vi.mock("@/api/client", () => ({
  default: { get: vi.fn() },
}));

import client from "@/api/client";
import { useApiQuery } from "@/lib/queries";
import {
  getOpportunities,
  type OpportunityCounts,
  type OpportunityListResp,
} from "@/api/sales";

const mockedClient = client as unknown as { get: ReturnType<typeof vi.fn> };

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper };
}

const dummyResp: OpportunityListResp = {
  list: [
    {
      id: 1,
      customer_id: 7,
      product_id: null,
      title: "ACME robot expansion",
      description: null,
      status: "active",
      stage: "negotiation",
      notes: null,
      amount: 50000,
      win_probability: 60,
      expected_close_date: "2026-08-15T00:00:00+00:00",
      assigned_to: "alice",
      source: "exhibition",
      created_at: "2026-07-01T00:00:00+00:00",
      updated_at: "2026-07-25T00:00:00+00:00",
    },
  ],
  total: 47,
  page: 1,
  page_size: 200,
  counts: {
    count: 47,
    amount: 250000,
    weightedAmount: 130000,
    active: 32,
    overdue: 4,
    dueSoon: 7,
    atRisk: 3,
  } satisfies OpportunityCounts,
  ai: {
    1: {
      risk_level: "high",
      win_probability: 60,
      next_best_action: "re-engage",
      key_concerns: ["no reply 14d"],
    },
  },
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe("getOpportunities (contract)", () => {
  it("serializes kanban/page/page_size/filter params correctly", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { code: 0, msg: "ok", data: dummyResp } });

    await getOpportunities({
      kanban: "true",
      page: 2,
      page_size: 50,
      status: "active",
      stage: "negotiation",
      q: "ACME",
      customer_id: 7,
      include_ai: "true",
    });

    expect(mockedClient.get).toHaveBeenCalledWith(
      "/opportunities",
      expect.objectContaining({
        params: expect.objectContaining({
          kanban: "true",
          page: 2,
          page_size: 50,
          status: "active",
          stage: "negotiation",
          q: "ACME",
          customer_id: 7,
          include_ai: "true",
        }),
      }),
    );
  });

  it("useApiQuery unwraps envelope so query.data is the inner body", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { code: 0, msg: "ok", data: dummyResp } });

    const { wrapper } = makeWrapper();
    const { result } = renderHook(
      () =>
        useApiQuery<OpportunityListResp>(
          ["opportunities", "board", 1, "", "", "", "", false],
          "/opportunities",
          { kanban: "true" },
        ),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const d = result.current.data;
    expect(d).toBeDefined();
    // Counts — 7 keys, server-aggregated, NOT derived client-side
    expect(d?.counts).toEqual({
      count: 47, amount: 250000, weightedAmount: 130000, active: 32,
      overdue: 4, dueSoon: 7, atRisk: 3,
    });
    expect(d?.total).toBe(47);
    expect(d?.list).toHaveLength(1);
    // AI map keyed by opportunity id
    expect(d?.ai?.[1]?.risk_level).toBe("high");
  });

  it("query key change forces refetch (proves filter change is wired)", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { code: 0, msg: "ok", data: dummyResp } });
    mockedClient.get.mockResolvedValueOnce({
      data: { code: 0, msg: "ok", data: { ...dummyResp, total: 99 } },
    });

    const { wrapper } = makeWrapper();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    const { result, rerender } = renderHook(
      ({ k }) =>
        useApiQuery<OpportunityListResp>(
          ["opportunities", ...k],
          "/opportunities",
          { page: k[0] },
        ),
      { wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>, initialProps: { k: [1] as number[] } },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(47);

    // Change the key — must refetch
    rerender({ k: [2] });
    await waitFor(() => expect(result.current.data?.total).toBe(99));
    expect(mockedClient.get).toHaveBeenCalledTimes(2);
  });
});
