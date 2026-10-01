import api from "./api";
import type { User } from "../types";

export const userService = {
  updateName: (name: string) =>
    api.put<User>("/users/me", { name }),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<{ message: string }>("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  setPassword: (newPassword: string) =>
    api.post<{ message: string }>("/auth/set-password", {
      new_password: newPassword,
    }),

  updateTimezone: (timezone: string) => api.put<User>("/users/me", { timezone }),

  /** OAuth-only accounts: emails a 6-digit code (1/min, 5/day). */
  requestDeletionCode: () => api.post<{ message: string }>("/users/me/deletion-code"),

  /** v1.1 re-auth: password accounts send {password}; OAuth-only accounts send {code}. */
  deleteAccount: (proof: { password: string } | { code: string }) => api.delete("/users/me", { data: proof }),
};
