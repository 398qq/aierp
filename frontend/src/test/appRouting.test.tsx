import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Outlet, useLocation } from "react-router";

import App from "../App";
import AppRoutes from "../routes/AppRoutes";
import { useAuthStore } from "../store/auth";

vi.mock("../api", () => ({
  getMe: vi.fn(),
  login: vi.fn(),
  getUnreadCount: vi.fn(),
  naturalLanguageQuery: vi.fn(),
}));

vi.mock("../pages/auth/Login", () => ({
  default: () => <div>登录页</div>,
}));

vi.mock("../pages/dashboard/index", () => ({
  default: () => <div>经营总览页</div>,
}));

vi.mock("../layouts/MainLayout", () => ({
  default: function MockMainLayout() {
    const location = useLocation();
    return (
      <div data-testid="application-shell">
        <output data-testid="route-location">
          {location.pathname}
          {location.search}
        </output>
        <Outlet />
      </div>
    );
  },
}));

import { getMe } from "../api";

describe("application routing", () => {
  beforeEach(() => {
    useAuthStore.setState({ username: null, roles: [], loading: true });
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    cleanup();
  });

  it("starts the real App with its browser Router owner", () => {
    window.history.replaceState({}, "", "/login");

    render(<App />);

    expect(screen.getByText("登录页")).toBeInTheDocument();
  });

  it("initializes the session before rendering the authenticated shell", async () => {
    vi.mocked(getMe).mockResolvedValue({
      data: { data: { username: "manager", roles: ["sales_manager"] } },
    } as never);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(screen.queryByTestId("application-shell")).not.toBeInTheDocument();
    expect(await screen.findByTestId("application-shell")).toBeInTheDocument();
    expect(await screen.findByText("经营总览页")).toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(1);
  });

  it("redirects an unauthenticated session to login", async () => {
    vi.mocked(getMe).mockRejectedValue(new Error("Unauthorized"));

    render(
      <MemoryRouter initialEntries={["/finance/accounts"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByText("登录页")).toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["/customers/acme/insight", "/customers/acme?tab=ai"],
    ["/customers/acme/360", "/customers/acme?tab=profile"],
  ])("redirects %s to the customer detail tab", async (from, expected) => {
    vi.mocked(getMe).mockResolvedValue({
      data: { data: { username: "manager", roles: ["sales_manager"] } },
    } as never);

    render(
      <MemoryRouter initialEntries={[from]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("route-location")).toHaveTextContent(expected);
    });
  });

  it("sends unknown routes through the authenticated home route", async () => {
    vi.mocked(getMe).mockRejectedValue(new Error("Unauthorized"));

    render(
      <MemoryRouter initialEntries={["/not-a-real-route"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByText("登录页")).toBeInTheDocument();
  });
});
