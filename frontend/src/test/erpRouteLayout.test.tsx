import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ErpRouteLayout from "../layouts/ErpRouteLayout";
import { useAuthStore } from "../store/auth";

vi.mock("../layouts/MainLayout", () => ({
  default: () => <div>ERP shell</div>,
}));

describe("ErpRouteLayout", () => {
  beforeEach(() => {
    useAuthStore.setState({
      username: null,
      roles: [],
      loading: true,
      init: vi.fn().mockResolvedValue(undefined),
    });
  });

  it("restores the cookie session before deciding whether to redirect", async () => {
    const init = useAuthStore.getState().init;

    render(
      <MemoryRouter initialEntries={["/customers"]}>
        <ErpRouteLayout />
      </MemoryRouter>,
    );

    expect(screen.queryByText("ERP shell")).not.toBeInTheDocument();
    await waitFor(() => expect(init).toHaveBeenCalledTimes(1));
  });

  it("renders the ERP shell after a valid session is restored", () => {
    useAuthStore.setState({ username: "manager", loading: false });

    render(
      <MemoryRouter initialEntries={["/customers"]}>
        <ErpRouteLayout />
      </MemoryRouter>,
    );

    expect(screen.getByText("ERP shell")).toBeInTheDocument();
  });

  it("redirects only after session restoration confirms no user", () => {
    useAuthStore.setState({ username: null, loading: false });

    render(
      <MemoryRouter initialEntries={["/customers"]}>
        <Routes>
          <Route path="/customers" element={<ErpRouteLayout />} />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Login page")).toBeInTheDocument();
  });
});
