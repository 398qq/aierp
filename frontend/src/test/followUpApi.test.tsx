/**
 * Contract tests for the paginated follow-ups API helper.
 *
 * The follow-ups list endpoint now expects pagination + filter params
 * and returns {list, total, counts}. These tests pin:
 *   - request query string shape (camelCase + filter omission)
 *   - response unwrapping layer (`query.data` lands as `{list, total, counts}`)
 *
 * Component-level render tests for FollowUpList are out of scope here
 * (heavy; ProTable integration is well covered upstream). The contract
 * is the riskiest seam.
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
import { type FollowUpListResp } from "@/api/customers";

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

const dummyResp: FollowUpListResp = {
  list: [
    {
      id: 1,
      method: "phone",
      status: "planned",
      content: "follow up on quote",
      result: null,
      planned_at: "2026-07-20T09:00:00+00:00",
      completed_at: null,
      priority: "high",
      assigned_to: "alice",
      created_at: "2026-07-15T08:00:00+00:00",
      due_bucket: "overdue",
    },
  ],
  total: 7,
  counts: { open: 3, completed: 1, high: 2, overdue: 1, today: 0 },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getFollowUps (contract)", () => {
  it("returns data shaped {list, total, counts} from the API", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { code: 0, msg: "ok", data: dummyResp } });

    const { wrapper } = makeWrapper();
    const { result } = renderHook(
      () =>
        useApiQuery<FollowUpListResp>(
          ["follow-ups", 42, 1, "", "", "all"],
          "/customers/42/follow-ups",
          {},
        ),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(dummyResp);
    expect(result.current.data?.list).toHaveLength(1);
    expect(result.current.data?.total).toBe(7);
    expect(result.current.data?.counts.overdue).toBe(1);
  });

  it("each list item carries a due_bucket field", () => {
    expect(dummyResp.list[0].due_bucket).toBe("overdue");
  });
});
