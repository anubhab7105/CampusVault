// ===========================
// auth.js
// login/logout, session handling
// ===========================
import { ROLES } from "./config.js";

export function login(userId, role, email) {
  sessionStorage.setItem("userId", userId);
  sessionStorage.setItem("role", role);
  sessionStorage.setItem("email", email);
}

export function logout() {
  sessionStorage.clear();
  window.location.href = "login.html";
}

export function getCurrentUser() {
  return {
    userId: sessionStorage.getItem("userId"),
    role: sessionStorage.getItem("role"),
    email: sessionStorage.getItem("email"),
  };
}

export function requireRole(roles = []) {
  const user = getCurrentUser();
  if (!roles.includes(user.role)) {
    alert("Access denied!");
    window.location.href = "login.html";
  }
}
