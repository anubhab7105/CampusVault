// ===========================
// api.js
// centralized API wrapper
// ===========================
import { API_BASE } from "./config.js";

export async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";
  options.headers = headers;

  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("API Error:", err);
    throw err;
  }
}
