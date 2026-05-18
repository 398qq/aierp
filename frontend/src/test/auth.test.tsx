import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useAuthStore } from "../store/auth";

// Mock the API module
vi.mock("../api", () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}));

import { login as apiLogin, getMe } from "../api";

describe("useAuthStore", () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset store state between tests
    useAuthStore.setState({ username: null, loading: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("init", () => {
    it("sets username from current session when API succeeds", async () => {
      vi.mocked(getMe).mockResolvedValue({
        data: { data: { username: "testuser" } },
      } as any);

      await act(async () => {
        await useAuthStore.getState().init();
      });

      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.username).toBe("testuser");
      expect(getMe).toHaveBeenCalledTimes(1);
    });

    it("clears username when API call fails", async () => {
      vi.mocked(getMe).mockRejectedValue(new Error("Unauthorized"));

      await act(async () => {
        await useAuthStore.getState().init();
      });

      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.username).toBeNull();
    });

    it("handles missing username in API response gracefully", async () => {
      vi.mocked(getMe).mockResolvedValue({
        data: { data: {} },
      } as any);

      await act(async () => {
        await useAuthStore.getState().init();
      });

      const state = useAuthStore.getState();
      expect(state.username).toBeNull();
    });
  });

  describe("login", () => {
    it("stores username on successful login", async () => {
      vi.mocked(apiLogin).mockResolvedValue({
        data: { data: { username: "admin" } },
      } as any);

      await act(async () => {
        await useAuthStore.getState().login("admin", "password");
      });

      const state = useAuthStore.getState();
      expect(state.username).toBe("admin");
      expect(localStorage.getItem("token")).toBeNull();
      expect(apiLogin).toHaveBeenCalledWith("admin", "password");
    });

    it("throws error on failed login", async () => {
      vi.mocked(apiLogin).mockRejectedValue(new Error("Invalid credentials"));

      await expect(
        act(async () => {
          await useAuthStore.getState().login("admin", "wrong");
        })
      ).rejects.toThrow();
    });
  });

  describe("logout", () => {
    it("clears username", () => {
      useAuthStore.setState({ username: "user" });
      localStorage.setItem("token", "some-token");

      act(() => {
        useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.username).toBeNull();
      expect(localStorage.getItem("token")).toBe("some-token");
    });
  });
});
