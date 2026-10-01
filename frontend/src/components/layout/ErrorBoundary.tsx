import { Component, type ErrorInfo, type ReactNode } from "react";
import { CloudOff } from "lucide-react";
import { EmptyState } from "../ui/EmptyState";
import { Button } from "../ui/Button";

interface State {
  failed: boolean;
}

/** Last line of defence: an unexpected render error shows a calm page instead of a blank screen. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled render error", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="flex min-h-svh items-center justify-center px-4">
        <EmptyState
          tone="danger"
          icon={<CloudOff />}
          title="Something went wrong on this page"
          body="Reloading usually fixes it. Your data is safe."
          action={<Button variant="secondary" onClick={() => window.location.reload()}>Reload</Button>}
        />
      </div>
    );
  }
}
