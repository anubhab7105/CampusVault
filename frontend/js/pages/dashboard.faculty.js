// dashboard.faculty.js
(function () {
  const user = window.__USER__ || null;
  if (!user || user.role !== 'faculty') {
    console.warn('Permission error: faculty-only page.');
    window.location.href = '/login.html';
    return;
  }

  document.getElementById('greeting').textContent = `Hello, ${user.name}. Here are your courses and recent uploads.`;

  // TODO: Replace with fetch('/api/faculty/courses')
  const courses = [
    { code: 'CS201', title: 'Data Structures', semester: 'Autumn 2025' },
    { code: 'CS403', title: 'Cybersecurity', semester: 'Autumn 2025' },
  ];
  const courseList = document.getElementById('course-list');
  courses.forEach(c => {
    const item = document.createElement('div');
    item.className = 'cv-item';
    item.innerHTML = `<div><strong>${c.code} — ${c.title}</strong><div class="muted">${c.semester}</div></div>
                      <div><button class="cv-btn" onclick="location.href='course-materials.html?course=${c.code}'">Open</button></div>`;
    courseList.appendChild(item);
  });

  // Recent uploads - TODO: fetch personal uploads
  const uploads = [
    { title: 'Assignment 1', when: '3 days ago' },
    { title: 'Lecture 7 - Slides', when: '1 week ago' },
  ];
  const uploadsEl = document.getElementById('latest-uploads');
  uploads.forEach(u => {
    const li = document.createElement('div');
    li.className = 'cv-item';
    li.innerHTML = `<div><strong>${u.title}</strong><div class="muted">${u.when}</div></div>
                    <div><button class="cv-btn-link">Edit</button></div>`;
    uploadsEl.appendChild(li);
  });

  // Quick action handlers
  document.getElementById('btn-upload-material').addEventListener('click', () => {
    window.location.href = 'upload.html';
  });
  document.getElementById('btn-post-notice').addEventListener('click', () => {
    window.location.href = 'create-notice.html';
  });
  document.getElementById('btn-contact-admin').addEventListener('click', () => {
    window.location.href = 'contact-admin.html';
  });
})();
