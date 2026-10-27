/** Entry point — React 18 root render. */

import { createRoot } from "react-dom/client";
import AppContent from "@App";

const root = createRoot(document.getElementById("root") as HTMLElement);
root.render(
  <React.StrictMode>
    <AppContent />
  </React.StrictMode>,
);
