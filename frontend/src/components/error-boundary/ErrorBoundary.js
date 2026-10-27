import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Error boundary — catches render errors without leaking stack traces. */
import { Component } from "react";
export class ErrorBoundary extends Component {
    state = { hasError: false, error: null };
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    componentDidCatch(_error, errorInfo) {
        console.error("[CampusVault ErrorBoundary]", errorInfo.componentStack);
    }
    reset = () => this.setState({ hasError: false, error: null });
    render() {
        if (this.state.hasError) {
            const fallback = this.props.fallback ?? DefaultFallback;
            return _jsx("fallback", { error: this.state.error ?? new Error("Unknown error"), reset: this.reset });
        }
        return this.props.children;
    }
}
function DefaultFallback({ error, reset }) {
    return (_jsxs("div", { className: "flex flex-col items-center justify-center py-12 text-center", children: [_jsx("h2", { className: "text-body-lg font-semibold text-ink-default", children: "Something went wrong" }), _jsx("p", { className: "text-body-sm text-ink-secondary mt-2", children: error.message }), _jsx("button", { onClick: reset, className: "mt-4 px-4 py-2 text-body-sm font-medium text-brand hover:underline", children: "Try again" })] }));
}
