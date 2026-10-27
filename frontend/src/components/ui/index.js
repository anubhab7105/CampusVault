import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/** Base UI components — accessible, mobile-first, dark-mode aware. */
import { cn } from "@utils/cn";
export const Button = React.forwardRef(({ className, variant = "default", size = "md", isLoading, children, disabled, ...props }, ref) => {
    const variants = {
        default: "bg-brand text-white hover:bg-brand-900 active:bg-brand-900",
        destructive: "bg-red-600 text-white hover:bg-red-700",
        outline: "border border-border bg-surface-50 hover:bg-surface-100",
        secondary: "bg-surface-100 text-ink-default hover:bg-surface-200",
        ghost: "text-ink-secondary hover:bg-surface-100",
        link: "text-brand underline-offset-4 hover:underline",
    };
    const sizes = {
        sm: "px-3 py-1.5 text-body-sm",
        md: "px-4 py-2 text-body-md",
        lg: "px-6 py-3 text-body-lg",
    };
    return (_jsx("button", { ref: ref, className: cn("inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brandFocus disabled:pointer-events-none disabled:opacity-50", variants[variant], sizes[size], className), disabled: disabled || isLoading, ...props, children: isLoading ? (_jsxs("span", { className: "flex items-center gap-2", children: [_jsxs("svg", { className: "animate-spin h-4 w-4", xmlns: "http://www.w3.org/2000/svg", fill: "none", viewBox: "0 0 24 24", children: [_jsx("circle", { className: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", strokeWidth: "4" }), _jsx("path", { className: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8V0C5.373 0 2 5.373 2 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" })] }), "Loading\u2026"] })) : (children) }));
});
Button.displayName = "Button";
export const Input = React.forwardRef(({ className, label, error, helperText, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).slice(2)}`;
    return (_jsxs("div", { className: "w-full space-y-1", children: [label && (_jsx("label", { htmlFor: inputId, className: "block text-body-sm font-medium text-ink-secondary", children: label })), _jsx("input", { ref: ref, id: inputId, className: cn("flex h-10 w-full rounded-md border border-border bg-surface-50 px-3 py-2 text-body-md text-ink-default shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-ink-tertiary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brandFocus disabled:cursor-not-allowed disabled:opacity-50", error ? "border-red-500 ring-1 ring-red-500" : "border-border", className), "aria-invalid": error ? "true" : "false", "aria-describedby": error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined, ...props }), error && (_jsx("p", { id: `${inputId}-error`, className: "text-xs text-red-600", role: "alert", children: error })), helperText && !error && (_jsx("p", { id: `${inputId}-helper`, className: "text-xs text-muted-foreground", children: helperText }))] }));
});
Input.displayName = "Input";
export const Card = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("div", { ref: ref, className: cn("rounded-lg border border-border bg-surface-50 shadow-sm", className), ...props, children: children })));
Card.displayName = "Card";
export const CardHeader = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("div", { ref: ref, className: cn("flex flex-col space-y-1.5 p-6", className), ...props, children: children })));
CardHeader.displayName = "CardHeader";
export const CardTitle = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("h3", { ref: ref, className: cn("text-2xl font-semibold leading-none tracking-tight text-ink-default", className), ...props, children: children })));
CardTitle.displayName = "CardTitle";
export const CardDescription = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("p", { ref: ref, className: cn("text-body-sm text-ink-tertiary", className), ...props, children: children })));
CardDescription.displayName = "CardDescription";
export const CardContent = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("div", { ref: ref, className: cn("p-6 pt-0", className), ...props, children: children })));
CardContent.displayName = "CardContent";
export const CardFooter = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("div", { ref: ref, className: cn("flex items-center p-6 pt-0", className), ...props, children: children })));
CardFooter.displayName = "CardFooter";
export const Table = ({ className, columns, rows, ...props }) => (_jsx("div", { className: cn("w-full overflow-auto rounded-md border border-border", className), children: _jsxs("table", { ...props, className: "w-full text-sm", children: [_jsx("thead", { children: _jsx("tr", { children: columns.map((col) => (_jsx("th", { scope: "col", className: "px-4 py-3 text-left text-body-sm font-medium text-ink-secondary bg-surface-100 border-b border-border", children: col }, col))) }) }), _jsx("tbody", { className: "divide-y divide-border", children: rows.map((row, i) => (_jsx("tr", { className: "bg-surface-50 border-b border-border last:border-0", children: _jsx("td", { className: "px-4 py-3", children: row }) }, i))) })] }) }));
export const Dialog = ({ open, onOpenChange, title, description, children }) => (_jsxs(_Fragment, { children: [_jsx("div", { className: cn("fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity", open ? "opacity-100" : "opacity-0 pointer-events-none"), onClick: () => onOpenChange(false), "aria-hidden": "true" }), _jsxs("div", { className: cn("fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-surface-50 p-6 shadow-lg rounded-lg", open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"), role: "dialog", "aria-modal": "true", "aria-labelledby": title ? "dialog-title" : undefined, "aria-describedby": description ? "dialog-description" : undefined, onKeyDown: (e) => e.key === "Escape" && onOpenChange(false), children: [title && _jsx("h2", { id: "dialog-title", className: "text-lg font-semibold text-ink-default", children: title }), description && _jsx("p", { id: "dialog-description", className: "text-body-sm text-ink-tertiary", children: description }), _jsx("div", { className: "mt-4", children: children })] })] }));
export const ToastItem = ({ id, title, description, variant, onDismiss }) => {
    const variants = {
        default: "border-border bg-surface-50 text-ink-default",
        destructive: "border-red-500 bg-red-50 text-red-900",
        success: "border-green-500 bg-green-50 text-green-900",
        warning: "border-amber-500 bg-amber-50 text-amber-900",
    };
    return (_jsxs("div", { className: cn("flex items-start gap-3 rounded-md border px-4 py-3 text-sm shadow-lg", variants[variant], "animate-in slide-in-from-right-2 duration-200"), role: "alert", "aria-live": "polite", children: [_jsx("div", { className: "shrink-0", children: variant === "success" ? (_jsx("svg", { className: "h-5 w-5 text-green-500", fill: "currentColor", viewBox: "0 0 20 20", children: _jsx("path", { fillRule: "evenodd", d: "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z", clipRule: "evenodd" }) })) : variant === "destructive" ? (_jsx("svg", { className: "h-5 w-5 text-red-500", fill: "currentColor", viewBox: "0 0 20 20", children: _jsx("path", { fillRule: "evenodd", d: "M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z", clipRule: "evenodd" }) })) : variant === "warning" ? (_jsx("svg", { className: "h-5 w-5 text-amber-500", fill: "currentColor", viewBox: "0 0 20 20", children: _jsx("path", { fillRule: "evenodd", d: "M8.257 3.099c.765-0.86 3.116-0.86 3.882 0l0.848 0.955a1 1 0 001.48 0l1.48-1.667c0.473-0.532 1.618-0.532 2.092 0l3.977 4.479a1 1 0 001.48 0l0.848-0.955a1 1 0 011.48 0l0.848 0.955a1 1 0 001.48 0l3.977-4.479c0.474-0.532 1.618-0.532 2.092 0l0.848 0.955a1 1 0 001.48 0l0.848-0.955a1 1 0 111.48 0l3.977 4.479a1 1 0 001.48 0l1.48-1.667c0.474-0.532 1.618-0.532 2.092 0l1.48 1.667a1 1 0 001.48 0l3.977-4.479a1 1 0 111.48 0l-8.734 9.827c-0.474 0.532-1.618 0.532-2.092 0l-3.977-4.479a1 1 0 00-1.48 0l-3.977 4.479a1 1 0 001.48 0l1.48 1.667a1 1 0 001.48 0l-0.848 0.955a1 1 0 01-1.48 0l-0.848-0.955a1 1 0 10-1.48 0l-1.48 1.667a1 1 0 01-1.48 0l-8.734-9.827a1 1 0 010-1.48z", clipRule: "evenodd" }) })) : (_jsx("svg", { className: "h-5 w-5 text-muted-foreground", fill: "currentColor", viewBox: "0 0 20 20", children: _jsx("path", { fillRule: "evenodd", d: "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z", clipRule: "evenodd" }) })) }), _jsxs("div", { className: "min-w-0 flex-1", children: [_jsx("h4", { className: "font-semibold text-ink-default", children: title }), description && _jsx("p", { className: "text-body-sm text-ink-secondary line-clamp-2", children: description })] }), _jsx("button", { onClick: onDismiss, className: "ml-2 shrink-0 p-1 opacity-50 hover:opacity-100 rounded hover:bg-surface-100", "aria-label": "Dismiss", children: _jsx("svg", { className: "h-4 w-4", fill: "currentColor", viewBox: "0 0 20 20", children: _jsx("path", { fillRule: "evenodd", d: "M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z", clipRule: "evenodd" }) }) })] }, id));
};
export const ToastContainer = () => {
    const { toasts, dismiss } = useToast();
    return (_jsx("div", { className: "fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none", children: toasts.map((toast) => (_jsx(ToastItem, { ...toast, onDismiss: () => dismiss(toast.id) }, toast.id))) }));
};
// --- Skeleton ---------------------------------------------------------------
export const Skeleton = ({ className }) => (_jsx("div", { className: cn("animate-pulse rounded-md bg-surface-200", className) }));
// --- EmptyState -------------------------------------------------------------
export const EmptyState = ({ title, description, action }) => (_jsxs("div", { className: "flex flex-col items-center justify-center py-12 text-center", children: [_jsx("h3", { className: "text-body-lg font-semibold text-ink-default", children: title }), description && _jsx("p", { className: "text-body-sm text-ink-secondary mt-2", children: description }), action && _jsx("div", { className: "mt-4", children: action })] }));
