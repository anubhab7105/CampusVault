// ===========================
// dom.js
// DOM helper functions
// ===========================

export function $(selector) {
  return document.querySelector(selector);
}

export function $all(selector) {
  return document.querySelectorAll(selector);
}

export function createEl(tag, classes = [], attrs = {}) {
  const el = document.createElement(tag);
  classes.forEach((c) => el.classList.add(c));
  Object.keys(attrs).forEach((key) => el.setAttribute(key, attrs[key]));
  return el;
}
