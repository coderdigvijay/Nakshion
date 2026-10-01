import { MessageCircle, Plus, Trash2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { formatRelativeTime } from "../../lib/format";
import type { Conversation } from "../../types";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Skeleton } from "../ui/Skeleton";
import { ErrorState } from "../ui/EmptyState";

export interface ConversationListProps {
  conversations: Conversation[] | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (c: Conversation) => void;
  creating?: boolean;
}

export function ConversationList({ conversations, isLoading, error, onRetry, activeId, onSelect, onNew, onDelete, creating }: ConversationListProps) {
  return (
    <nav aria-label="Conversations" className="flex h-full flex-col">
      <div className="p-4">
        <Button fullWidth leadingIcon={<Plus aria-hidden="true" className="size-4" />} onClick={onNew} loading={creating}>
          New chat
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {isLoading ? (
          <div aria-busy="true" className="space-y-2 px-2">
            <span className="sr-only" role="status">
              Loading conversations
            </span>
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 rounded-control" />
            ))}
          </div>
        ) : error ? (
          <div className="px-2">
            <ErrorState compact error={error} what="your conversations" onRetry={onRetry} />
          </div>
        ) : !conversations || conversations.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <MessageCircle aria-hidden="true" className="mx-auto size-6 text-fg-muted" />
            <p className="mt-2 text-body-sm text-fg-secondary">No conversations yet.</p>
            <p className="text-caption text-fg-muted">Your questions will be saved here.</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {conversations.map((c) => {
              const active = c.id === activeId;
              const title = c.title || "New conversation";
              return (
                <li key={c.id} className="group relative">
                  <button
                    type="button"
                    aria-current={active ? "page" : undefined}
                    onClick={() => onSelect(c.id)}
                    className={cn(
                      "focus-ring flex min-h-14 w-full cursor-pointer flex-col justify-center rounded-control py-2 pl-4 pr-12 text-left",
                      active ? "bg-ai-subtle shadow-[inset_3px_0_0_var(--nk-ai)]" : "hover:bg-elevated",
                    )}
                  >
                    <span className={cn("truncate text-body-sm", active ? "font-semibold text-fg" : "font-medium text-fg-secondary")}>{title}</span>
                    <span className="text-caption text-fg-muted">{formatRelativeTime(c.updated_at)}</span>
                  </button>
                  <IconButton
                    aria-label={`Delete conversation: ${title}`}
                    size="sm"
                    onClick={() => onDelete(c)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-100 md:opacity-0 md:focus-visible:opacity-100 md:group-hover:opacity-100"
                  >
                    <Trash2 aria-hidden="true" />
                  </IconButton>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </nav>
  );
}
