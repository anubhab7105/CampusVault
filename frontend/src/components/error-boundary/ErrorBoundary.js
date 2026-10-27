/** Error boundary — catches render errors without leaking stack traces. */
import { Component } from "react";
export class ErrorBoundary extends Component {
    state = { hasError: false, error: null };
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    componentDidCatch(_error, _errorInfo) {
        console.error("[CampusVault ErrorBoundary]", _errorInfo.componentStack);
    }
    reset = () => this.setState({ hasError: false, error: null });
    render() {
        if (this.state.hasError) {
            return this.props.fallback({
                error: this.state.error ?? new Error("Unknown error"),
                reset: this.reset,
            });
        }
        return this.props.children;
    }
}
