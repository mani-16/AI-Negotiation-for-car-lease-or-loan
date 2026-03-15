/**
 * Auth store — production token strategy
 *
 * Access token  → in-memory (Zustand state). Never written to localStorage.
 *                  Lost on page refresh, recovered by calling /auth/refresh.
 * Refresh token → HTTP-only cookie set by the server.
 *                  Invisible to JavaScript. Survives page refreshes.
 */
import { create } from "zustand";
import { UserRead } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface AuthState {
  accessToken: string | null;
  user: UserRead | null;
  isAuthenticated: boolean;

  /** Called after a successful login response. */
  login: (accessToken: string, user: UserRead) => void;

  /** Set / update the access token in memory (used by the refresh interceptor). */
  setAccessToken: (accessToken: string, user: UserRead) => void;

  /**
   * Silently call POST /auth/refresh.
   * Returns the new access token, or null if the refresh token has expired.
   */
  refreshAccessToken: () => Promise<string | null>;

  /** Revoke the refresh token server-side and clear local state. */
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,

  login(accessToken, user) {
    set({ accessToken, user, isAuthenticated: true });
    // No localStorage — token stays in memory only
  },

  setAccessToken(accessToken, user) {
    set({ accessToken, user, isAuthenticated: true });
  },

  async refreshAccessToken() {
    try {
      // withCredentials sends the HTTP-only refresh_token cookie
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) {
        set({ accessToken: null, user: null, isAuthenticated: false });
        return null;
      }

      const data = await res.json();
      set({
        accessToken: data.access_token,
        user: data.user,
        isAuthenticated: true,
      });
      return data.access_token as string;
    } catch {
      set({ accessToken: null, user: null, isAuthenticated: false });
      return null;
    }
  },

  async logout() {
    try {
      // Tell the server to revoke the refresh token and clear the cookie
      await fetch(`${BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore network errors during logout
    }
    set({ accessToken: null, user: null, isAuthenticated: false });
  },
}));
