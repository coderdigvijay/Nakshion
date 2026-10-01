import api, { API_BASE_URL } from "./api";
import type { User } from "../types";

export const authService = {
  register: (data: { email: string; password: string; name: string }) =>
    api.post<{ access_token: string }>("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post<{ access_token: string }>("/auth/login", data),

  verifyEmail: (code: string) =>
    api.post<{ message: string }>("/auth/verify-email", { code }),

  resendOtp: () => api.post<{ message: string }>("/auth/resend-otp"),

  forgotPassword: (email: string) =>
    api.post<{ message: string }>("/auth/forgot-password", { email }),

  resetPassword: (token: string, newPassword: string) =>
    api.post<{ message: string }>("/auth/reset-password", {
      token,
      new_password: newPassword,
    }),

  /** v1.1: swap the one-time code from the Google redirect for a JWT. 400 INVALID_OR_EXPIRED_CODE on reuse/expiry. */
  oauthExchange: (code: string) =>
    api.post<{ access_token: string; token_type: string }>("/auth/oauth/exchange", { code }),

  getMe: () => api.get<User>("/auth/me"),

  googleOAuthUrl: () => `${API_BASE_URL}/auth/oauth/google`,
};
