/** Error boundary — catches render errors without leaking stack traces. */

import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(_error: Error, errorInfo: ErrorInfo): void {
    console.error("[CampusVault ErrorBoundary]", errorInfo.componentStack);
  }

  reset = (): void => this.setState({ hasError: false, error: null });

  render(): ReactNode {
    if (this.state.hasError) {
      const fallback = this.props.fallback ?? DefaultFallback;
      return <fallback error={this.state.error ?? new Error("Unknown error")} reset={this.reset} />;
    }
    return this.props.children;
  }
}

function DefaultFallback({ error, reset }: { error: Error; reset: () => void }): ReactNode {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <h2 className="text-body-lg font-semibold text-ink-default">Something went wrong</h2>
      <p className="text-body-sm text-ink-secondary mt-2">
        {error.message}
      </p>
      <button onClick={reset} className="mt-4 px-4 py-2 text-body-sm font-medium text-brand hover:underline">
        Try again
      </button>
    </div>
  );
}
