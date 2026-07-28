import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import DeliveryNoteDetail from "../pages/sales/DeliveryNoteDetail";
import * as api from "../api";

vi.mock("../api", () => ({
  convertDeliveryToInvoice: vi.fn(),
  convertDeliveryToReturn: vi.fn(),
  getApiErrorMessage: vi.fn((_error, fallback) => fallback),
  getCustomer: vi.fn().mockResolvedValue({ data: { data: { name: "深圳市测试客户有限公司" } } }),
  getDeliveryNote: vi.fn(),
  getPayments: vi.fn(),
  markDeliveryNotePaid: vi.fn(),
  updateDeliveryNote: vi.fn(),
}));

const note = {
  id: 12,
  delivery_no: "DN202607200012",
  sales_order_id: 8,
  sales_order_no: "SO202607180008",
  customer_id: 42,
  customer_name: "深圳市测试客户有限公司",
  status: "shipped",
  shipping_method: "顺丰速运",
  tracking_number: "SF1234567890",
  incoterms: "DDP",
  delivery_date: "2026-07-20T00:00:00Z",
  received_date: null,
  notes: "原厂包装，外箱完好",
  created_at: "2026-07-20T00:00:00Z",
  updated_at: null,
  items: [{
    id: 1,
    delivery_note_id: 12,
    product_id: 25,
    product_name: "毫米波传感器 QMA6101T",
    quantity: 1000,
    unit: "pcs",
    notes: "10 盘",
  }],
};

describe("DeliveryNoteDetail printing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getDeliveryNote).mockResolvedValue({ data: { data: note } } as never);
    vi.mocked(api.getPayments).mockResolvedValue({ data: { data: { list: [] } } } as never);
    vi.stubGlobal("print", vi.fn());
  });

  afterEach(cleanup);

  it("renders a customer-safe delivery note and invokes browser printing", async () => {
    render(
      <MemoryRouter initialEntries={["/sales/delivery-notes/12"]}>
        <Routes><Route path="/sales/delivery-notes/:id" element={<DeliveryNoteDetail />} /></Routes>
      </MemoryRouter>,
    );

    const printable = await screen.findByTestId("delivery-note-print");
    expect(printable.parentElement).toBe(document.body);
    expect(within(printable).getByText("销售送货单")).toBeInTheDocument();
    expect(within(printable).getAllByText("DN202607200012").length).toBeGreaterThan(0);
    expect(within(printable).getAllByText("深圳市测试客户有限公司").length).toBeGreaterThan(0);
    expect(within(printable).getByText("毫米波传感器 QMA6101T")).toBeInTheDocument();
    expect(within(printable).getByText("SF1234567890")).toBeInTheDocument();
    expect(within(printable).queryByText("回款信息")).not.toBeInTheDocument();
    expect(within(printable).queryByText("AI")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /打印送货单/ }));
    await waitFor(() => expect(window.print).toHaveBeenCalledOnce());
  });
});
