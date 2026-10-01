import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatService } from "../services/chat";
import type { Conversation, ConversationDetail, Message } from "../types";

export const chatKeys = {
  all: ["chat"] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
  conversation: (id: string) => [...chatKeys.all, "conversation", id] as const,
};

export function useConversations() {
  return useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: async () => (await chatService.listConversations()).data,
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: chatKeys.conversation(id ?? ""),
    queryFn: async () => (await chatService.getConversation(id ?? "")).data,
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await chatService.createConversation()).data,
    onSuccess: (conv) => {
      qc.setQueryData<Conversation[]>(chatKeys.conversations(), (prev) => [conv, ...(prev ?? [])]);
      qc.setQueryData<ConversationDetail>(chatKeys.conversation(conv.id), { conversation: conv, messages: [] });
    },
  });
}

export function useRenameConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; title: string }) => (await chatService.rename(v.id, v.title)).data,
    onSuccess: (conv) => {
      qc.setQueryData<Conversation[]>(chatKeys.conversations(), (prev) => (prev ?? []).map((c) => (c.id === conv.id ? { ...c, ...conv } : c)));
      qc.setQueryData<ConversationDetail>(chatKeys.conversation(conv.id), (prev) => (prev ? { ...prev, conversation: { ...prev.conversation, ...conv } } : prev));
    },
  });
}

/** H9 starter questions; falls back to static suggestions in the page if the call fails. */
export function useSuggestions(conversationId: string | null) {
  return useQuery({
    queryKey: [...chatKeys.all, "suggestions", conversationId ?? "none"] as const,
    queryFn: async () => (await chatService.suggestions(conversationId)).data.suggestions,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}

function patchMessage(qc: ReturnType<typeof useQueryClient>, convId: string, id: string, patch: Partial<Message>) {
  qc.setQueryData<ConversationDetail>(chatKeys.conversation(convId), (prev) =>
    prev ? { ...prev, messages: prev.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)) } : prev,
  );
}

/** H7 / H8 with optimistic updates and rollback. */
export function useMessageActions(convId: string | null) {
  const qc = useQueryClient();
  const bookmark = useMutation({
    mutationFn: async (v: { id: string; bookmarked: boolean }) => (await chatService.bookmark(v.id, v.bookmarked)).data,
    onMutate: (v) => {
      if (convId) patchMessage(qc, convId, v.id, { bookmarked: v.bookmarked });
    },
    onError: (_e, v) => {
      if (convId) patchMessage(qc, convId, v.id, { bookmarked: !v.bookmarked });
    },
  });
  const feedback = useMutation({
    mutationFn: async (v: { id: string; rating: "up" | "down"; previous: "up" | "down" | null | undefined }) => {
      await chatService.feedback(v.id, v.rating);
    },
    onMutate: (v) => {
      if (convId) patchMessage(qc, convId, v.id, { feedback: v.rating });
    },
    onError: (_e, v) => {
      if (convId) patchMessage(qc, convId, v.id, { feedback: v.previous ?? null });
    },
  });
  return { bookmark, feedback };
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await chatService.deleteConversation(id);
      return id;
    },
    onSuccess: (id) => {
      qc.setQueryData<Conversation[]>(chatKeys.conversations(), (prev) => (prev ?? []).filter((c) => c.id !== id));
      qc.removeQueries({ queryKey: chatKeys.conversation(id) });
    },
  });
}
