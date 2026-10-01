import axios from "axios";

/** Normalised API error (docs/api-contract.md §1.3). */
export interface ApiError {
  status: number | undefined;
  code: string | undefined;
  /** Human-readable, safe to show. */
  detail: string;
  /** Seconds, from the Retry-After header on 429. */
  retryAfter: number | undefined;
  /** True when the request never got a response (offline, CORS, server asleep). */
  network: boolean;
  /** True when the user cancelled (Stop button). */
  aborted: boolean;
  /** 429 QUOTA_EXCEEDED: when the quota resets (ISO, UTC) and the plan's limit. */
  resetsAt?: string;
  limit?: number;
}

/** "5:30 AM" in the viewer's local zone, with "tomorrow" when it falls on another day. */
export function formatResetTime(iso: string): string | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const time = d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  return d.toDateString() === new Date().toDateString() ? time : `tomorrow at ${time}`;
}

/** Plain-language quota copy: server detail plus the reset time converted to local time. */
export function quotaMessage(e: ApiError): string {
  const at = e.resetsAt ? formatResetTime(e.resetsAt) : null;
  const base = e.detail.replace(/\s*They reset at midnight[^.]*\./i, "").trim();
  return at ? `${base} Resets at ${at}.` : base;
}

export function isNotFound(e: ApiError): boolean {
  return e.code === "NOT_FOUND" || e.status === 404;
}

const STATUS_FALLBACK: Record<number, string> = {
  400: "That didn't work. Check the details and try again.",
  401: "Your session has ended. Please sign in again.",
  403: "You don't have access to this yet.",
  404: "We couldn't find that. It may have been deleted.",
  409: "That conflicts with something already saved.",
  413: "That is too much to send at once. Please shorten it and try again.",
  422: "Some details need fixing before we can continue.",
  429: "You've hit a limit for now. Please try again a little later.",
  500: "Something went wrong on our side. Please try again.",
  503: "Nakshion is resting for a moment. Please try again shortly.",
};

/** Server copy is plain text; strip any stray markdown emphasis/backticks so users never see "*your*". */
function plain(text: string): string {
  return text.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*\n]+)\*/g, "$1").replace(/`([^`]+)`/g, "$1");
}

function detailFromBody(data: unknown): string | undefined {
  if (typeof data !== "object" || data === null) return undefined;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return plain(detail);
  // FastAPI's default 422 shape (array) — contract gap G-02. Read the first message defensively.
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first?.msg === "string") return plain(first.msg);
  }
  return undefined;
}

/** Non-2xx response from a fetch-based call (the streaming chat endpoint). */
export class HttpError extends Error {
  status: number;
  code: string | undefined;
  detail: string;
  retryAfter: number | undefined;
  resetsAt: string | undefined;
  limit: number | undefined;

  constructor(status: number, code: string | undefined, detail: string, retryAfter: number | undefined, extra: { resetsAt?: string; limit?: number } = {}) {
    super(detail);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.retryAfter = retryAfter;
    this.resetsAt = extra.resetsAt;
    this.limit = extra.limit;
  }
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof HttpError) {
    return { status: err.status, code: err.code, detail: plain(err.detail), retryAfter: err.retryAfter, network: false, aborted: false, resetsAt: err.resetsAt, limit: err.limit };
  }
  if (axios.isCancel(err) || (err instanceof DOMException && err.name === "AbortError")) {
    return { status: undefined, code: "ABORTED", detail: "Stopped.", retryAfter: undefined, network: false, aborted: true };
  }
  if (axios.isAxiosError(err)) {
    if (err.code === "ERR_CANCELED") {
      return { status: undefined, code: "ABORTED", detail: "Stopped.", retryAfter: undefined, network: false, aborted: true };
    }
    const res = err.response;
    if (!res) {
      const timedOut = err.code === "ECONNABORTED" || err.code === "ETIMEDOUT";
      return {
        status: undefined,
        code: timedOut ? "TIMEOUT" : "NETWORK",
        detail: timedOut
          ? "This is taking longer than usual. Please try again."
          : "We couldn't reach Nakshion. Check your connection and try again.",
        retryAfter: undefined,
        network: true,
        aborted: false,
      };
    }
    const data = res.data as { code?: unknown; resets_at?: unknown; limit?: unknown } | undefined;
    const retryHeader = res.headers?.["retry-after"];
    const retryAfter = retryHeader !== undefined ? Number(retryHeader) : undefined;
    return {
      status: res.status,
      code: typeof data?.code === "string" ? data.code : undefined,
      detail: detailFromBody(res.data) ?? STATUS_FALLBACK[res.status] ?? STATUS_FALLBACK[500],
      retryAfter: Number.isFinite(retryAfter) ? retryAfter : undefined,
      network: false,
      aborted: false,
      resetsAt: typeof data?.resets_at === "string" ? data.resets_at : undefined,
      limit: typeof data?.limit === "number" ? data.limit : undefined,
    };
  }
  if (err instanceof Error && err.message) {
    return { status: undefined, code: undefined, detail: err.message, retryAfter: undefined, network: false, aborted: false };
  }
  return { status: undefined, code: undefined, detail: STATUS_FALLBACK[500], retryAfter: undefined, network: false, aborted: false };
}

export function errorMessage(err: unknown): string {
  return toApiError(err).detail;
}

export function errorStatus(err: unknown): number | undefined {
  return toApiError(err).status;
}
