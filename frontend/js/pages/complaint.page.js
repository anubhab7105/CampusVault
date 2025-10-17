// ===========================
// complaint.page.js
// Handles complaint submission
// ===========================
import { getCurrentUser } from "../auth.js";
import { showToast } from "../ui.js";

document.addEventListener("DOMContentLoaded", () => {
  const complaintForm = document.getElementById("complaint-form");
  const user = getCurrentUser();

  complaintForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = document.getElementById("complaint-msg").value.trim();

    if (!msg) {
      showToast("Please write a complaint", "error");
      return;
    }

    // Here we would call backend API
    console.log("Complaint submitted by", user.userId, msg);
    showToast("Complaint sent successfully");
    complaintForm.reset();
  });
});
