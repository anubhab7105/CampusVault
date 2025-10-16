/* Minimal API helper. Import config from config.json or replace at build time. */
const API = {
  baseUrl: (window.__API_BASE__ || '/api') // can be replaced in deployment
};

async function getJson(path) {
  const res = await fetch(API.baseUrl + path, { credentials: 'include' });
  return res.json();
}

async function postJson(path, data) {
  const res = await fetch(API.baseUrl + path, { method: 'POST', body: JSON.stringify(data) });
  return res.json();
}

async function putJson(path, data) {
  const res = await fetch(API.baseUrl + path, { method: 'PUT', body: JSON.stringify(data) });
  return res.json();
}

async function deleteJson(path) {
  const res = await fetch(API.baseUrl + path, { method: 'DELETE' });
  return res.json();
}