import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import QuotationDetail from "../pages/sales/QuotationDetail";
import * as api from "../api";

vi.mock("../api", () => ({
  convertQuotationToOrder: vi.fn(),
  downloadQuotationPDF: vi.fn(),
  duplicateQuotation: vi.fn(),
  getApiErrorMessage: vi.fn((_error, fallback) => fallback),
  getCustomer: vi.fn().mockResolvedValue({ data: { data: { name: "深圳市测试客户有限公司" } } }),
  getOpportunity: vi.fn().mockResolvedValue({ data: { data: { title: "毫米波传感器项目" } } }),
  getQuotation: vi.fn(),
  sendQuotation: vi.fn(),
  updateQuotationStatus: vi.fn(),
}));

const quote = {
  id: 6,
  quotation_no: "QT202607200006",
  customer_id: 42,
  customer_name: "深圳市测试客户有限公司",
  opportunity_id: 3,
  opportunity_title: "毫米波传感器项目",
  title: "毫米波传感器批量报价",
  total_amount: 1130,
  status: "sent",
  currency: "CNY",
  incoterms: "DDP",
  payment_terms: "月结30天",
  discount_rate: 0,
  discount_amount: 0,
  subtotal: 1000,
  valid_until: "2026-07-31T00:00:00Z",
  notes: "原厂包装交付",
  created_at: "2026-07-20T00:00:00Z",
  updated_at: null,
  items: [{
    id: 1,
    quotation_id: 6,
    product_id: 25,
    product_name: "毫米波传感器 QMA6101T",
    quantity: 1000,
    unit: "pcs",
    unit_price: 1.13,
    total_price: 1130,
    tax_rate: 13,
    discount_rate: 0,
    cost_price: 0.8,
    untaxed_cost: 707.96,
    taxed_cost: 800,
    sales_profit: 330,
    datecode: "DC 24+",
    lead_time: "2周",
    notes: "整盘包装",
  }],
};

describe("QuotationDetail printing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getQuotation).mockResolvedValue({ data: { data: quote } } as never);
    vi.mocked(api.getCustomer).mockResolvedValue({ data: { data: { name: "深圳市测试客户有限公司" } } } as never);
    vi.stubGlobal("print", vi.fn());
  });

  afterEach(cleanup);

  it("renders a customer-safe quotation and invokes browser printing", async () => {
    render(
      <MemoryRouter initialEntries={["/sales/quotations/6"]}>
        <Routes><Route path="/sales/quotations/:id" element={<QuotationDetail />} /></Routes>
      </MemoryRouter>,
    );

    const printable = await screen.findByTestId("sales-quotation-print");
    expect(printable.parentElement).toBe(document.body);
    expect(within(printable).getByText("销售报价单")).toBeInTheDocument();
    expect(within(printable).getAllByText("QT202607200006").length).toBeGreaterThan(0);
    expect(within(printable).getAllByText("深圳市测试客户有限公司").length).toBeGreaterThan(0);
    expect(within(printable).getByText("毫米波传感器 QMA6101T")).toBeInTheDocument();
    expect(within(printable).getByText("月结30天")).toBeInTheDocument();
    expect(within(printable).queryByText("销售利润")).not.toBeInTheDocument();
    expect(within(printable).queryByText("含税成本")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /打印报价单/ }));
    await waitFor(() => expect(window.print).toHaveBeenCalledOnce());
  });
});
