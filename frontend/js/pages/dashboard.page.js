// ===========================
// dashboard.page.js
// Handles dashboard widgets
// ===========================
import { state, setCurrentUser } from "../state.js";
import { getCurrentUser } from "../auth.js";

document.addEventListener("DOMContentLoaded", () => {
  const currentUser = getCurrentUser();
  setCurrentUser(currentUser);

  const widgetContainer = document.getElementById("dashboard-widgets");
  if (!widgetContainer) return;

  const widgets = [
    { title: "Total Books", value: 120 },
    { title: "Your Uploads", value: currentUser.role === "faculty" ? 12 : 0 },
    { title: "Active Students", value: 320 },
    { title: "Notices", value: 5 },
  ];

  widgets.forEach((w) => {
    const card = document.createElement("div");
    card.className = "cv-dashboard-widget";
    card.innerHTML = `<h3>${w.value}</h3><p>${w.title}</p>`;
    widgetContainer.appendChild(card);
  });
});
