import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
/** Login page — unified entry for Student (Google OAuth) + Teacher (OTP). */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { authService } from "@services/authService";
import { useAuthStore } from "@stores/useAuthStore";
import { Button, Input, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, } from "@components/ui/index";
import { cn } from "@utils/cn";
import { PATHS } from "@constants/routes";
const teacherSchema = z.object({
    email: z.string().email("Enter a valid college email address."),
    code: z.string().min(6, "Code must be 6 digits").max(6),
});
export default function Login() {
    const navigate = useNavigate();
    const { setTokens, setUser } = useAuthStore();
    const [phase, setPhase] = useState("provider");
    const [pending, setPending] = useState(false);
    const form = useForm({
        resolver: zodResolver(teacherSchema),
        defaultValues: { email: "", code: "" },
    });
    const handleGoogle = async (e) => {
        e.preventDefault();
        setPending(true);
        try {
            // Provider-consent URL — in production the SPA opens this in a browser context.
            const data = await authService.googleAuthorize("init");
            // Scaffold note: Google consent-screen flow completes at /auth/google?code=…
            navigate(`${PATHS.LOGIN}?google_authorize_url=${encodeURIComponent(data.authorize_url)}`);
        }
        catch (err) {
            toast.error("Sign-in failed", err?.campusvaultError?.message ?? String(err ?? ""));
        }
        finally {
            setPending(false);
        }
    };
    const handleOtpRequest = async (values) => {
        setPending(true);
        try {
            const { expires_in_seconds } = await authService.requestTeacherOtp(values.email);
            setPhase("verifying");
            toast("Code sent", `Expires in ${expires_in_seconds} seconds.`);
        }
        catch (err) {
            toast.error("Could not send code", err?.campusvaultError?.message ?? String(err ?? ""));
        }
        finally {
            setPending(false);
        }
    };
    const handleOtpVerify = async (values) => {
        setPending(true);
        try {
            const result = await authService.verifyTeacherOtp(values.email, values.code);
            setTokens(result.tokens.access_token, result.tokens.refresh_token);
            setUser(result.user);
            navigate(PATHS.DASHBOARD, { replace: true });
        }
        catch (err) {
            form.setError("code", { message: err?.campusvaultError?.message ?? "Invalid or expired code." });
        }
        finally {
            setPending(false);
        }
    };
    return (_jsx("div", { className: "flex min-h-screen flex-col items-center justify-center bg-surface-100 px-4 py-12 sm:px-6 lg:px-8", children: _jsxs("div", { className: "max-w-md w-full space-y-8", children: [_jsxs("div", { children: [_jsx("h2", { className: "text-heading-lg font-semibold tracking-tight text-ink-default", children: "CampusVault" }), _jsx("p", { className: "mt-2 text-body-md text-ink-secondary", children: "Sign in to your academic library." })] }), _jsxs(Card, { className: cn("w-full", phase === "provider" ? "pt-6" : "pt-0"), children: [_jsxs(CardHeader, { children: [_jsx(CardTitle, { children: phase === "provider" ? "Sign in" : "Teacher verification" }), _jsx(CardDescription, { children: phase === "provider"
                                        ? "Students sign in with Google. Teachers use email OTP."
                                        : "Enter the code sent to your college email." })] }), _jsxs(CardContent, { children: [phase === "provider" ? (_jsxs(_Fragment, { children: [_jsx(Button, { onClick: handleGoogle, disabled: pending, className: "w-full justify-center", variant: "default", isLoading: pending, children: "Continue with Google" }), _jsx("p", { className: "mt-4 text-caption-xs text-ink-tertiary", children: "College Google Workspace account required." })] })) : (_jsxs("form", { onSubmit: form.handleSubmit(handleOtpRequest), className: "space-y-4", children: [_jsx(Input, { label: "College email", type: "email", placeholder: "name@college.edu", ...form.register("email") }), _jsx(Button, { type: "submit", disabled: pending, isLoading: pending, className: "w-full", children: "Send verification code" })] })), phase === "verifying" && (_jsxs("form", { onSubmit: form.handleSubmit(handleOtpVerify), className: "mt-6 space-y-4", children: [_jsx(Input, { label: "6-digit code", ...form.register("code") }), _jsx(Button, { type: "submit", disabled: pending, isLoading: pending, className: "w-full", children: "Verify & sign in" })] }))] }), _jsx(CardFooter, { className: "flex flex-col gap-3 pt-6 border-t", children: phase === "provider" ? (_jsx(Button, { type: "button", onClick: () => setPhase("teacher"), variant: "ghost", className: "w-full text-left text-ink-secondary", children: "Teacher sign-in with email OTP" })) : (_jsx(Button, { type: "button", onClick: () => setPhase("provider"), variant: "ghost", className: "w-full", children: "Back to provider selection" })) })] })] }) }));
}
