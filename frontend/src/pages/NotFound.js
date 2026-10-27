import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** NotFound placeholder — 404 recovery. */
import { useNavigate } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@components/ui/index";
export default function NotFound() {
    const navigate = useNavigate();
    return (_jsx("div", { className: "flex min-h-screen flex-col items-center justify-center bg-surface-100 px-4 py-12", children: _jsxs(Card, { className: "max-w-md w-full text-center", children: [_jsxs(CardHeader, { children: [_jsx(CardTitle, { className: "text-6xl font-bold text-ink-default", children: "404" }), _jsx("p", { className: "text-body-sm text-ink-secondary", children: "Page not found." })] }), _jsx(CardContent, { children: _jsx(Button, { onClick: () => navigate("/"), className: "w-full", children: "Return to dashboard" }) })] }) }));
}
