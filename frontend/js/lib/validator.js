// ===========================
// validator.js
// Simple form validators
// ===========================

export function isEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

export function isNotEmpty(value) {
  return value && value.trim().length > 0;
}

export function isValidFileType(file, allowedTypes) {
  if (!file) return false;
  const ext = file.name.split('.').pop().toUpperCase();
  return allowedTypes.includes(ext);
}
