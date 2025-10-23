// js/pages/profile.page.js
// ES module to power the expanded profile page
//
// Features:
// - Populate inputs and summary from window.__USER__ or GET /api/profile
// - Map inputs using data-field attributes
// - Avatar preview and optional upload callback (client-side preview only)
// - Save (POST /api/profile) with Authorization token support (localStorage 'cv_token')
// - Validation, inline errors, cancel/reset, edit toggle, download JSON, logout
// - Role-specific UI: shows faculty-code input when role === 'faculty' (if present)
//
// NOTE:
// - Change API_PROFILE constant if your backend uses a different endpoint/method.

const API_PROFILE = '/api/profile'; // update if needed

// DOM references (inputs are selected by data-field)
const form = document.getElementById('profile-form');
const btnSave = document.getElementById('profile-save');
const btnCancel = document.getElementById('profile-cancel');
const statusEl = document.getElementById('profile-status');
const avatarEl = document.getElementById('profile-avatar');
const avatarInput = document.getElementById('profile-avatar-input');
const initialsEl = document.getElementById('profile-initials');
const summary = {
  name: document.getElementById('summary-name'),
  email: document.getElementById('summary-email'),
  phone: document.getElementById('summary-phone'),
  role: document.getElementById('summary-role'),
  college: document.getElementById('summary-college'),
  department: document.getElementById('summary-department'),
  degree: document.getElementById('summary-degree'),
  year: document.getElementById('summary-year'),
  registration: document.getElementById('summary-registration'),
  github: document.getElementById('summary-github'),
  linkedin: document.getElementById('summary-linkedin'),
  bio: document.getElementById('summary-bio'),
};
const downloadBtn = document.getElementById('profile-download-json');
const editBtn = document.getElementById('profile-edit');
const logoutBtn = document.getElementById('profile-logout');
const debugPre = document.getElementById('profile-json');
const debugSection = document.getElementById('profile-debug');

// Helper: find all inputs with data-field
const inputs = Array.from(form.querySelectorAll('[data-field]'));

// Local state
let originalProfile = null; // raw object from server or window.__USER__
let currentAvatarFile = null; // File object selected for preview (not auto-uploaded)
let saving = false;

// UI helpers
function showStatus(message, type = 'info', timeout = 4000) {
  statusEl.textContent = message;
  statusEl.className = 'cv-small cv-status ' + (type === 'success' ? 'success' : type === 'error' ? 'error' : '');
  if (timeout) {
    clearTimeout(statusEl._hideTimeout);
    statusEl._hideTimeout = setTimeout(() => {
      statusEl.textContent = '';
      statusEl.className = 'cv-small';
    }, timeout);
  }
}
function setSaving(v) {
  saving = !!v;
  if (saving) {
    btnSave.disabled = true;
    btnSave.textContent = 'Saving...';
  } else {
    btnSave.disabled = false;
    btnSave.textContent = 'Save';
  }
}

// Validation
function isValidEmail(email) {
  return typeof email === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
function validatePayload(payload) {
  const errors = {};
  if (!payload.name || payload.name.trim().length < 2) errors.name = 'Name required (2+ chars).';
  if (!isValidEmail(payload.email)) errors.email = 'Valid email required.';
  if (payload.password && payload.password.length > 0 && payload.password.length < 8) errors.password = 'Password must be at least 8 characters.';
  // optional: phone format check (basic)
  if (payload.phone && payload.phone.trim().length > 0 && !/^\+?[\d\s\-().]{6,20}$/.test(payload.phone)) {
    errors.phone = 'Enter a valid phone number.';
  }
  return errors;
}

// Map server/user object to form fields
function populateFormFromObject(obj = {}) {
  if (!obj) return;
  inputs.forEach(input => {
    const key = input.dataset.field;
    if (!key) return;
    // prefer exact property, fallback to nested keys (like profile.github) not implemented here
    const val = obj[key] ?? '';
    if (input.type === 'checkbox') {
      input.checked = !!val;
    } else if (input.tagName.toLowerCase() === 'select') {
      input.value = val || input.value || '';
    } else {
      input.value = val === null ? '' : String(val);
    }
  });

  // set avatar or initials
  if (obj.avatarUrl) {
    setAvatarFromUrl(obj.avatarUrl);
  } else {
    setInitials(obj.name || obj.fullName || obj.email);
  }

  // populate summary
  for (const k in summary) {
    const el = summary[k];
    if (!el) continue;
    const v = obj[k] ?? '';
    if (k === 'github' || k === 'linkedin') {
      // show as link when present
      if (v) el.innerHTML = `<a href="${escapeHtml(String(v))}" target="_blank" rel="noopener noreferrer">${escapeHtml(String(v))}</a>`;
      else el.textContent = '';
    } else {
      el.textContent = v ?? '';
    }
  }

  // show debug JSON if present
  if (debugPre) {
    debugPre.textContent = JSON.stringify(obj, null, 2);
  }
}

// Populate from window.__USER__ or API
async function fetchProfile() {
  if (window.__USER__ && typeof window.__USER__ === 'object') {
    originalProfile = window.__USER__;
    populateFormFromObject(originalProfile);
    return originalProfile;
  }

  try {
    const headers = {};
    const token = localStorage.getItem('cv_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(API_PROFILE, { method: 'GET', headers });
    if (!res.ok) {
      console.warn('Profile fetch failed', res.status);
      showStatus('Could not load profile.', 'error');
      return null;
    }
    const data = await res.json();
    originalProfile = data;
    populateFormFromObject(data);
    return data;
  } catch (err) {
    console.error('Fetch profile error', err);
    showStatus('Could not load profile.', 'error');
    return null;
  }
}

// Helpers: avatar
function setAvatarFromUrl(url) {
  // clear initials
  initialsEl && (initialsEl.textContent = '');
  // if avatarEl already has an <img>, replace src
  let img = avatarEl.querySelector('img');
  if (!img) {
    img = document.createElement('img');
    avatarEl.innerHTML = '';
    avatarEl.appendChild(img);
  }
  img.src = url;
}
function setInitials(nameOrEmail) {
  const initials = (nameOrEmail || 'U').toString().trim().split(/\s+/).slice(0,2).map(s => s[0]?.toUpperCase() || '').join('');
  if (avatarEl.querySelector('img')) avatarEl.querySelector('img').remove();
  if (initialsEl) initialsEl.textContent = initials || 'U';
}
function handleAvatarFile(file) {
  if (!file) return;
  currentAvatarFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    // show preview
    avatarEl.innerHTML = '';
    const img = document.createElement('img');
    img.src = e.target.result;
    img.alt = 'Avatar preview';
    avatarEl.appendChild(img);
  };
  reader.readAsDataURL(file);
}

// Escape HTML for safe link rendering in summary
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
  });
}

// Collect payload from inputs
function collectPayload() {
  const payload = {};
  inputs.forEach(input => {
    const key = input.dataset.field;
    if (!key) return;
    if (input.type === 'checkbox') payload[key] = !!input.checked;
    else payload[key] = input.value;
  });
  // include avatar as data URL if selected (optional; many backends expect a separate upload endpoint)
  if (currentAvatarFile) {
    // we will not synchronously convert to dataURL here; some apps prefer a separate upload
    // include a flag to indicate client has a new avatar
    payload._avatarUpdated = true;
  }
  return payload;
}

// Submit profile to server
async function submitProfile(ev) {
  if (ev && ev.preventDefault) ev.preventDefault();
  if (saving) return;

  // collect and validate
  const payload = collectPayload();
  const errors = validatePayload(payload);

  // clear old inline errors
  form.querySelectorAll('.cv-error').forEach(n => n.remove());

  if (Object.keys(errors).length > 0) {
    // show inline errors
    for (const k in errors) {
      const input = form.querySelector(`[data-field="${k}"]`);
      if (input) {
        const err = document.createElement('div');
        err.className = 'cv-error';
        err.textContent = errors[k];
        input.parentElement.appendChild(err);
      }
    }
    showStatus('Please fix the highlighted fields.', 'error', 4000);
    return;
  }

  // proceed to submit
  setSaving(true);
  showStatus('Saving...', 'info', 0);

  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('cv_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // If backend expects multipart/form-data for avatar, you'd use FormData instead.
    // Here we POST JSON to API_PROFILE. Adjust if your API differs.
    const res = await fetch(API_PROFILE, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const bodyText = await res.text().catch(() => '');
      throw new Error(`Server error ${res.status}: ${bodyText}`);
    }

    const resp = await res.json().catch(() => ({}));
    setSaving(false);
    showStatus('Profile saved successfully.', 'success', 3500);

    // update originalProfile and UI
    originalProfile = resp.user ?? payload;
    // if server returned updated resource, use it; else merge
    if (!resp.user) {
      originalProfile = { ...(originalProfile || {}), ...payload };
    }
    // If avatar was selected but backend didn't accept, we'll keep preview client-side.
    populateFormFromObject(originalProfile);

  } catch (err) {
    console.error('Save profile failed', err);
    setSaving(false);
    showStatus('Could not save profile — try again.', 'error', 6000);
  }
}

// Cancel / revert to originalProfile
function cancelEdit() {
  if (!originalProfile) {
    showStatus('Nothing to revert to.', 'error', 2000);
    return;
  }
  populateFormFromObject(originalProfile);
  currentAvatarFile = null;
  showStatus('Changes cancelled.', 'info', 2000);
}

// Download JSON of current form
function downloadCurrentJson() {
  const payload = collectPayload();
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `campusvault-profile-${(payload.name || 'user').replace(/\s+/g,'_').toLowerCase()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Toggle read/edit mode (simple switch that focuses first input)
function enterEditMode() {
  const firstInput = inputs[0];
  if (firstInput) firstInput.focus();
}

// Logout handler: clear token and redirect to login
function handleLogout() {
  localStorage.removeItem('cv_token');
  // redirect to login — change path if you use a different route
  window.location.href = '/login.html';
}

// Role-specific UI: show faculty code input if present in DOM and role is faculty
function handleRoleSpecifics() {
  const roleSelect = form.querySelector('[data-field="role"]');
  if (!roleSelect) return;
  const facultyCodeInput = form.querySelector('[data-field="facultyCode"]');
  if (facultyCodeInput) {
    if (roleSelect.value === 'faculty') facultyCodeInput.parentElement.style.display = 'block';
    else facultyCodeInput.parentElement.style.display = 'none';
  }
}

// Wire up events
function addEventListeners() {
  form.addEventListener('submit', submitProfile);
  btnCancel.addEventListener('click', cancelEdit);
  downloadBtn.addEventListener('click', downloadCurrentJson);
  editBtn && editBtn.addEventListener('click', enterEditMode);
  logoutBtn && logoutBtn.addEventListener('click', handleLogout);

  // avatar input
  if (avatarInput) {
    avatarInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) handleAvatarFile(f);
    });
  }
  // "Change photo" label click is handled by HTML label -> input association.

  // Inputs: remove inline errors when user types
  inputs.forEach(inp => {
    inp.addEventListener('input', () => {
      const err = inp.parentElement.querySelector('.cv-error');
      if (err) err.remove();
      // if role changed, apply role UI
      if (inp.dataset.field === 'role') handleRoleSpecifics();
    });
  });
}

// Initialize page
async function init() {
  // show edit controls if missing
  addEventListeners();
  await fetchProfile();
  handleRoleSpecifics();

  // expose debug toggle via double-click on summary (dev only)
  if (summary.name && debugSection) {
    summary.name.addEventListener('dblclick', () => {
      debugSection.style.display = debugSection.style.display === 'none' ? 'block' : 'none';
    });
  }
}

// Run init
init().catch(err => {
  console.error('Profile page init error', err);
  showStatus('Initialization error', 'error');
});

// Optional exports for testing
export {
  fetchProfile,
  populateFormFromObject,
  submitProfile,
  cancelEdit,
  downloadCurrentJson
};
