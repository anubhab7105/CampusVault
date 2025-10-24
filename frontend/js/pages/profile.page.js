// js/pages/profile.page.js
// ES module for the simplified profile page
// - No avatar handling
// - No download JSON, no summary/read-only DB fields
// - Loads profile (window.__USER__ preferred, otherwise GET /api/profile)
// - Validates, submits to POST /api/profile (adjust method/URL if needed)
// - Cancel reverts to last-known server state

const API_PROFILE = '/api/profile'; // change if your backend uses a different route

// DOM refs
const form = document.getElementById('profile-form');
const btnSave = document.getElementById('profile-save');
const btnCancel = document.getElementById('profile-cancel');
const statusEl = document.getElementById('profile-status');
const editBtn = document.getElementById('profile-edit');
const logoutBtn = document.getElementById('profile-logout');

// inputs (by data-field)
const inputs = Array.from(form.querySelectorAll('[data-field]'));

// state
let originalProfile = null;
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
  if (payload.phone && payload.phone.trim().length > 0 && !/^\+?[\d\s\-().]{6,20}$/.test(payload.phone)) {
    errors.phone = 'Enter a valid phone number.';
  }
  return errors;
}

// Populate form inputs from object
function populateFormFromObject(obj = {}) {
  if (!obj) return;
  inputs.forEach(input => {
    const key = input.dataset.field;
    if (!key) return;
    const val = obj[key] ?? '';
    if (input.type === 'checkbox') input.checked = !!val;
    else input.value = val === null ? '' : String(val);
  });

  // update top display if present
  const displayName = document.getElementById('profile-display-name');
  if (displayName) displayName.textContent = obj.name || obj.fullName || '';

  const roleText = document.getElementById('profile-role-text');
  if (roleText) {
    const r = obj.role || 'student';
    roleText.innerHTML = `Role: <strong>${r}</strong>`;
  }

  const bioEl = document.getElementById('profile-bio');
  if (bioEl) bioEl.textContent = obj.bio || '';
}

// Fetch profile (prefers window.__USER__)
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

// Collect payload from inputs
function collectPayload() {
  const payload = {};
  inputs.forEach(input => {
    const key = input.dataset.field;
    if (!key) return;
    if (input.type === 'checkbox') payload[key] = !!input.checked;
    else payload[key] = input.value;
  });
  return payload;
}

// Submit handler
async function submitProfile(ev) {
  if (ev && ev.preventDefault) ev.preventDefault();
  if (saving) return;

  const payload = collectPayload();
  const errors = validatePayload(payload);

  // clear previous inline errors
  form.querySelectorAll('.cv-error').forEach(n => n.remove());

  if (Object.keys(errors).length > 0) {
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

  setSaving(true);
  showStatus('Saving...', 'info', 0);

  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('cv_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(API_PROFILE, {
      method: 'POST', // change to PUT if your API requires it
      headers,
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const bodyText = await res.text().catch(() => '');
      throw new Error(`Server error ${res.status}: ${bodyText}`);
    }

    const resp = await res.json().catch(() => ({}));
    setSaving(false);
    showStatus('Profile saved successfully.', 'success', 3500);

    // update originalProfile and form
    originalProfile = resp.user ?? { ...(originalProfile || {}), ...payload };
    populateFormFromObject(originalProfile);

    // clear password field for safety
    const pwd = form.querySelector('[data-field="password"]');
    if (pwd) pwd.value = '';

  } catch (err) {
    console.error('Save error', err);
    setSaving(false);
    showStatus('Could not save profile — try again.', 'error', 6000);
  }
}

// Cancel / revert
function cancelEdit() {
  if (!originalProfile) {
    showStatus('Nothing to revert to.', 'error', 2000);
    return;
  }
  populateFormFromObject(originalProfile);
  showStatus('Changes cancelled.', 'info', 2000);
}

// Edit button: focus first input
function enterEditMode() {
  const firstInput = inputs[0];
  if (firstInput) firstInput.focus();
}

// Logout handler
function handleLogout() {
  localStorage.removeItem('cv_token');
  window.location.href = '/login.html';
}

// Role-specific UI (if you add facultyCode input it will be toggled)
function handleRoleSpecifics() {
  const roleSelect = form.querySelector('[data-field="role"]');
  if (!roleSelect) return;
  const facultyCodeInput = form.querySelector('[data-field="facultyCode"]');
  if (facultyCodeInput) {
    facultyCodeInput.parentElement.style.display = roleSelect.value === 'faculty' ? '' : 'none';
  }
}

// Events
function addEventListeners() {
  form.addEventListener('submit', submitProfile);
  btnCancel.addEventListener('click', cancelEdit);
  editBtn && editBtn.addEventListener('click', enterEditMode);
  logoutBtn && logoutBtn.addEventListener('click', handleLogout);

  inputs.forEach(inp => {
    inp.addEventListener('input', () => {
      const err = inp.parentElement.querySelector('.cv-error');
      if (err) err.remove();
      if (inp.dataset.field === 'role') handleRoleSpecifics();
    });
  });
}

// Init
async function init() {
  addEventListeners();
  await fetchProfile();
  handleRoleSpecifics();
}

init().catch(err => {
  console.error('Profile init error', err);
  showStatus('Initialization error', 'error');
});

// Exports for testing
export { fetchProfile, populateFormFromObject, submitProfile, cancelEdit };
