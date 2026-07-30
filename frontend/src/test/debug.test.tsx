import { cleanup, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

vi.mock("../api/client", () => {
  const emptyPage = { data: { list: [], total: 0 } };
  const fakeClient = {
    get: vi.fn().mockImplementation(() =>
      Promise.resolve({ data: { data: emptyPage, msg: "ok", code: 0 } }),
    ),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  };
  return { default: fakeClient };
});

describe("debug", () => {
  it("prints DOM", async () => {
    vi.mocked(api.getSalesOrders).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
    vi.mocked(api.getCustomers).mockResolvedValue({ data: { data: { list: [] }, msg: "ok", code: 0 } } as never);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/sales/contracts/new"]}>
          <Routes>
            <Route path="/sales/contracts/new" element={<ContractForm />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await new Promise(r => setTimeout(r, 500));
    console.log("INNER_HTML_START");
    console.log(container.innerHTML.substring(0, 5000));
    console.log("INNER_HTML_END");
  });
});
