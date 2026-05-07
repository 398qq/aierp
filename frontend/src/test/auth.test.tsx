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
    useAuthStore.setState({ token: null, username: null, loading: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("init", () => {
    it("sets loading=false when no token in localStorage", async () => {
      await act(async () => {
        await useAuthStore.getState().init();
      });
      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.token).toBeNull();
      expect(state.username).toBeNull();
    });

    it("fetches user when token exists and API succeeds", async () => {
      localStorage.setItem("token", "valid-token");
      vi.mocked(getMe).mockResolvedValue({
        data: { data: { username: "testuser" } },
      } as any);

      await act(async () => {
        await useAuthStore.getState().init();
      });
      // Wait for async state update to propagate
      await new Promise(r => setTimeout(r, 0));

      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.token).toBe("valid-token");
      expect(state.username).toBe("testuser");
      expect(getMe).toHaveBeenCalledTimes(1);
    });

    it("clears token when API call fails", async () => {
      localStorage.setItem("token", "expired-token");
      vi.mocked(getMe).mockRejectedValue(new Error("Unauthorized"));

      await act(async () => {
        await useAuthStore.getState().init();
      });

      const state = useAuthStore.getState();
      expect(state.loading).toBe(false);
      expect(state.token).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });

    it("handles missing username in API response gracefully", async () => {
      localStorage.setItem("token", "valid-token");
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
    it("stores token and username on successful login", async () => {
      vi.mocked(apiLogin).mockResolvedValue({
        data: { data: { token: "new-token" } },
      } as any);

      await act(async () => {
        await useAuthStore.getState().login("admin", "password");
      });

      const state = useAuthStore.getState();
      expect(state.token).toBe("new-token");
      expect(localStorage.getItem("token")).toBe("new-token");
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
    it("clears token and username", () => {
      useAuthStore.setState({ token: "some-token", username: "user" });
      localStorage.setItem("token", "some-token");

      act(() => {
        useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.token).toBeNull();
      expect(state.username).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });
  });
});