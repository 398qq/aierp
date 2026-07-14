import { create } from "zustand";
import { login as apiLogin, getMe } from "../api";

interface AuthState {
  username: string | null;
  roles: string[];
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  init: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  // Token is now in httpOnly cookie — never stored in JS
  username: null,
  roles: [],
  loading: true,

  login: async (username: string, password: string) => {
    const resp = await apiLogin(username, password);
    const data = resp.data.data as { username?: string; roles?: string[] } | undefined;
    set({ username: data?.username ?? null, roles: data?.roles ?? [] });
  },

  logout: () => {
    set({ username: null, roles: [] });
  },

  init: async () => {
    try {
      const resp = await getMe();
      const data = resp.data.data as { username?: string; roles?: string[] } | undefined;
      set({ username: data?.username ?? null, roles: data?.roles ?? [], loading: false });
    } catch {
      set({ username: null, roles: [], loading: false });
    }
  },
}));
