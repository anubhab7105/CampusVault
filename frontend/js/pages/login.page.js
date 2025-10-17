// ===========================
// login.page.js
// Handles login page
// ===========================
import { isEmail, isNotEmpty } from "../lib/validator.js";
import { login } from "../auth.js";
import { ROLES } from "../config.js";
import { showToast } from "../ui.js";

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");

  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();
    const role = document.getElementById("role").value;

    if (!isNotEmpty(email) || !isNotEmpty(password)) {
      showToast("Please fill all fields", "error");
      return;
    }

    if (!isEmail(email)) {
      showToast("Invalid email", "error");
      return;
    }

    // Simulate ID generation
    let userId = "";
    if (role === ROLES.STUDENT) userId = "S" + Math.floor(Math.random() * 900000 + 100000);
    else if (role === ROLES.FACULTY) userId = "F" + Math.floor(Math.random() * 900000 + 100000);
    else userId = "A" + Math.floor(Math.random() * 900 + 100);

    login(userId, role, email);
    showToast(`Logged in as ${role} (${userId})`);
    window.location.href = "dashboard.html";
  });
});
