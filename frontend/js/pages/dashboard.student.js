// dashboard.student.js
(function () {
  const user = window.__USER__ || null;
  if (!user || user.role !== 'student') {
    console.warn('Permission error: student-only page.');
    window.location.href = '/login.html';
    return;
  }

  document.getElementById('greeting').textContent = `Welcome, ${user.name}!`;

  // TODO: fetch student's enrolled courses/resources: GET /api/student/resources
  const resources = [
    { title: 'Data Structures - Notes', source: 'Prof. A' },
    { title: 'OS Lab Manual', source: 'Library' },
  ];
  const list = document.getElementById('resource-list');
  resources.forEach(r => {
    const li = document.createElement('div');
    li.className = 'cv-item';
    li.innerHTML = `<div><strong>${r.title}</strong><div class="muted">${r.source}</div></div>
                    <div><button class="cv-btn-link">Open</button></div>`;
    list.appendChild(li);
  });

  // Latest uploads - TODO: fetch global/latest uploads
  const uploads = [
    { title: 'Database Notes', when: '2 days ago' },
    { title: 'Programming Lab Solutions', when: '4 days ago' },
  ];
  const uploadsEl = document.getElementById('latest-uploads');
  uploads.forEach(u => {
    const li = document.createElement('div');
    li.className = 'cv-item';
    li.innerHTML = `<div><strong>${u.title}</strong><div class="muted">${u.when}</div></div>
                    <div><button class="cv-btn-link">View</button></div>`;
    uploadsEl.appendChild(li);
  });

  // Actions
  document.getElementById('btn-search-library').addEventListener('click', () => {
    window.location.href = 'library.html';
  });
  document.getElementById('btn-open-chat').addEventListener('click', () => {
    window.location.href = 'chat.html';
  });
  document.getElementById('btn-raise-complaint').addEventListener('click', () => {
    window.location.href = 'complaint.html';
  });
})();
