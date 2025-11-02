// dashboard.admin.js
// Controller for admin-dashboard.html
// Backend integration points are marked with TODO comments

(function () {
  // Ensure the user is an admin.
  // BACKEND OPTION A: Server redirects non-admins away before rendering this page.
  // BACKEND OPTION B: Server injects user into window.__USER__ (see auth.js) and we verify here.
  const user = window.__USER__ || null; // backend can set: <script>window.__USER__ = { id:123, role:'admin', name:'Anubhab' }</script>

  if (!user || user.role !== 'admin') {
    // If backend didn't redirect, enforce client-side
    console.warn('Permission error: admin-only page.');
    // Redirect to login or role-appropriate page.
    // NOTE: backend should redirect earlier; this is a fallback.
    window.location.href = '/login.html';
    return;
  }

  // Populate welcome greeting
  document.getElementById('greeting').textContent = `Hello, ${user.name} — system summary below.`;

  // Small helper to create tiles
  function makeTile(title, value, subtitle) {
    const el = document.createElement('div');
    el.className = 'cv-tile';
    el.innerHTML = `<h4>${title}</h4><p>${value}</p><small>${subtitle || ''}</small>`;
    return el;
  }

  // TODO: Replace stubbed data with API calls to server endpoints
  // Example: fetch('/api/admin/overview').then(res => res.json()).then(renderOverview)
  const overviewData = [
    { title: 'Total Users', value: '2,134', subtitle: 'Students/Faculty/Admin' },
    { title: 'Total Uploads', value: '4,890', subtitle: 'Last 30 days' },
    { title: 'Pending Approvals', value: '12', subtitle: 'Uploads & User requests' },
    { title: 'Active Sessions', value: '230', subtitle: 'Real-time' },
  ];

  const grid = document.getElementById('overview-grid');
  overviewData.forEach(d => grid.appendChild(makeTile(d.title, d.value, d.subtitle)));

  // Latest uploads - TODO: fetch from API
  const latestUploads = [
    { title: 'AI Lecture Notes', owner: 'Prof. X', when: '2 hours ago' },
    { title: 'DBMS Slides', owner: 'Prof. Y', when: '1 day ago' },
  ];
  const uploadsEl = document.getElementById('latest-uploads');
  latestUploads.forEach(u => {
    const li = document.createElement('div');
    li.className = 'cv-item';
    li.innerHTML = `<div><strong>${u.title}</strong><div class="muted">${u.owner} • ${u.when}</div></div>
                    <div><button class="cv-btn-link">View</button></div>`;
    uploadsEl.appendChild(li);
  });

  // Hook up quick action buttons (call backend endpoints)
  document.getElementById('btn-manage-users').addEventListener('click', () => {
    window.location.href = 'admin-users.html';
  });
  document.getElementById('btn-manage-library').addEventListener('click', () => {
    window.location.href = 'admin-library.html';
  });
  document.getElementById('btn-system-reports').addEventListener('click', () => {
    // Example: open reports generator endpoint
    window.open('/admin/reports', '_blank');
  });
})();
