/** Auth service layer — thin wrapper over the Axios client. */
import { apiClient } from "@services/apiClient";
export const authService = {
    /** Builds the Google OAuth authorize URL for the SPA consent step. */
    googleAuthorize: async (state) => {
        const { data } = await apiClient.get(`/auth/google/authorize?state=${encodeURIComponent(state)}`);
        return data.data;
    },
    /** Exchange consent-screen code for CampusVault tokens. */
    googleCallback: async (code) => {
        const { data } = await apiClient.post("/auth/google", { code });
        return data.data;
    },
    /** Teacher: request OTP (phase 1). */
    requestTeacherOtp: async (email) => {
        const { data } = await apiClient.post("/auth/teachers/otp/request", { email });
        return data.data;
    },
    /** Teacher: verify OTP → tokens (phase 2). */
    verifyTeacherOtp: async (email, code) => {
        const { data } = await apiClient.post("/auth/teachers/otp/verify", { email, code });
        return data.data;
    },
    /** Rotate the refresh token. */
    refresh: async () => {
        const { data } = await apiClient.post("/auth/refresh", {});
        return data.data.tokens;
    },
    /** Revoke the refresh token server-side + local logout. */
    logout: async () => {
        try {
            await apiClient.post("/auth/logout", {});
        }
        catch {
            /* ignore — logout is local regardless of network */
        }
    },
    /** Echo identity + claims from the access token. */
    me: async () => {
        const { data } = await apiClient.get("/auth/me");
        return data.data;
    },
};
