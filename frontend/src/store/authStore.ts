import { create } from "zustand";
import { authService } from "../services/auth";
import { toApiError } from "../services/errors";
import type { User } from "../types";

// Known risk (coding_rules_frontend §5): the JWT lives in localStorage until the v2 refresh-cookie
// flow ships. Never store PII or birth data alongside it.
const TOKEN_KEY = "token";

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage blocked (private mode): the session lasts for this tab only.
  }
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** Set when loading the current user failed for a reason other than an expired session. */
  userError: string | null;
  /** True after a 401 on a stored token (expired, revoked or forged). */
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<User | null>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<User | null>;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: readToken(),
  user: null,
  isLoading: false,
  isAuthenticated: !!readToken(),
  userError: null,
  sessionExpired: false,

  login: async (email, password) => {
    try {
      const res = await authService.login({ email, password });
      writeToken(res.data.access_token);
      set({ token: res.data.access_token, isAuthenticated: true, sessionExpired: false });
      return await get().fetchUser();
    } catch (err) {
      throw new Error(toApiError(err).detail);
    }
  },

  register: async (email, password, name) => {
    try {
      const res = await authService.register({ email, password, name, terms_accepted: true });
      writeToken(res.data.access_token);
      set({ token: res.data.access_token, isAuthenticated: true });
      void get().fetchUser();
    } catch (err) {
      const e = toApiError(err);
      throw new Error(e.code === "TERMS_NOT_ACCEPTED" ? "Please agree to the Terms and Privacy Policy to create an account." : e.detail);
    }
  },

  logout: () => {
    writeToken(null);
    set({ token: null, user: null, isAuthenticated: false, userError: null, sessionExpired: false });
  },

  fetchUser: async () => {
    set({ isLoading: true, userError: null });
    try {
      const res = await authService.getMe();
      set({ user: res.data, isLoading: false });
      return res.data;
    } catch (err) {
      const e = toApiError(err);
      if (e.status === 401) {
        // Session expired or revoked: the api interceptor also redirects to /auth.
        writeToken(null);
        set({ token: null, user: null, isAuthenticated: false, isLoading: false, sessionExpired: true });
      } else {
        // Network blip or server error: keep the session, surface the problem (rules §3).
        set({ isLoading: false, userError: e.detail });
      }
      return null;
    }
  },

  setToken: (token: string) => {
    writeToken(token);
    set({ token, isAuthenticated: true });
  },
}));
