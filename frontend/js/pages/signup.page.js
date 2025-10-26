// frontend/js/pages/signup.page.js
// Sign-up page controller with optional faculty verification code
// Extended: if API returns { token, user } we auto-login (store session + redirect)

import { isEmail, isNotEmpty } from "../lib/validator.js";
import { apiFetch } from "../api.js";        // centralized API wrapper
import { showToast } from "../ui.js";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("signup-form");
  const errorEl = document.getElementById("signup-error");
  const submitBtn = document.getElementById("signup-submit");
  const roleSelect = document.getElementById("signup-role");
  const facultyCodeField = document.getElementById("faculty-code-field");
  const facultyCodeInput = document.getElementById("signup-faculty-code");

  // Show/hide faculty code field based on role
  function toggleFacultyField() {
    const role = roleSelect.value;
    if (role === "faculty") {
      facultyCodeField.classList.remove("hidden");
      facultyCodeInput.setAttribute("required", "required");
    } else {
      facultyCodeField.classList.add("hidden");
      facultyCodeInput.removeAttribute("required");
      facultyCodeInput.value = "";
    }
  }

  roleSelect.addEventListener("change", toggleFacultyField);
  // initialize correct visibility
  toggleFacultyField();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.textContent = "";

    const name = document.getElementById("signup-name").value.trim();
    const email = document.getElementById("signup-email").value.trim();
    const password = document.getElementById("signup-password").value;
    const role = roleSelect.value;
    const facultyCode = facultyCodeInput.value.trim();

    // Basic validation
    if (!isNotEmpty(name)) {
      errorEl.textContent = "Please enter your name.";
      return;
    }
    if (!isEmail(email)) {
      errorEl.textContent = "Please enter a valid email address.";
      return;
    }
    if (!isNotEmpty(password) || password.length < 6) {
      errorEl.textContent = "Password must be at least 6 characters.";
      return;
    }

    // If faculty, ensure faculty code provided
    if (role === "faculty") {
      if (!isNotEmpty(facultyCode)) {
        errorEl.textContent = "Faculty verification code is required for faculty registration.";
        return;
      }
      // Basic pattern (alphanumeric, length 4-16). Adjust as needed.
      const codePattern = /^[A-Za-z0-9\-\_]{4,16}$/;
      if (!codePattern.test(facultyCode)) {
        errorEl.textContent = "Faculty code format invalid. Use letters, numbers, - or _ (4-16 chars).";
        return;
      }
    }

    // disable button to avoid duplicate submits
    submitBtn.disabled = true;

    try {
      // Backend expects: { name, email, password, role, faculty_code? }
      const payload = { name, email, password, role };
      if (role === "faculty") payload.faculty_code = facultyCode;

      const res = await apiFetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // handle typical error shape
      if (!res || res.error) {
        const msg = (res && res.error) ? res.error : "Registration failed";
        errorEl.textContent = msg;
        submitBtn.disabled = false;
        return;
      }

      // ----If backend returned token + user, auto-login ----
      // Accept common shapes: { token, user } or { data: { token, user } }
      const token = res.token || (res.data && res.data.token);
      const user = res.user || (res.data && res.data.user);

      if (token && user) {
        // save session (sessionStorage used to match original snippet)
        // NOTE: consider switching to httpOnly cookies for production
        sessionStorage.setItem("auth_token", token);
        // support different user id key names returned by backend
        const uniqueId = user.unique_id || user.uniqueId || user.id || user._id || "";
        sessionStorage.setItem("user_unique_id", uniqueId);
        sessionStorage.setItem("user_name", user.name || "");
        sessionStorage.setItem("user_email", user.email || "");
        sessionStorage.setItem("user_role", user.role || role || "");

        showToast("Account created and logged in!", "success");

        // short delay so toast shows briefly, then redirect based on role
        setTimeout(() => {
          const r = (user.role || role || "").toLowerCase();
          if (r === "admin") window.location.href = "/admin_dashboard.html";
          else if (r === "faculty") window.location.href = "/dashboard.faculty.html";
          else window.location.href = "/dashboard.student.html";
        }, 600);

        return; // done
      }

      // ---- fallback: no token returned (email verification flow or manual login) ----
      showToast("Account created successfully — please login", "success");
      setTimeout(() => (window.location.href = "index.html"), 1200);
    } catch (err) {
      console.error("Signup error", err);
      errorEl.textContent = "Failed to create account. Try again later.";
      submitBtn.disabled = false;
    }
  });
});
