import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

/** Shows while the browser is offline; refetches everything when the connection returns. */
export function ConnectionBanner() {
  const qc = useQueryClient();
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  useEffect(() => {
    const on = () => {
      setOnline(true);
      void qc.invalidateQueries();
    };
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, [qc]);
  if (online) return null;
  return (
    <div
      role="status"
      className="pointer-events-none fixed inset-x-4 bottom-[calc(var(--nk-bottom-nav-h)+env(safe-area-inset-bottom)+12px)] z-[75] mx-auto flex w-fit max-w-full items-center justify-center gap-2 rounded-chip border border-warning/40 bg-overlay px-4 py-2 text-body-sm text-fg shadow-e2 md:bottom-6"
    >
      <WifiOff aria-hidden="true" className="size-4 text-warning" />
      You're offline. Nakshion will reconnect on its own.
    </div>
  );
}
