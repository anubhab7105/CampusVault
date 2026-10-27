/** CampusVault design tokens — single source of truth for the design system. */
const spacing = {
  1: "0.25rem",
  2: "0.5rem",
  3: "0.75rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  8: "2rem",
  10: "2.5rem",
  12: "3rem",
  16: "4rem",
  20: "5rem",
};

const borderRadius = {
  sm: "0.375rem",
  md: "0.5rem",
  lg: "0.75rem",
  full: "9999px",
};

const colors = {
  // Light theme defaults; dark theme overrides via [data-theme="dark"].
  surface: {
    "50": "#ffffff",
    "100": "#f8fafc",
    "200": "#f1f5f9",
    DEFAULT: "#ffffff",
    "900": "#0f172a",
  },
  brand: {
    "50": "#eff6ff",
    DEFAULT: "#2563eb",
    "900": "#1d4ed8",
  },
  ink: {
    default: "#0f172a",
    secondary: "#334155",
    tertiary: "#64748b",
  },
  muted: {
    default: "#94a3b8",
    foreground: "#94a3b8",
  },
  border: {
    default: "#e2e8f0",
    brand: "#2563eb",
  },
  brandFocus: "#bfdbfe",
};

const fonts = {
  sans: "var(--font-sans)",
  mono: "var(--font-mono)",
};

module.exports = {
  spacing,
  borderRadius,
  colors,
  fonts,
};
