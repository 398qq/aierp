import { cleanup, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ContractForm from "../pages/sales/ContractForm";
import * as api from "../api";

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

describe("debug", () => {
  it("prints DOM", async () => {
    vi.mocked(api.getSalesOrders).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
    vi.mocked(api.getCustomers).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
    const { container } = render(
      <MemoryRouter initialEntries={["/sales/contracts/new"]}>
        <Routes>
          <Route path="/sales/contracts/new" element={<ContractForm />} />
        </Routes>
      </MemoryRouter>
    );
    await new Promise(r => setTimeout(r, 500));
    console.log("INNER_HTML_START");
    console.log(container.innerHTML.substring(0, 5000));
    console.log("INNER_HTML_END");
  });
});
