/** @type {import('tailwindcss').Config} */
import sharedTokens from "./tailwind.tokens.cjs";

export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          50: sharedTokens.colors.surface["50"],
          100: sharedTokens.colors.surface["100"],
          200: sharedTokens.colors.surface["200"],
          900: sharedTokens.colors.surface["900"],
          DEFAULT: sharedTokens.colors.surface.DEFAULT,
        },
        brand: {
          50: sharedTokens.colors.brand["50"],
          DEFAULT: sharedTokens.colors.brand.DEFAULT,
          900: sharedTokens.colors.brand["900"],
        },
        ink: sharedTokens.colors.ink,
        muted: sharedTokens.colors.muted,
        border: sharedTokens.colors.border,
        brandFocus: sharedTokens.colors.brandFocus,
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "heading-xl": ["2rem", { lineHeight: "1.2", fontWeight: "700" }],
        "heading-lg": ["1.5rem", { lineHeight: "1.33", fontWeight: "700" }],
        "heading-md": ["1.25rem", { lineHeight: "1.4", fontWeight: "600" }],
        "body-lg": ["1.125rem", { lineHeight: "1.6" }],
        "body-md": ["1rem", { lineHeight: "1.6" }],
        "body-sm": ["0.875rem", { lineHeight: "1.5" }],
        "caption-xs": ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.02em" }],
      },
      spacing: sharedTokens.spacing,
      borderRadius: sharedTokens.borderRadius,
      animation: {
        "fade-in": "fadeIn 200ms ease-in-out",
        "slide-up": "slideUp 300ms ease-out",
        "pulse-fast": "pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
} satisfies import("tailwindcss").Config;
