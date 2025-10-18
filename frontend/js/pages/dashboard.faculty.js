(function () {
  const SELECTORS = {
    greeting: '#greeting',
    courseList: '#course-list',
    uploadsList: '#latest-uploads',
    btnUpload: '#btn-upload-material',
    btnPostNotice: '#btn-post-notice',
    btnContactAdmin: '#btn-contact-admin',
    logoutBtn: '#logout-btn',
    hamburger: '#cv-hamburger',
    topnav: '#cv-topnav',
  };

  const user = window.__USER__ || null;
  if (!user || user.role !== 'faculty') {
    console.warn('Permission error: faculty-only page.');
    window.location.href = '/login.html';
    return;
  }

  // small utility
  const $ = (s) => document.querySelector(s);
  const el = (s) => document.querySelector(s);
  const formatRelative = (d) => {
    try {
      const date = new Date(d);
      const diff = Date.now() - date.getTime();
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      if (isNaN(days)) return d;
      if (days === 0) return 'today';
      if (days === 1) return '1 day ago';
      if (days < 7) return `${days} days ago`;
      return date.toLocaleDateString();
    } catch { return d; }
  };

  // show greeting
  const greetingEl = el(SELECTORS.greeting);
  if (greetingEl) {
    greetingEl.textContent = `Hello, ${user.name}. Here are your courses and recent uploads.`;
  }

  // Attempt real fetch functions if API endpoints exist.
  // You can set a global API_BASE (e.g. window.__API_BASE__ = '/api') if you want the page to call real endpoints.
  const API_BASE = window.__API_BASE__ || null;

  async function fetchCourses() {
    if (!API_BASE) return null;
    try {
      const res = await fetch(`${API_BASE}/faculty/${encodeURIComponent(user.id || 'me')}/courses`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to fetch courses');
      return await res.json();
    } catch (err) {
      console.warn('courses fetch failed, falling back to mock', err);
      return null;
    }
  }

  async function fetchUploads() {
    if (!API_BASE) return null;
    try {
      const res = await fetch(`${API_BASE}/faculty/${encodeURIComponent(user.id || 'me')}/uploads?limit=10`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to fetch uploads');
      return await res.json();
    } catch (err) {
      console.warn('uploads fetch failed, falling back to mock', err);
      return null;
    }
  }

  // --- Render helpers ---
  function clearChildren(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function renderCourses(courses) {
    const container = el(SELECTORS.courseList);
    if (!container) return;
    clearChildren(container);

    if (!Array.isArray(courses) || courses.length === 0) {
      container.innerHTML = `<div class="cv-empty">No courses yet. Use Upload to add materials.</div>`;
      return;
    }

    const grid = document.createElement('div');
    grid.className = 'cv-course-grid';

    courses.forEach(c => {
      const card = document.createElement('article');
      card.className = 'cv-course';
      card.dataset.course = c.code ?? c.id ?? '';

      const code = c.code ?? c.id ?? '';
      const title = c.title ?? c.name ?? 'Untitled course';
      const semester = c.semester ?? c.term ?? '';
      const enrolled = c.enrolled ?? c.students ?? null;

      card.innerHTML = `
        <div class="cv-course-head">
          <div class="cv-course-avatar" aria-hidden>${(code.slice(0,2) || 'C')}</div>
          <div class="cv-course-info">
            <h4 class="cv-course-title">${title}</h4>
            <div class="cv-course-meta">
              <span class="cv-pill">${code}</span>
              ${semester ? `<span class="cv-muted">• ${semester}</span>` : ''}
              ${enrolled ? `<span class="cv-muted">• ${enrolled} students</span>` : ''}
            </div>
          </div>
        </div>
        <div class="cv-course-actions">
          <button class="cv-btn cv-btn-ghost" data-action="materials" data-course="${encodeURIComponent(code)}">Materials</button>
          <button class="cv-btn cv-btn-ghost" data-action="chat" data-course="${encodeURIComponent(code)}">Chat</button>
        </div>
      `;

      grid.appendChild(card);
    });

    container.appendChild(grid);

    // delegate clicks
    grid.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-action');
      const course = decodeURIComponent(btn.getAttribute('data-course') || '');
      if (action === 'materials') {
        location.href = `course-materials.html?course=${encodeURIComponent(course)}`;
      } else if (action === 'chat') {
        location.href = `chat.html?course=${encodeURIComponent(course)}`;
      }
    });
  }

  function renderUploads(uploads) {
    const container = el(SELECTORS.uploadsList);
    if (!container) return;
    clearChildren(container);

    if (!Array.isArray(uploads) || uploads.length === 0) {
      container.innerHTML = `<div class="cv-empty">No recent uploads.</div>`;
      return;
    }

    const ul = document.createElement('ul');
    ul.className = 'cv-upload-list';

    uploads.slice(0, 8).forEach(u => {
      const id = u.id ?? '';
      const title = u.title ?? u.name ?? 'Untitled';
      const when = u.when ?? u.createdAt ?? u.date ?? null;
      const type = (u.type || '').toUpperCase() || 'FILE';

      const li = document.createElement('li');
      li.className = 'cv-upload-item';
      li.innerHTML = `
        <div class="cv-upload-left">
          <div class="cv-upload-type">${type}</div>
        </div>
        <div class="cv-upload-body">
          <div class="cv-upload-title">${title}</div>
          <div class="cv-upload-meta cv-muted">${when ? formatRelative(when) : ''}</div>
        </div>
        <div class="cv-upload-actions">
          <button class="cv-btn-link" data-action="view" data-id="${encodeURIComponent(id)}">View</button>
          <button class="cv-btn-link" data-action="edit" data-id="${encodeURIComponent(id)}">Edit</button>
        </div>
      `;
      ul.appendChild(li);
    });

    container.appendChild(ul);

    ul.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-action');
      const id = decodeURIComponent(btn.getAttribute('data-id') || '');
      if (action === 'view') {
        location.href = `upload.html?view=${encodeURIComponent(id)}`;
      } else if (action === 'edit') {
        location.href = `upload.html?edit=${encodeURIComponent(id)}`;
      }
    });
  }

  // --- Fallback mocks (your original arrays) ---
  const MOCK_COURSES = [
    { code: 'CS201', title: 'Data Structures', semester: 'Autumn 2025', enrolled: 120 },
    { code: 'CS403', title: 'Cybersecurity', semester: 'Autumn 2025', enrolled: 88 },
  ];
  const MOCK_UPLOADS = [
    { id: 'upl-1', title: 'Assignment 1', when: '2025-10-16', type: 'pdf' },
    { id: 'upl-2', title: 'Lecture 7 - Slides', when: '2025-10-10', type: 'pdf' },
  ];

  // --- Quick action wiring ---
  function attachQuickActions() {
    const up = el(SELECTORS.btnUpload);
    const post = el(SELECTORS.btnPostNotice);
    const contact = el(SELECTORS.btnContactAdmin);
    const logout = el(SELECTORS.logoutBtn);
    const hamburger = el(SELECTORS.hamburger);
    const topnav = el(SELECTORS.topnav);

    if (up) up.addEventListener('click', () => (location.href = 'upload.html'));
    if (post) post.addEventListener('click', () => (location.href = 'create-notice.html'));
    if (contact) contact.addEventListener('click', () => (location.href = 'contact-admin.html'));

    if (logout) {
      logout.addEventListener('click', async () => {
        try {
          // If a global logout function exists, call it to clear session on server
          if (typeof window.__LOGOUT__ === 'function') {
            await window.__LOGOUT__();
          } else if (API_BASE) {
            await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'same-origin' });
          }
        } catch (e) {
          // ignore errors and proceed to client-side redirect
        } finally {
          location.href = '/';
        }
      });
    }

    if (hamburger && topnav) {
      hamburger.addEventListener('click', () => {
        topnav.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', String(topnav.classList.contains('open')));
      });
    }
  }

  // --- Initialization ---
  async function init() {
    attachQuickActions();

    // attempt to fetch remote data, fallback to mocks
    const [coursesRemote, uploadsRemote] = await Promise.allSettled([fetchCourses(), fetchUploads()]);

    const courses = (coursesRemote.status === 'fulfilled' && Array.isArray(coursesRemote.value) && coursesRemote.value.length)
      ? coursesRemote.value
      : MOCK_COURSES;

    const uploads = (uploadsRemote.status === 'fulfilled' && Array.isArray(uploadsRemote.value) && uploadsRemote.value.length)
      ? uploadsRemote.value
      : MOCK_UPLOADS;

    renderCourses(courses);
    renderUploads(uploads);
  }

  // run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
