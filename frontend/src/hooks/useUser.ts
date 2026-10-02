import { useMutation, useQueryClient } from "@tanstack/react-query";
import { userService } from "../services/user";
import { useAuthStore } from "../store/authStore";

export function useUpdateName() {
  const fetchUser = useAuthStore((s) => s.fetchUser);
  return useMutation({
    mutationFn: async (name: string) => (await userService.updateName(name)).data,
    onSuccess: () => {
      void fetchUser();
    },
  });
}

export function useChangePassword() {
  // The backend bumps token_version, so the old token is dead: store the fresh one at once.
  const setToken = useAuthStore((s) => s.setToken);
  return useMutation({
    mutationFn: async (v: { current: string; next: string }) => (await userService.changePassword(v.current, v.next)).data,
    onSuccess: (data) => {
      if (data.access_token) setToken(data.access_token);
    },
  });
}

export function useSetPassword() {
  const setToken = useAuthStore((s) => s.setToken);
  return useMutation({
    mutationFn: async (next: string) => (await userService.setPassword(next)).data,
    onSuccess: (data) => {
      if (data.access_token) setToken(data.access_token);
    },
  });
}

export function useUpdateTimezone() {
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (tz: string) => (await userService.updateTimezone(tz)).data,
    onSuccess: () => {
      void fetchUser();
      // "Today" readings are keyed to the user's local day.
      void qc.invalidateQueries({ queryKey: ["horoscope"] });
    },
  });
}

export function useRequestDeletionCode() {
  return useMutation({ mutationFn: async () => (await userService.requestDeletionCode()).data });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  const logout = useAuthStore((s) => s.logout);
  return useMutation({
    mutationFn: async (proof: { password: string } | { code: string }) => {
      await userService.deleteAccount(proof);
    },
    onSuccess: () => {
      // Gap G-12: clear the token ourselves and drop every cached query.
      logout();
      qc.clear();
      // Hard navigation: ProtectedRoute would otherwise bounce us to /auth?next=/profile first.
      window.location.replace("/auth?deleted=1");
    },
  });
}
