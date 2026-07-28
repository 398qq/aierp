import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import CustomerModuleShell from "../pages/customers/CustomerModuleShell";
import { useAuthStore } from "../store/auth";

describe("CustomerModuleShell", () => {
  beforeEach(() => {
    useAuthStore.setState({ username: "manager", roles: ["sales_manager"], loading: false });
  });

  it("shows the consolidated four-part information architecture", () => {
    render(
      <MemoryRouter initialEntries={["/customers"]}>
        <CustomerModuleShell title="客户台账">content</CustomerModuleShell>
      </MemoryRouter>,
    );

    expect(screen.getByText("工作台")).toBeInTheDocument();
    expect(screen.getByText("客户台账", { selector: ".customer-module-nav-item span:last-child" })).toBeInTheDocument();
    expect(screen.getByText("跟进任务")).toBeInTheDocument();
    expect(screen.getByText("分析中心")).toBeInTheDocument();
    expect(screen.getByText(/主管视图/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "AI工作队列" })).not.toBeInTheDocument();
  });

  it("groups analytics tools behind the analysis entry", () => {
    render(
      <MemoryRouter initialEntries={["/customers/intelligence"]}>
        <CustomerModuleShell title="智能分析">content</CustomerModuleShell>
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /智能分析/ })).toBeInTheDocument();
  });
});
