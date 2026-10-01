import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowDown, ArrowLeft, History, MailWarning, Pencil, Plus } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { ChatInput } from "../components/chat/ChatInput";
import { ChatMessage, type ChatMessageStatus } from "../components/chat/ChatMessage";
import { ConversationList } from "../components/chat/ConversationList";
import { AiAvatar } from "../components/ui/Avatar";
import { Button, ButtonLink } from "../components/ui/Button";
import { Chip } from "../components/ui/Badge";
import { Dialog } from "../components/ui/Dialog";
import { IconButton } from "../components/ui/IconButton";
import { Skeleton } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/EmptyState";
import { chatKeys, useConversation, useConversations, useCreateConversation, useDeleteConversation, useMessageActions, useRenameConversation, useSuggestions } from "../hooks/useChat";
import { Input } from "../components/ui/Field";
import { streamMessage } from "../services/chat";
import { HttpError, quotaMessage, toApiError, type ApiError } from "../services/errors";
import { useAuthStore } from "../store/authStore";
import { usePrefsStore } from "../store/prefsStore";
import { toast } from "../store/toastStore";
import { firstName } from "../lib/format";
import type { Conversation, ConversationDetail, Message } from "../types";

const SUGGESTIONS = [
  "What does my chart say about love?",
  "Is this a good month for a job change?",
  "What does my current dasha mean?",
  "What should I focus on today?",
];

interface PendingTurn {
  id: string;
  content: string;
  createdAt: string;
  status: "thinking" | "streaming" | "interrupted" | "failed";
  /** Assistant text received so far (streaming). */
  text: string;
  error?: ApiError;
}

/** Blocking states that disable the composer (contract §6 H5 pre-checks). */
function blockingNotice(err: ApiError | null) {
  if (!err) return null;
  if (err.status === 429 && err.code === "QUOTA_EXCEEDED") return { kind: "quota" as const, text: quotaMessage(err) };
  if (err.status === 403 && err.code === "EMAIL_NOT_VERIFIED") return { kind: "verify" as const, text: err.detail };
  if (err.status === 409 && err.code === "CHART_REQUIRED") return { kind: "chart" as const, text: err.detail };
  return null;
}

export default function ChatPage() {
  const qc = useQueryClient();
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const language = usePrefsStore((s) => s.language);
  const setLanguage = usePrefsStore((s) => s.setLanguage);

  const conversations = useConversations();
  const [activeId, setActiveId] = useState<string | null>(null);
  // Conversations with no messages (aborted first sends, refresh mid-stream) stay out of the list.
  const visibleConversations = conversations.data?.filter((c) => c.message_count > 0);
  const effectiveId = activeId ?? visibleConversations?.[0]?.id ?? null;
  const detail = useConversation(effectiveId);
  const createConv = useCreateConversation();
  const deleteConv = useDeleteConversation();
  const rename = useRenameConversation();
  const actions = useMessageActions(effectiveId);
  const suggestionsQ = useSuggestions(effectiveId);
  const [renaming, setRenaming] = useState(false);
  const [renameText, setRenameText] = useState("");

  const [draft, setDraft] = useState<string>(() => (location.state as { draft?: string } | null)?.draft ?? "");
  const [pending, setPending] = useState<PendingTurn | null>(null);
  const [blocking, setBlocking] = useState<ApiError | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [toDelete, setToDelete] = useState<Conversation | null>(null);
  const [showJump, setShowJump] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [announce, setAnnounce] = useState("");

  const messages: Message[] = detail.data?.messages ?? [];
  const busy = pending?.status === "thinking" || pending?.status === "streaming";

  // Auto-follow only when the reader is near the bottom (COMPONENTS.md → ChatMessage scroll).
  const nearBottom = () => {
    const el = logRef.current;
    return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };
  const scrollToBottom = useCallback(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    setShowJump(false);
  }, []);
  // First paint of a thread: jump to the end silently. The "New reply" pill is only for replies that
  // arrive while the reader has scrolled up.
  const settledFor = useRef<string | null>(null);
  useEffect(() => {
    if (detail.isLoading) return;
    if (settledFor.current !== effectiveId) {
      settledFor.current = effectiveId;
      scrollToBottom();
      return;
    }
    if (nearBottom()) scrollToBottom();
    else setShowJump(true);
  }, [messages.length, pending, scrollToBottom, effectiveId, detail.isLoading]);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || busy) return;
      setBlocking(null);
      const turn: PendingTurn = { id: `p-${Date.now()}`, content, createdAt: new Date().toISOString(), status: "thinking", text: "" };
      setPending(turn);
      setDraft("");
      requestAnimationFrame(scrollToBottom);

      let convId = effectiveId;
      let createdHere: string | null = null;
      let received = "";
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        if (!convId) {
          const conv = await createConv.mutateAsync();
          convId = conv.id;
          createdHere = conv.id;
          setActiveId(conv.id);
        }
        let finished = false;
        for await (const ev of streamMessage(convId, content, language, controller.signal)) {
          if (ev.type === "delta") {
            received += ev.text;
            setPending((p) => (p ? { ...p, status: "streaming", text: received } : p));
          } else if (ev.type === "replace") {
            received = ev.text;
            setPending((p) => (p ? { ...p, status: "streaming", text: received } : p));
          } else if (ev.type === "done") {
            finished = true;
            const cid = convId;
            qc.setQueryData<ConversationDetail>(chatKeys.conversation(cid), (prev) =>
              prev
                ? {
                    ...prev,
                    messages: [
                      ...prev.messages,
                      { id: turn.id, conversation_id: cid, role: "user", content, created_at: turn.createdAt },
                      ev.assistant_message,
                    ],
                  }
                : prev,
            );
            void qc.invalidateQueries({ queryKey: chatKeys.conversation(cid) });
            void qc.invalidateQueries({ queryKey: chatKeys.conversations() });
            setPending(null);
            setAnnounce(`Nakshion replied: ${ev.assistant_message.content.slice(0, 140)}`);
          } else if (ev.type === "error") {
            finished = true;
            throw new HttpError(ev.code === "AI_UNAVAILABLE" ? 503 : 500, ev.code, ev.detail, undefined);
          }
        }
        if (!finished) throw new HttpError(503, "STREAM_CLOSED", "The connection closed before the answer finished.", undefined);
      } catch (err) {
        const e = toApiError(err);
        const partial = received.trim().length > 0;
        if (blockingNotice(e)) {
          setDraft((d) => (d.trim() ? d : content));
          setPending(null);
          setBlocking(e);
        } else if (partial) {
          // Keep what arrived; the question was answered in part, so it stays out of the composer.
          setPending({ ...turn, status: "interrupted", text: received, error: e });
        } else {
          // Preserve the question: put it back in the composer unless the user already typed something new.
          setDraft((d) => (d.trim() ? d : content));
          setPending({ ...turn, status: "failed", error: e });
        }
        if (createdHere && !partial && !e.aborted) {
          // Nothing was saved: drop the empty conversation we just created (best effort).
          const empty = createdHere;
          deleteConv.mutate(empty, { onSettled: () => setActiveId((a) => (a === empty ? null : a)) });
        }
        const cid = convId;
        if (cid && (e.aborted || partial)) {
          // The server may still have saved the reply; refresh shortly so history matches.
          setTimeout(() => void qc.invalidateQueries({ queryKey: chatKeys.conversation(cid) }), 4000);
        }
      } finally {
        abortRef.current = null;
      }
    },
    [busy, effectiveId, createConv, deleteConv, language, qc, scrollToBottom],
  );

  // Suggestion handoff from other screens: { send } sends once, { draft } only pre-fills.
  const handoffDone = useRef(false);
  useEffect(() => {
    const st = location.state as { send?: string } | null;
    if (!handoffDone.current && st?.send && !conversations.isLoading) {
      handoffDone.current = true;
      navigate(location.pathname, { replace: true, state: null });
      void send(st.send);
    }
  }, [location, navigate, send, conversations.isLoading]);

  // "/" focuses the composer when not typing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.key === "/" && t && !["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName) && !t.isContentEditable) {
        e.preventDefault();
        composerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const stop = () => abortRef.current?.abort();

  const newChat = () => {
    createConv.mutate(undefined, {
      onSuccess: (c) => {
        setActiveId(c.id);
        setPending(null);
        setHistoryOpen(false);
        composerRef.current?.focus();
      },
      onError: (err) => toast.error("Couldn't start a new chat", toApiError(err).detail),
    });
  };

  const confirmDelete = () => {
    if (!toDelete) return;
    const id = toDelete.id;
    deleteConv.mutate(id, {
      onSuccess: () => {
        if (effectiveId === id) setActiveId(null);
        setToDelete(null);
        toast.success("Conversation deleted");
      },
      onError: (err) => toast.error("Couldn't delete the conversation", toApiError(err).detail),
    });
  };

  const notice = blockingNotice(blocking);
  const active = conversations.data?.find((c) => c.id === effectiveId);
  const showEmpty = !detail.isLoading && messages.length === 0 && !pending;

  const list = (
    <ConversationList
      conversations={visibleConversations}
      isLoading={conversations.isLoading}
      error={conversations.error}
      onRetry={() => void conversations.refetch()}
      activeId={effectiveId}
      onSelect={(id) => {
        setActiveId(id);
        setPending(null);
        setHistoryOpen(false);
      }}
      onNew={newChat}
      onDelete={setToDelete}
      creating={createConv.isPending}
    />
  );

  return (
    <AppShell hideBottomNav fullHeight>
      <div className="flex h-full md:h-[calc(100svh-var(--nk-header-h))]">
        <aside className="hidden w-[280px] shrink-0 border-r border-border bg-surface lg:block">{list}</aside>

        <section aria-labelledby="chat-title" className="flex min-w-0 flex-1 flex-col bg-bg">
          <header className="flex h-14 shrink-0 items-center gap-1 border-b border-border px-2 md:px-4">
            <IconButton aria-label="Back to Today" className="md:hidden" onClick={() => navigate("/dashboard")}>
              <ArrowLeft aria-hidden="true" />
            </IconButton>
            <IconButton aria-label="Conversation history" className="lg:hidden" onClick={() => setHistoryOpen(true)}>
              <History aria-hidden="true" />
            </IconButton>
            <div className="min-w-0 flex-1 px-1">
              <h1 id="chat-title" className="truncate font-sans text-title text-fg">
                {active?.title || "Ask Nakshion"}
              </h1>
            </div>
            {active && (
              <IconButton
                aria-label="Rename conversation"
                onClick={() => {
                  setRenameText(active.title ?? "");
                  setRenaming(true);
                }}
              >
                <Pencil aria-hidden="true" />
              </IconButton>
            )}
            <IconButton aria-label="New chat" className="lg:hidden" onClick={newChat} disabled={createConv.isPending}>
              <Plus aria-hidden="true" />
            </IconButton>
          </header>

          <div
            ref={logRef}
            role="log"
            aria-live="polite"
            aria-relevant="additions"
            aria-label="Conversation"
            onScroll={() => {
              if (nearBottom()) setShowJump(false);
            }}
            className="relative min-h-0 flex-1 overflow-y-auto"
          >
            <div className="mx-auto max-w-chat space-y-8 px-4 py-6 md:px-6">
              {conversations.isError && (
                <ErrorState compact className="lg:hidden" error={conversations.error} what="your conversations" onRetry={() => void conversations.refetch()} />
              )}
              {detail.isLoading ? (
                <div aria-busy="true" className="space-y-8">
                  <span role="status" className="sr-only">
                    Loading messages
                  </span>
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="space-y-4">
                      <Skeleton className="ml-auto h-12 w-2/3 rounded-bubble" />
                      <div className="space-y-2">
                        <Skeleton className="h-8 w-32 rounded-chip" />
                        <Skeleton className="h-3 w-full" />
                        <Skeleton className="h-3 w-4/5" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : detail.isError ? (
                <ErrorState error={detail.error} what="this conversation" onRetry={() => void detail.refetch()} retrying={detail.isFetching} notFoundAction={{ label: "Back to your conversations", onClick: () => { setActiveId(null); setHistoryOpen(true); } }} />
              ) : showEmpty ? (
                <div className="flex flex-col items-center pt-[8vh] text-center">
                  <AiAvatar size="lg" />
                  <h2 className="mt-4 text-h2 text-fg">What's on your mind{firstName(user?.name) ? `, ${firstName(user?.name)}` : ""}?</h2>
                  <p className="mt-2 max-w-md text-body text-fg-secondary">
                    I'll answer from your own chart — your Moon, your current dasha and today's transits — not generic sun-sign text.
                  </p>
                  <ul className="mt-6 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                    {(suggestionsQ.data && suggestionsQ.data.length > 0 ? suggestionsQ.data.slice(0, 4) : SUGGESTIONS).map((s) => (
                      <li key={s}>
                        <Chip kind="suggestion" className="w-full justify-start py-2" onClick={() => void send(s)} disabled={!!notice}>
                          {s}
                        </Chip>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <>
                  {messages.map((m) => (
                    <ChatMessage
                      key={m.id}
                      role={m.role}
                      content={m.content}
                      createdAt={m.created_at}
                      citations={m.citations}
                      sources={m.sources}
                      lang={m.role === "assistant" && language === "hindi" ? "hi" : undefined}
                      messageId={m.role === "assistant" ? m.id : undefined}
                      bookmarked={m.bookmarked}
                      feedback={m.feedback}
                      onBookmark={(b) => actions.bookmark.mutate({ id: m.id, bookmarked: b }, { onError: (err) => toast.error("Couldn't save the bookmark", toApiError(err).detail) })}
                      onFeedback={(rating) =>
                        actions.feedback.mutate(
                          { id: m.id, rating, previous: m.feedback },
                          { onSuccess: () => toast.info("Thanks for the feedback"), onError: (err) => toast.error("Couldn't send feedback", toApiError(err).detail) },
                        )
                      }
                    />
                  ))}
                  {pending && (
                    <>
                      <ChatMessage
                        role="user"
                        content={pending.content}
                        createdAt={pending.createdAt}
                        status={pending.status === "failed" ? "failed" : "complete"}
                        errorText={pending.error?.aborted ? "Stopped. Your question is back in the box." : undefined}
                        onRetry={pending.status === "failed" ? () => void send(pending.content) : undefined}
                      />
                      {(pending.status === "thinking" || pending.status === "streaming" || pending.status === "interrupted") && (
                        <ChatMessage
                          role="assistant"
                          content={pending.text}
                          status={pending.status satisfies ChatMessageStatus}
                          onRetry={pending.status === "interrupted" ? () => void send(pending.content) : undefined}
                        />
                      )}
                      {pending.status === "failed" && !pending.error?.aborted && (
                        <ChatMessage
                          role="assistant"
                          content=""
                          status="error"
                          errorText={
                            pending.error?.status === 503
                              ? "Nakshion couldn't answer just now. Your question is saved in the box below."
                              : pending.error && pending.error.status && pending.error.status < 500
                                ? pending.error.detail
                                : "Nakshion couldn't answer just now."
                          }
                          onRetry={() => void send(pending.content)}
                        />
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="relative shrink-0 border-t border-border bg-bg px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 md:px-6">
            {showJump && (
              <button
                type="button"
                onClick={scrollToBottom}
                className="focus-ring absolute -top-12 left-1/2 flex min-h-9 -translate-x-1/2 cursor-pointer items-center gap-1.5 rounded-chip border border-border bg-overlay px-3 text-body-sm text-fg shadow-e2"
              >
                <ArrowDown aria-hidden="true" className="size-4" /> New reply
              </button>
            )}
            <div className="mx-auto max-w-chat">
              {notice && (
                <div className="mb-3 flex flex-col gap-3 rounded-control bg-warning-subtle p-3 sm:flex-row sm:items-center" role="alert">
                  {notice.kind === "verify" ? (
                    <MailWarning aria-hidden="true" className="size-5 shrink-0 text-warning" />
                  ) : (
                    <AlertTriangle aria-hidden="true" className="size-5 shrink-0 text-warning" />
                  )}
                  <p className="flex-1 text-body-sm text-fg">{notice.text}</p>
                  {notice.kind === "verify" && (
                    <ButtonLink to="/verify" size="sm" variant="secondary">
                      Verify now
                    </ButtonLink>
                  )}
                  {notice.kind === "chart" && (
                    <ButtonLink to="/onboarding" size="sm" variant="secondary">
                      Add birth details
                    </ButtonLink>
                  )}
                  {notice.kind === "quota" && (
                    <Button size="sm" variant="ghost" onClick={() => setBlocking(null)}>
                      Dismiss
                    </Button>
                  )}
                </div>
              )}
              <ChatInput
                inputRef={composerRef}
                value={draft}
                onChange={setDraft}
                onSend={() => void send(draft)}
                onStop={stop}
                busy={busy}
                language={language}
                onLanguageChange={setLanguage}
                disabledReason={notice?.text}
              />
            </div>
          </div>
        </section>
      </div>

      <span className="sr-only" aria-live="polite">
        {busy ? "Nakshion is thinking" : announce}
      </span>

      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Conversations" presentation="sheet">
        <div className="-mx-5 h-[60dvh]">{list}</div>
      </Dialog>

      <Dialog
        open={renaming}
        onClose={() => setRenaming(false)}
        title="Rename conversation"
        presentation="dialog"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRenaming(false)}>
              Cancel
            </Button>
            <Button type="submit" form="rename-form" variant="primary" disabled={!renameText.trim()} loading={rename.isPending}>
              Save
            </Button>
          </>
        }
      >
        <form
          id="rename-form"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (!active || !renameText.trim()) return;
            rename.mutate(
              { id: active.id, title: renameText.trim() },
              {
                onSuccess: () => {
                  setRenaming(false);
                  toast.success("Renamed");
                },
                onError: (err) => toast.error("Couldn't rename", toApiError(err).detail),
              },
            );
          }}
        >
          <Input label="Title" maxLength={255} autoFocus value={renameText} onChange={(e) => setRenameText(e.target.value)} />
        </form>
      </Dialog>

      <Dialog
        open={!!toDelete}
        onClose={() => setToDelete(null)}
        title="Delete this conversation?"
        description={`“${toDelete?.title || "New conversation"}” and all its messages will be removed. This can't be undone.`}
        presentation="dialog"
        footer={
          <>
            <Button variant="secondary" onClick={() => setToDelete(null)} autoFocus>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete} loading={deleteConv.isPending}>
              Delete conversation
            </Button>
          </>
        }
      />
    </AppShell>
  );
}
