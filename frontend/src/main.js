import { jsx as _jsx } from "react/jsx-runtime";
/** Entry point — React 18 root render. */
import { createRoot } from "react-dom/client";
import AppContent from "./App";
import React from "react";
const root = createRoot(document.getElementById("root"));
root.render(_jsx(React.StrictMode, { children: _jsx(AppContent, {}) }));
