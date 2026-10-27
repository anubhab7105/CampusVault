/** App-wide constants (shared keys, storage keys, limits). */
export const STORAGE_KEYS = {
    TOKENS: "cv_tokens",
    THEME: "cv_theme",
    SIDEBAR_COLLAPSED: "cv_sidebar_collapsed",
};
export const AUTH = {
    TOKEN_ACCESS_NAME: "access_token",
    TOKEN_REFRESH_NAME: "refresh_token",
    OAUTH_STATE_NAME: "cv_oauth_state",
    CODE_VERIFIER_NAME: "cv_code_verifier",
    GOOGLE_CLIENT_ID: import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "",
    REDIRECT_URI: import.meta.env.VITE_GOOGLE_OAUTH_REDIRECT_URI ?? "http://localhost:5173/auth/google/callback",
};
export const UPLOAD = {
    MAX_SIZE_BYTES: 25 * 1024 * 1024,
    ALLOWED_EXTENSIONS: [
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
        "png", "jpg", "jpeg", "webp", "txt", "csv", "md", "zip",
    ],
};
export const DEBOUNCE_MS = {
    SEARCH: 300,
};
