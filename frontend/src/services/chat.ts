import api, { API_BASE_URL } from "./api";
import { HttpError } from "./errors";
import type { ChatLanguage, ChatStreamEvent, Conversation, ConversationDetail, Message } from "../types";

/** Server deadline is 25 s (api-contract H5); give the network a little headroom (gap G-10). */
const SEND_TIMEOUT_MS = 30_000;

export const chatService = {
  createConversation: () => api.post<Conversation>("/chat/conversations", {}),

  listConversations: () => api.get<Conversation[]>("/chat/conversations"),

  getConversation: (id: string) => api.get<ConversationDetail>(`/chat/conversations/${id}`),

  deleteConversation: (id: string) => api.delete(`/chat/conversations/${id}`),

  /** H10 rename. */
  rename: (id: string, title: string) => api.patch<Conversation>(`/chat/conversations/${id}`, { title }),

  /** H7 */
  bookmark: (messageId: string, bookmarked: boolean) =>
    api.put<Message>(`/chat/messages/${messageId}/bookmark`, { bookmarked }),

  /** H8: 204. Feeds the eval set. */
  feedback: (messageId: string, rating: "up" | "down") => api.post(`/chat/messages/${messageId}/feedback`, { rating }),

  /** H9: template-driven from the user's chart, no LLM cost. */
  suggestions: (conversationId?: string | null) =>
    api.get<{ suggestions: string[] }>("/chat/suggestions", { params: conversationId ? { conversation_id: conversationId } : {} }),

  /**
   * H5 (MVP, non-streaming): resolves to exactly [savedUserMessage, assistantMessage].
   * `signal` lets the Stop button abort the wait. Streaming (H6) is v1-add and not wired yet.
   */
  sendMessage: (conversationId: string, content: string, language: ChatLanguage = "english", signal?: AbortSignal) =>
    api.post<Message[]>(
      `/chat/conversations/${conversationId}/messages`,
      { content, language },
      { timeout: SEND_TIMEOUT_MS, signal },
    ),
};

function parseSseBlock(block: string): ChatStreamEvent | null {
  let event = "";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!event || data.length === 0) return null;
  try {
    const payload = JSON.parse(data.join("\n")) as Record<string, unknown>;
    return { type: event, ...payload } as ChatStreamEvent;
  } catch {
    return null;
  }
}

/**
 * H6 streaming send. axios can't stream in browsers, so this uses fetch + ReadableStream
 * (api-contract H6). Yields typed SSE events; pre-stream failures (404/403/409/422/429)
 * throw HttpError so callers handle them exactly like the non-streaming path.
 */
export async function* streamMessage(
  conversationId: string,
  content: string,
  language: ChatLanguage,
  signal: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  let token: string | null = null;
  try {
    token = localStorage.getItem("token");
  } catch {
    token = null;
  }
  const res = await fetch(`${API_BASE_URL}/chat/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ content, language }),
    signal,
  });
  if (!res.ok || !res.body) {
    let code: string | undefined;
    let detail = "";
    let extra: { resetsAt?: string; limit?: number } = {};
    try {
      const body = (await res.json()) as { detail?: unknown; code?: unknown; resets_at?: unknown; limit?: unknown };
      extra = { resetsAt: typeof body.resets_at === "string" ? body.resets_at : undefined, limit: typeof body.limit === "number" ? body.limit : undefined };
      if (typeof body.detail === "string") detail = body.detail;
      if (typeof body.code === "string") code = body.code;
    } catch {
      // Non-JSON error body: fall through to the status-based fallback.
    }
    if (res.status === 401) {
      try {
        localStorage.removeItem("token");
      } catch {
        // storage unavailable
      }
      if (!window.location.pathname.startsWith("/auth")) window.location.href = "/auth?expired=1";
    }
    const retry = Number(res.headers.get("Retry-After"));
    throw new HttpError(res.status, code, detail || "Something went wrong. Please try again.", Number.isFinite(retry) && retry > 0 ? retry : undefined, extra);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const ev = parseSseBlock(buffer.slice(0, idx));
        buffer = buffer.slice(idx + 2);
        if (ev) yield ev;
      }
    }
    const tail = parseSseBlock(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}
