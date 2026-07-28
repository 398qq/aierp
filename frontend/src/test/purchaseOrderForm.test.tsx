import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PurchaseOrderForm from "../pages/sales/PurchaseOrderForm";
import * as api from "../api";

vi.mock("../api", () => ({
  createPurchaseOrder: vi.fn(),
  getProducts: vi.fn(),
  getPurchaseOrder: vi.fn(),
  getSalesOrders: vi.fn(),
  getSupplierProducts: vi.fn(),
  getSuppliers: vi.fn(),
  updatePurchaseOrder: vi.fn(),
}));

const page = (list: unknown[]) => ({ data: { code: 0, msg: "ok", data: { list } } });

function renderForm() {
  return render(
    <MemoryRouter initialEntries={["/sales/purchase-orders/new"]}>
      <Routes>
        <Route path="/sales/purchase-orders/new" element={<PurchaseOrderForm />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PurchaseOrderForm base data", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSuppliers).mockResolvedValue(page([]) as never);
    vi.mocked(api.getProducts).mockResolvedValue(page([]) as never);
    vi.mocked(api.getSalesOrders).mockResolvedValue(page([]) as never);
  });

  afterEach(cleanup);

  it("uses the backend-supported page size for products and sales orders", async () => {
    renderForm();

    await waitFor(() => {
      expect(api.getProducts).toHaveBeenCalledWith({ page: 1, page_size: 100 });
      expect(api.getSalesOrders).toHaveBeenCalledWith({ page: 1, page_size: 100 });
    });
  });

  it("keeps supplier and product data available when sales orders fail", async () => {
    vi.mocked(api.getSuppliers).mockResolvedValue(page([{ id: 9, name: "深圳市恒泰瑞科技有限公司" }]) as never);
    vi.mocked(api.getProducts).mockResolvedValue(page([{ id: 25, sku: "QMA6101T", name: "QMA6101T" }]) as never);
    vi.mocked(api.getSalesOrders).mockRejectedValue(new Error("sales orders unavailable"));

    renderForm();

    fireEvent.mouseDown(await screen.findByLabelText("供应商"));
    expect(await screen.findByText("深圳市恒泰瑞科技有限公司")).toBeInTheDocument();
  });
});
