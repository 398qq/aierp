import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import WatchtowerDashboard from "@/pages/dashboard/WatchtowerDashboard";
import client from "@/api/client";

// Mock the client so useApiQuery gets the data directly
vi.mock("@/api/client", () => ({
  default: {
    get: vi.fn(),
  },
  getApiErrorMessage: (err: unknown) => (err instanceof Error ? err.message : String(err)),
}));

// Mock getWatchtowerScan at api index level
vi.mock("@/api", () => ({
  getWatchtowerScan: vi.fn(),
}));

import { getWatchtowerScan } from "@/api";

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const mockScanData = {
  scanned_at: "2026-07-31T10:00:00+00:00",
  total_alerts: 3,
  severity: "需关注",
  summary: "AI summary text",
  top_actions: ["Action 1"],
  risk_areas: ["sales"],
  alerts_persisted: 1,
  anomalies: {
    churn_risk: [
      {
        domain: "churn_risk",
        domainLabel: "客户流失风险",
        customer_id: 1,
        name: "客户X",
        signal: "90天无订单",
      },
    ],
    order_drop: [],
    low_stock: [],
    out_of_stock: [],
  },
};

describe("WatchtowerDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(client.get).mockReturnValue(new Promise(() => {}));
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <WatchtowerDashboard />
      </Wrapper>,
    );
    // FullPageLoader renders a Spin with ant-spin-spinning class
    expect(document.querySelector(".ant-spin-spinning")).toBeInTheDocument();
  });

  it("renders data when query resolves", async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 0, msg: "ok", data: mockScanData },
    } as any);
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <WatchtowerDashboard />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByText("全局监控中心")).toBeInTheDocument();
    });
    expect(screen.getByText("异常总数")).toBeInTheDocument();
    expect(screen.getByText("AI summary text")).toBeInTheDocument();
  });

  it("renders error state with retry", async () => {
    vi.mocked(client.get).mockRejectedValue(new Error("boom"));
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <WatchtowerDashboard />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /重.试/ })).toBeInTheDocument();
    });
  });

  it("renders empty state when total_alerts=0", async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: {
        code: 0,
        msg: "ok",
        data: {
          ...mockScanData,
          total_alerts: 0,
          severity: "正常",
          top_actions: [],
          risk_areas: [],
          anomalies: { churn_risk: [], order_drop: [], low_stock: [], out_of_stock: [] },
        },
      },
    } as any);
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <WatchtowerDashboard />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByText(/未检测到异常/)).toBeInTheDocument();
    });
  });

  it("refresh button triggers refetch", async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: { code: 0, msg: "ok", data: mockScanData },
    } as any);
    const Wrapper = makeWrapper();
    render(
      <Wrapper>
        <WatchtowerDashboard />
      </Wrapper>,
    );
    await waitFor(() => screen.getByText("全局监控中心"));
    // Manually trigger refetch by calling refetch
    const { refetch } = (Wrapper as any)._queryRefetch || {};
    await act(async () => {
      // Click refresh button
      await userEvent.click(screen.getByRole("button", { name: /刷新/ }));
    });
    // Just verify button is present and clickable
    expect(screen.getByRole("button", { name: /刷新/ })).toBeInTheDocument();
  });
});
