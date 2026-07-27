import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import SalesOrderDetail from "../pages/sales/SalesOrderDetail";
import * as api from "../api";

vi.mock("../api", () => ({
  convertSalesOrderToDelivery: vi.fn(),
  downloadSalesOrderPDF: vi.fn(),
  getApiErrorMessage: vi.fn((_error, fallback) => fallback),
  getCustomer: vi.fn().mockResolvedValue({ data: { data: { name: "深圳市测试客户有限公司" } } }),
  getPayments: vi.fn().mockResolvedValue({ data: { data: { list: [] } } }),
  getSalesOrder: vi.fn(),
  getSalesOrderBusinessChain: vi.fn().mockRejectedValue(new Error("no chain")),
  updateSalesOrder: vi.fn(),
}));

const order = {
  id: 8,
  order_no: "SO202607180008",
  customer_id: 42,
  customer_name: "深圳市测试客户有限公司",
  quotation_id: 3,
  quotation_no: "QT202607160003",
  total_amount: 1130,
  status: "confirmed",
  currency: "CNY",
  incoterms: "DDP",
  payment_terms: "月结30天",
  due_date: "2026-08-18T00:00:00Z",
  customer_po_no: "CPO-7788",
  shipping_address: "深圳市南山区测试路 8 号",
  billing_address: "深圳市南山区测试路 8 号",
  discount_rate: 0,
  discount_amount: 0,
  subtotal: 1000,
  order_date: "2026-07-18T00:00:00Z",
  delivery_date: "2026-07-25T00:00:00Z",
  notes: "原厂包装交付",
  created_at: "2026-07-18T00:00:00Z",
  updated_at: null,
  items: [{
    id: 1,
    order_id: 8,
    product_id: 25,
    product_name: "毫米波传感器 QMA6101T",
    quantity: 1000,
    unit: "pcs",
    unit_price: 1.13,
    total_price: 1130,
    tax_rate: 13,
    discount_rate: 0,
    notes: "DC 24+",
  }],
};

describe("SalesOrderDetail printing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSalesOrder).mockResolvedValue({ data: { data: order } } as never);
    vi.mocked(api.getPayments).mockResolvedValue({ data: { data: { list: [] } } } as never);
    vi.mocked(api.getSalesOrderBusinessChain).mockRejectedValue(new Error("no chain"));
    vi.stubGlobal("print", vi.fn());
  });

  afterEach(cleanup);

  it("renders and prints the sales order document", async () => {
    render(
      <MemoryRouter initialEntries={["/sales/orders/8"]}>
        <Routes><Route path="/sales/orders/:id" element={<SalesOrderDetail />} /></Routes>
      </MemoryRouter>,
    );

    const printable = await screen.findByTestId("sales-order-print");
    expect(printable.parentElement).toBe(document.body);
    expect(within(printable).getByText("销售订单")).toBeInTheDocument();
    expect(within(printable).getAllByText("SO202607180008").length).toBeGreaterThan(0);
    expect(within(printable).getAllByText("深圳市测试客户有限公司").length).toBeGreaterThan(0);
    expect(within(printable).getByText("毫米波传感器 QMA6101T")).toBeInTheDocument();
    expect(within(printable).getByText("月结30天")).toBeInTheDocument();
    expect(window.print).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /打印销售订单/ }));
    await waitFor(() => expect(window.print).toHaveBeenCalledOnce());
  });
});
