// js/pages/dashboard.student.js
(async function () {
  // --- CONFIG: in dev you can set this token; in prod use real auth (cookies / JWT)
  const AUTH_TOKEN = localStorage.getItem('cv_token') || 'token-student-1';

  async function apiFetch(path, opts = {}) {
    const headers = opts.headers || {};
    headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    const res = await fetch(`/api${path}`, { ...opts, headers });
    if (!res.ok) {
      console.error('API error', res.status, await res.text());
      throw new Error(`API ${path} failed: ${res.status}`);
    }
    return res.json();
  }

  // get current user
  let user = null;
  try {
    user = await apiFetch('/me');
  } catch (err) {
    console.warn('Auth required or failed:', err);
    // redirect to login page
    window.location.href = '/login.html';
    return;
  }

  if (!user || user.role !== 'student') {
    console.warn('Permission error: student-only page.');
    window.location.href = '/login.html';
    return;
  }

  document.getElementById('greeting').textContent = `Welcome, ${user.name}!`;

  // fetch student's enrolled courses/resources
  try {
    const resources = await apiFetch('/student/resources');
    const list = document.getElementById('resource-list');
    list.innerHTML = '';
    if (!resources || resources.length === 0) {
      list.innerHTML = '<div class="cv-item muted">No resources found.</div>';
    } else {
      resources.forEach(r => {
        const li = document.createElement('div');
        li.className = 'cv-item';
        li.innerHTML = `<div><strong>${r.title}</strong><div class="muted">${r.source}</div></div>
                        <div><a class="cv-btn-link" href="${r.link || '#'}">Open</a></div>`;
        list.appendChild(li);
      });
    }
  } catch (err) {
    console.error('Failed to load resources', err);
  }

  // Latest uploads
  try {
    const uploads = await apiFetch('/uploads/latest?limit=10');
    const uploadsEl = document.getElementById('latest-uploads');
    uploadsEl.innerHTML = '';
    if (!uploads || uploads.length === 0) {
      uploadsEl.innerHTML = '<div class="cv-item muted">No recent uploads.</div>';
    } else {
      uploads.forEach(u => {
        const li = document.createElement('div');
        li.className = 'cv-item';
        li.innerHTML = `<div><strong>${u.title}</strong><div class="muted">${u.when}</div></div>
                        <div><button class="cv-btn-link">View</button></div>`;
        uploadsEl.appendChild(li);
      });
    }
  } catch (err) {
    console.error('Failed to load uploads', err);
  }

  // Actions (keep navigation for Search & Chat)
  document.getElementById('btn-search-library').addEventListener('click', () => {
    window.location.href = 'student_library.html';
  });
  document.getElementById('btn-open-chat').addEventListener('click', () => {
    window.location.href = 'student_chat.html';
  });

  // NOTE: don't redirect 'Raise Complaint' button if you want the floating button to open modal.
  // Leave this element to open the modal if the static button also exists:
  const staticRaiseBtn = document.getElementById('btn-raise-complaint');
  if (staticRaiseBtn) {
    staticRaiseBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const modal = document.getElementById('complaint-modal');
      if (modal) modal.style.display = 'block';
    });
  }

})();

// Complaint modal & floating button logic — run after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const floatBtn = document.getElementById('complaint-float-btn');
  const complaintModal = document.getElementById('complaint-modal');
  const closeComplaintBtn = document.getElementById('close-complaint-modal');
  const complaintForm = document.getElementById('complaint-form');
  const feedbackEl = document.getElementById('complaint-feedback');

  // If your HTML doesn't include the floating button & modal, nothing happens — but this avoids errors
  if (!floatBtn && !complaintModal) {
    // nothing to do
    return;
  }

  if (floatBtn) {
    floatBtn.addEventListener('click', () => {
      if (complaintModal) complaintModal.style.display = 'block';
    });
  }

  if (closeComplaintBtn) {
    closeComplaintBtn.addEventListener('click', () => {
      if (complaintModal) complaintModal.style.display = 'none';
    });
  }

  // Close when clicking outside content
  window.addEventListener('click', (e) => {
    if (e.target === complaintModal) {
      complaintModal.style.display = 'none';
    }
  });

  // Form submission via Formspree
  if (complaintForm) {
    complaintForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (feedbackEl) feedbackEl.textContent = "Sending...";

      const formData = new FormData(complaintForm);
      const action = complaintForm.action;

      try {
        const response = await fetch(action, {
          method: 'POST',
          body: formData,
          headers: { 'Accept': 'application/json' }
        });

        if (response.ok) {
          if (feedbackEl) feedbackEl.textContent = "Complaint sent successfully!";
          complaintForm.reset();
        } else {
          if (feedbackEl) feedbackEl.textContent = "Oops! Something went wrong.";
        }
      } catch (err) {
        if (feedbackEl) feedbackEl.textContent = "Error sending complaint.";
      }
    });
  }
});
