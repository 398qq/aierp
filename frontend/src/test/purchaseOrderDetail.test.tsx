import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import PurchaseOrderDetail from "../pages/sales/PurchaseOrderDetail";
import * as api from "../api";

vi.mock("../api", () => ({
  confirmLargePurchaseOrder: vi.fn(),
  confirmPurchaseOrderSupplier: vi.fn(),
  getApiErrorMessage: vi.fn((_error, fallback) => fallback),
  getPurchaseOrder: vi.fn(),
  receivePurchaseOrder: vi.fn(),
  transitionPurchaseOrder: vi.fn(),
}));

const purchaseOrder = {
  id: 17,
  order_no: "PO202607170002",
  supplier_id: 9,
  supplier_name: "深圳市恒泰瑞科技有限公司",
  supplier_contact: "刘斌",
  status: "draft",
  total_amount: 1130,
  subtotal: 1000,
  tax_amount: 130,
  tax_rate: 13,
  currency: "CNY",
  incoterms: "DDP",
  payment_terms: "现款",
  sales_order_id: 3,
  sales_order_no: "SO202607150003",
  customer_name: "测试客户",
  delivery_address: "深圳市福田区测试地址",
  expected_date: "2026-07-24",
  large_order_confirmed: false,
  supplier_confirmation_status: "pending",
  allow_partial_delivery: false,
  contract_terms_version: "v3.4",
  notes: "测试采购订单",
  created_at: "2026-07-17T08:00:00+08:00",
  items: [{
    id: 1,
    product_id: 25,
    sales_order_id: 3,
    supplier_mpn: "QMA6101T",
    product_sku: "QMA6101T-SKU",
    product_name: "毫米波传感器",
    brand_name: "QST",
    package_type: "LGA",
    quantity: 1000,
    unit: "pcs",
    min_pack_qty: 1000,
    min_pack_unit: "盘",
    date_code_requirement: "≥24+",
    tax_rate: 13,
    unit_price: 1.13,
    amount: 1130,
    customer_name: "测试客户",
    notes: "关联客户订单",
  }],
};

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={["/sales/purchase-orders/17"]}>
      <Routes>
        <Route path="/sales/purchase-orders/:id" element={<PurchaseOrderDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PurchaseOrderDetail printing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getPurchaseOrder).mockResolvedValue({ data: { data: purchaseOrder } } as never);
    vi.stubGlobal("print", vi.fn());
  });

  afterEach(cleanup);

  it("prints contract terms and protects customer references by default", async () => {
    renderDetail();

    const document = await screen.findByTestId("purchase-order-print");
    expect(within(document).getByText("采购合同")).toBeInTheDocument();
    expect(within(document).getAllByText("PO202607170002").length).toBeGreaterThan(0);
    expect(within(document).getAllByText("深圳天允电子有限公司").length).toBeGreaterThan(0);
    expect(within(document).getByText(/商务与交付条件/)).toBeInTheDocument();
    expect(within(document).getByText("价税合计（大写）")).toBeInTheDocument();
    expect(within(document).getByText(/履约与验收要求/)).toBeInTheDocument();
    expect(within(document).getByText("QMA6101T")).toBeInTheDocument();
    expect(within(document).getByText("≥24+")).toBeInTheDocument();
    expect(within(document).queryByText("审批通过")).not.toBeInTheDocument();
    expect(within(document).getAllByText("采购合同条款 v3.4").length).toBeGreaterThan(0);
    expect(within(document).getByText("7.14 保密条款")).toBeInTheDocument();
    expect(within(document).queryByText("SO202607150003")).not.toBeInTheDocument();
    expect(within(document).queryByText("测试客户")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /打印采购订单/ }));
    expect(await screen.findByText("对外打印确认")).toBeInTheDocument();
    expect(window.print).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "确认打印" }));
    await waitFor(() => expect(window.print).toHaveBeenCalledOnce());
  });

  it("only includes related SO and customer after explicit opt-in", async () => {
    renderDetail();

    const document = await screen.findByTestId("purchase-order-print");
    fireEvent.click(screen.getByRole("button", { name: /打印采购订单/ }));
    fireEvent.click(await screen.findByRole("checkbox", { name: /显示关联 SO、关联客户及内部备注/ }));

    expect(within(document).getByText("SO202607150003")).toBeInTheDocument();
    expect(within(document).getAllByText("测试客户").length).toBeGreaterThan(0);
  });
});
