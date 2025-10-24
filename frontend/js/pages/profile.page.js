// js/pages/profile.page.js
// Standalone module: toggles display/edit, loads profile, saves updates.
// Uses window.__USER__ when available or GET /api/profile.
// POSTs updates to /api/profile (adjust API_PROFILE if needed).

const API_PROFILE = '/api/profile'; // change to your backend endpoint if required

// DOM refs
const profileTop = document.getElementById('profile-top');
const editSection = document.getElementById('profile-edit-section');
const editBtn = document.getElementById('profile-edit');
const cancelBtn = document.getElementById('profile-cancel');
const logoutBtn = document.getElementById('profile-logout');
const form = document.getElementById('profile-form');
const statusEl = document.getElementById('profile-status');

const displayFields = {
  name: document.getElementById('profile-display-name'),
  email: document.getElementById('profile-display-email'),
  phone: document.getElementById('profile-display-phone'),
  role: document.getElementById('profile-display-role'),
  college: document.getElementById('profile-display-college'),
  department: document.getElementById('profile-display-department'),
  degree: document.getElementById('profile-display-degree'),
  year: document.getElementById('profile-display-year'),
  registration: document.getElementById('profile-display-reg'),
  github: document.getElementById('profile-display-github'),
  linkedin: document.getElementById('profile-display-linkedin'),
  bio: document.getElementById('profile-display-bio'),
};

const inputs = Array.from(form.querySelectorAll('[data-field]'));

let originalProfile = null;
let saving = false;

function showStatus(msg = '', type = 'info', timeout = 4000) {
  statusEl.textContent = msg;
  statusEl.className = 'cv-small cv-status ' + (type === 'success' ? 'success' : type === 'error' ? 'error' : '');
  if (timeout) {
    clearTimeout(statusEl._timer);
    statusEl._timer = setTimeout(() => {
      statusEl.textContent = '';
      statusEl.className = 'cv-small';
    }, timeout);
  }
}

// populate display and form from object
function populateFromObject(obj = {}) {
  if (!obj) return;
  // display fields
  Object.keys(displayFields).forEach(k => {
    const el = displayFields[k];
    if (!el) return;
    if (k === 'github' || k === 'linkedin') {
      const v = obj[k] || '';
      el.href = v || '#';
      el.textContent = v ? v : (k === 'github' ? '' : '');
    } else {
      el.textContent = obj[k] ?? '';
    }
  });

  // fill form inputs
  inputs.forEach(inp => {
    const key = inp.dataset.field;
    if (!key) return;
    inp.value = (obj[key] ?? '') + '';
  });

  // update top visible name
  if (displayFields.name && obj.name) displayFields.name.textContent = obj.name;
}

// fetch profile from API or window.__USER__
async function fetchProfile() {
  if (window.__USER__ && typeof window.__USER__ === 'object') {
    originalProfile = window.__USER__;
    populateFromObject(originalProfile);
    return originalProfile;
  }
  try {
    const headers = {};
    const token = localStorage.getItem('cv_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(API_PROFILE, { method: 'GET', headers });
    if (!res.ok) {
      console.warn('Could not fetch profile', res.status);
      showStatus('Could not load profile.', 'error');
      return null;
    }
    const data = await res.json();
    originalProfile = data;
    populateFromObject(data);
    return data;
  } catch (err) {
    console.error('fetchProfile err', err);
    showStatus('Could not load profile.', 'error');
    return null;
  }
}

// collect payload
function collectPayload() {
  const payload = {};
  inputs.forEach(inp => {
    payload[inp.dataset.field] = inp.value;
  });
  return payload;
}

// basic validation
function isValidEmail(email) {
  return typeof email === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
function validate(payload) {
  const errors = {};
  if (!payload.name || payload.name.trim().length < 2) errors.name = 'Name required (2+ chars).';
  if (!isValidEmail(payload.email)) errors.email = 'Valid email required.';
  if (payload.password && payload.password.length > 0 && payload.password.length < 8) errors.password = 'Password must be at least 8 chars.';
  return errors;
}

// show inline errors
function showInlineErrors(errors) {
  // remove previous
  form.querySelectorAll('.cv-error').forEach(n => n.remove());
  Object.entries(errors).forEach(([k, msg]) => {
    const inp = form.querySelector(`[data-field="${k}"]`);
    if (inp) {
      const d = document.createElement('div');
      d.className = 'cv-error';
      d.textContent = msg;
      inp.parentElement.appendChild(d);
    }
  });
}

// submit handler
async function submitProfile(ev) {
  ev && ev.preventDefault();
  if (saving) return;

  const payload = collectPayload();
  const errors = validate(payload);
  if (Object.keys(errors).length) {
    showInlineErrors(errors);
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
      const txt = await res.text().catch(() => '');
      throw new Error(`Server ${res.status} ${txt}`);
    }

    const body = await res.json().catch(() => null);
    // prefer server-returned user, else merge with payload
    originalProfile = (body && body.user) ? body.user : { ...(originalProfile || {}), ...payload };

    populateFromObject(originalProfile);
    showStatus('Profile saved.', 'success', 2500);

    // hide form, show display
    toggleEdit(false);

    // clear password input
    const pwd = form.querySelector('[data-field="password"]');
    if (pwd) pwd.value = '';
  } catch (err) {
    console.error('save err', err);
    showStatus('Could not save profile.', 'error', 5000);
  } finally {
    setSaving(false);
  }
}

function setSaving(v) {
  saving = !!v;
  const saveBtn = document.getElementById('profile-save');
  if (saveBtn) {
    saveBtn.disabled = !!v;
    saveBtn.textContent = v ? 'Saving...' : 'Save';
  }
}

// toggle edit: true => show form, false => show read-only
function toggleEdit(show) {
  if (show) {
    profileTop.classList.add('hidden');
    editSection.classList.remove('hidden');
    editSection.setAttribute('aria-hidden', 'false');
    // focus first field
    const first = editSection.querySelector('[data-field]');
    if (first) first.focus();
  } else {
    editSection.classList.add('hidden');
    profileTop.classList.remove('hidden');
    editSection.setAttribute('aria-hidden', 'true');
  }
}

// cancel
function cancelEdit() {
  populateFromObject(originalProfile);
  toggleEdit(false);
  showStatus('Changes canceled.', 'info', 1600);
}

// logout
function handleLogout() {
  localStorage.removeItem('cv_token');
  window.location.href = '/login.html';
}

// attach events
function addListeners() {
  editBtn && editBtn.addEventListener('click', () => toggleEdit(true));
  cancelBtn && cancelBtn.addEventListener('click', cancelEdit);
  logoutBtn && logoutBtn.addEventListener('click', handleLogout);

  form && form.addEventListener('submit', submitProfile);

  // remove inline error when typing
  inputs.forEach(inp => {
    inp.addEventListener('input', () => {
      const e = inp.parentElement.querySelector('.cv-error');
      if (e) e.remove();
    });
  });
}

// init
(async function init() {
  addListeners();
  await fetchProfile();
})();
