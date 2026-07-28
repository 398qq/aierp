import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ContractDetail from "../pages/sales/ContractDetail";
import * as api from "../api";
import type { Contract } from "../types";

vi.mock("../api", () => ({
  getContract: vi.fn(),
  getCustomer: vi.fn().mockResolvedValue({ data: { data: { name: "测试客户" } } }),
  getCustomers: vi.fn().mockResolvedValue({ data: { data: { list: [] } } }),
}));

const contract = (overrides: Partial<Contract> = {}): Contract => ({
  id: 1,
  contract_no: "CT-2026-001",
  customer_id: 42,
  sales_order_id: null,
  title: "2026年度框架采购合同",
  amount: 128000,
  currency: "CNY",
  signed_date: "2026-03-15T00:00:00Z",
  expire_date: "2026-12-31T00:00:00Z",
  status: "active",
  file_url: null,
  notes: "年度框架合同",
  created_at: "2026-03-10T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
  ...overrides,
});

function renderContractDetail(mockContract: Contract) {
  vi.mocked(api.getContract).mockResolvedValue({ data: { data: mockContract } } as never);
  return render(
    <MemoryRouter initialEntries={["/sales/contracts/1"]}>
      <Routes>
        <Route path="/sales/contracts/:id" element={<ContractDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

async function waitForContent() {
  // Wait until the main content is rendered (after loading state)
  const els = await screen.findAllByText("CT-2026-001");
  expect(els.length).toBeGreaterThanOrEqual(1);
}

describe("ContractDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("print", vi.fn());
  });

  afterEach(() => {
    cleanup();
  });

  it("wraps content in SalesModuleShell with contracts activeKey", async () => {
    renderContractDetail(contract());
    await waitForContent();
    // Nav should have activeKey="contracts" - find the "合同" tab button
    const contractButtons = screen.getAllByRole("button", { name: /合同/ });
    expect(contractButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("renders MetricBand with 合同金额, 状态, 已开票金额, 到期日", async () => {
    renderContractDetail(contract());
    await waitForContent();
    // "合同金额" appears in MetricBand title and sidebar, so use getAllByText
    const amountTitles = screen.getAllByText("合同金额");
    expect(amountTitles.length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("状态").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("到期日").length).toBeGreaterThanOrEqual(1);
  });

  it("renders action buttons: 返回列表 and 编辑合同", async () => {
    renderContractDetail(contract());
    await waitForContent();
    // These buttons appear in both the shell extra and the action card
    const backButtons = screen.getAllByRole("button", { name: /返回列表/ });
    expect(backButtons.length).toBeGreaterThanOrEqual(1);
    const editButtons = screen.getAllByRole("button", { name: /编辑合同/ });
    expect(editButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("prints a formal sales contract from the detail page", async () => {
    renderContractDetail(contract({
      payment_terms: "合同签署后30日内付款",
      delivery_terms: "送货至客户指定地点",
    }));
    await waitForContent();

    const printable = screen.getByTestId("sales-contract-print");
    expect(printable.parentElement).toBe(document.body);
    expect(within(printable).getByText("销售合同")).toBeInTheDocument();
    expect(within(printable).getAllByText("CT-2026-001").length).toBeGreaterThan(0);
    expect(within(printable).getAllByText("测试客户").length).toBeGreaterThan(0);
    expect(within(printable).getByText("合同签署后30日内付款")).toBeInTheDocument();
    expect(window.print).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /打印销售合同/ }));
    await waitFor(() => expect(window.print).toHaveBeenCalledOnce());
  });

  it("renders contract info card with details", async () => {
    renderContractDetail(contract());
    await waitForContent();
    expect(screen.getAllByText("合同信息").length).toBeGreaterThanOrEqual(1);
    // Title appears in info card and possibly elsewhere
    const titles = screen.getAllByText("2026年度框架采购合同");
    expect(titles.length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("年度框架合同").length).toBeGreaterThanOrEqual(1);
  });

  it("renders sidebar with 合同摘要, 状态流转, 下一步动作", async () => {
    renderContractDetail(contract());
    await waitForContent();
    expect(screen.getByText("合同摘要")).toBeInTheDocument();
    expect(screen.getByText("状态流转")).toBeInTheDocument();
    expect(screen.getByText("下一步动作")).toBeInTheDocument();
  });

  it("shows contract summary in sidebar", async () => {
    renderContractDetail(contract());
    await waitForContent();
    expect(screen.getByText("合同标题")).toBeInTheDocument();
    const contractNoLabels = screen.getAllByText("合同号");
    expect(contractNoLabels.length).toBeGreaterThanOrEqual(1);
    const signedDateLabels = screen.getAllByText("签署日期");
    expect(signedDateLabels.length).toBeGreaterThanOrEqual(1);
    const expireDateLabels = screen.getAllByText("到期日期");
    expect(expireDateLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("shows loading state initially", () => {
    vi.mocked(api.getContract).mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(
      <MemoryRouter initialEntries={["/sales/contracts/1"]}>
        <Routes>
          <Route path="/sales/contracts/:id" element={<ContractDetail />} />
        </Routes>
      </MemoryRouter>
    );
    // Should show loading spinner
    expect(container.querySelector(".ant-spin")).toBeTruthy();
  });

  it("shows error alert when loading fails", async () => {
    vi.mocked(api.getContract).mockRejectedValue(new Error("加载失败") as never);
    render(
      <MemoryRouter initialEntries={["/sales/contracts/1"]}>
        <Routes>
          <Route path="/sales/contracts/:id" element={<ContractDetail />} />
        </Routes>
      </MemoryRouter>
    );
    expect(await screen.findByText("加载失败")).toBeInTheDocument();
  });

  it("shows empty state when contract not found", async () => {
    vi.mocked(api.getContract).mockResolvedValue({ data: { data: null } } as never);
    render(
      <MemoryRouter initialEntries={["/sales/contracts/1"]}>
        <Routes>
          <Route path="/sales/contracts/:id" element={<ContractDetail />} />
        </Routes>
      </MemoryRouter>
    );
    expect(await screen.findByText("合同不存在")).toBeInTheDocument();
  });

  it("shows different status labels", async () => {
    const tests: Array<{ status: string; label: string }> = [
      { status: "draft", label: "草稿" },
      { status: "signed", label: "已签署" },
      { status: "active", label: "履行中" },
      { status: "expired", label: "已到期" },
      { status: "terminated", label: "已终止" },
    ];
    for (const { status, label } of tests) {
      vi.clearAllMocks();
      renderContractDetail(contract({ status }));
      // Status labels appear in both tag and timeline
      const found = await screen.findAllByText(label);
      expect(found.length).toBeGreaterThanOrEqual(1);
      cleanup();
    }
  });

  it("shows next action suggestions based on status", async () => {
    renderContractDetail(contract({ status: "draft" }));
    expect(await screen.findByText("合同为草稿状态，完善信息后可签署。")).toBeInTheDocument();
    cleanup();

    renderContractDetail(contract({ status: "active" }));
    expect(await screen.findByText("合同履行中，关注到期日和交付进度。")).toBeInTheDocument();
    cleanup();

    renderContractDetail(contract({ status: "expired" }));
    expect(await screen.findByText("合同已到期，如需续签请及时处理。")).toBeInTheDocument();
  });
});
