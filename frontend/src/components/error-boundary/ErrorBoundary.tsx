/** Error boundary — catches render errors without leaking stack traces. */

import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback: (props: { error: Error; reset: () => void }) => ReactNode;
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

  override componentDidCatch(_error: Error, _errorInfo: ErrorInfo): void {
    console.error("[CampusVault ErrorBoundary]", _errorInfo.componentStack);
  }

  reset = (): void => this.setState({ hasError: false, error: null });

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback({
        error: this.state.error ?? new Error("Unknown error"),
        reset: this.reset,
      });
    }
    return this.props.children;
  }
}
