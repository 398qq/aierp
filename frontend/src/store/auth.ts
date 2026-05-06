import { create } from "zustand";
import { login as apiLogin, getMe } from "../api";

interface AuthState {
  token: string | null;
  username: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  init: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("token"),
  username: null,
  loading: true,

  login: async (username: string, password: string) => {
    const resp = await apiLogin(username, password);
    const { token } = resp.data.data;
    localStorage.setItem("token", token);
    set({ token, username });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, username: null });
  },

  init: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      set({ loading: false });
      return;
    }
    try {
      const resp = await getMe();
      const data = resp.data.data as { username?: string } | undefined;
      set({ username: data?.username ?? null, loading: false });
    } catch {
      localStorage.removeItem("token");
      set({ token: null, loading: false });
    }
  },
}));
