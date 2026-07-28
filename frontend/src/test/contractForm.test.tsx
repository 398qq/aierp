import { cleanup, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ContractForm from "../pages/sales/ContractForm";
import * as api from "../api";
import type { Contract } from "../types";

vi.mock("../api", () => ({
  getContract: vi.fn(),
  createContract: vi.fn(),
  updateContract: vi.fn(),
  getSalesOrders: vi.fn(),
  getCustomer: vi.fn().mockResolvedValue({ data: { data: { name: "测试客户" } } }),
  getCustomers: vi.fn().mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } }),
  getOpportunities: vi.fn().mockResolvedValue({ data: { data: { list: [] } } }),
  getQuotations: vi.fn().mockResolvedValue({ data: { data: { list: [] } } }),
  getProducts: vi.fn().mockResolvedValue({ data: { data: { list: [] } } }),
  getProduct: vi.fn(),
}));

function renderContractForm(isEdit = false) {
  const initialEntry = isEdit ? "/sales/contracts/1/edit" : "/sales/contracts/new";
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/sales/contracts/new" element={<ContractForm />} />
        <Route path="/sales/contracts/:id/edit" element={<ContractForm />} />
      </Routes>
    </MemoryRouter>
  );
}

async function waitForForm() {
  expect(await screen.findByText("客户")).toBeInTheDocument();
}

describe("ContractForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSalesOrders).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
    vi.mocked(api.getCustomers).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
  });

  afterEach(() => {
    cleanup();
  });

  it("wraps in SalesModuleShell with contracts activeKey (new)", async () => {
    renderContractForm(false);
    await waitForForm();
    expect(screen.getByText("新增合同")).toBeInTheDocument();
  });

  it("wraps in SalesModuleShell with contracts activeKey (edit)", async () => {
    const mockContract: Partial<Contract> = {
      id: 1, contract_no: "CT-001", customer_id: 42, title: "框架合同",
      amount: 50000, status: "draft", signed_date: null, expire_date: null,
      sales_order_id: null, file_url: null, notes: null,
      created_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(api.getContract).mockResolvedValue({ data: { data: mockContract } } as never);
    renderContractForm(true);
    expect(await screen.findByText("编辑合同")).toBeInTheDocument();
  });

  it("renders form fields: customer, title, contract_no, amount, status", async () => {
    renderContractForm(false);
    await waitForForm();
    expect(screen.getByText("标题")).toBeInTheDocument();
    expect(screen.getByText("合同号")).toBeInTheDocument();
    expect(screen.getByText("金额")).toBeInTheDocument();
    expect(screen.getByText("状态")).toBeInTheDocument();
  });

  it("renders form fields: signed_date, expire_date, file_url, notes", async () => {
    renderContractForm(false);
    await waitForForm();
    expect(screen.getByText("签署日期")).toBeInTheDocument();
    expect(screen.getByText("到期日期")).toBeInTheDocument();
    expect(screen.getByText("文件URL")).toBeInTheDocument();
    expect(screen.getByText("备注")).toBeInTheDocument();
  });

  it("renders related order select field", async () => {
    renderContractForm(false);
    await waitForForm();
    expect(screen.getByText("关联订单")).toBeInTheDocument();
  });

  // Ant Design 6 inserts spaces between Chinese characters in buttons (e.g. "创 建").
  // find by role with a name that ignores internal whitespace.
  const findByNormalizedLabel = async (labelNoSpaces: string) =>
    screen.findByRole("button", {
      name: (_accessibleName: string, element: Element) =>
        (element.textContent ?? "").replace(/\s+/g, "") === labelNoSpaces,
    });

  it("shows submit button with correct label for new form", async () => {
    renderContractForm(false);
    expect(await findByNormalizedLabel("创建")).toBeInTheDocument();
  });

  it("shows submit button with correct label for edit form", async () => {
    vi.mocked(api.getContract).mockResolvedValue({ data: { data: { id: 1, customer_id: 42, title: "T", amount: 0, status: "draft" } as Contract } } as never);
    renderContractForm(true);
    expect(await findByNormalizedLabel("保存")).toBeInTheDocument();
  });

  it("renders cancel button", async () => {
    renderContractForm(false);
    expect(await findByNormalizedLabel("取消")).toBeInTheDocument();
  });
});
