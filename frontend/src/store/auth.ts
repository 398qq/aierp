import { create } from "zustand";
import { login as apiLogin, getMe } from "../api";

interface AuthState {
  username: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  init: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  // Token is now in httpOnly cookie — never stored in JS
  username: null,
  loading: true,

  login: async (username: string, password: string) => {
    const resp = await apiLogin(username, password);
    const data = resp.data.data as { username?: string } | undefined;
    set({ username: data?.username ?? null });
  },

  logout: () => {
    set({ username: null });
  },

  init: async () => {
    try {
      const resp = await getMe();
      const data = resp.data.data as { username?: string } | undefined;
      set({ username: data?.username ?? null, loading: false });
    } catch {
      set({ username: null, loading: false });
    }
  },
}));
