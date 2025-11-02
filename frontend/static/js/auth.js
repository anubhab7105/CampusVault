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


// auth.js - simple client-side helpers and integration notes
// IMPORTANT: Prefer server-side role checks & redirects. These client helpers are fallbacks.

/*
Backend integration approaches (choose one):

A) Server-side redirect (recommended)
  - After validating credentials, backend returns HTTP 302 -> /admin-dashboard.html or /faculty-dashboard.html or /student-dashboard.html
  - Server may inject user info into the HTML page:
      <script>window.__USER__ = { id: 12, name: 'Anubhab', role: 'admin' };</script>

B) API-based login
  - Frontend sends credentials to backend: POST /api/login
  - Backend responds with JSON { success:true, role:'faculty', user:{...}, redirect:'/faculty-dashboard.html' }
  - Frontend stores token and navigates to redirect

C) Token-based (JWT)
  - Backend returns JWT containing role. Frontend stores token (httpOnly cookie preferred).
  - When rendering pages, backend or frontend decodes role and redirects/blocks accordingly.

Below is an example client-side login flow (if you do frontend redirect):
*/

async function doLogin(credentials) {
  // Example: use fetch to call backend. Replace endpoint accordingly.
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Login failed');
  }

  const payload = await res.json();
  // payload example: { success: true, user: { id, name, role }, redirect: '/admin-dashboard.html' }

  // Store user for in-page use (optional). Backend should still secure pages server-side.
  window.__USER__ = payload.user;

  // Redirect to backend-specified dashboard (recommended)
  if (payload.redirect) {
    window.location.href = payload.redirect;
  } else {
    // Fallback mapping:
    const r = payload.user.role;
    if (r === 'admin') window.location.href = '/admin-dashboard.html';
    else if (r === 'faculty') window.location.href = '/faculty-dashboard.html';
    else window.location.href = '/student-dashboard.html';
  }
}

// logout button handling - attach globally
document.addEventListener('click', (e) => {
  if (e.target && e.target.id === 'logout-btn') {
    // Invalidate server session and redirect to login
    fetch('/api/logout', { method: 'POST' }).finally(() => {
      window.location.href = '/login.html';
    });
  }
});
