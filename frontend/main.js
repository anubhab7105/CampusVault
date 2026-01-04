const API = 'http://localhost:4000/api';

const main = document.getElementById('main');

// Helpers
async function api(path, opts = {}) {
  opts.headers = opts.headers || {};
  const token = localStorage.getItem('token');
  if (token) opts.headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, opts);
  return res.json();
}

// Simple SPA: show home, signup, login
async function renderNav() {
  const nav = document.getElementById('nav') || document.createElement('div');
  const user = await api('/auth/me').catch(()=>null);
  let html = 'CampusVault';
  if (user && user.ok) {
    html += ` - ${user.user.fullName} (<span id="role">${user.user.role}</span>) <button id="logout">Logout</button>`;
    if (user.user.role === 'admin') html += ` <button id="adminBtn">Admin</button>`;
  } else {
    html += ` <button id="homeLogin">Login</button>`;
  }
  if (document.getElementById('nav')) document.getElementById('nav').innerHTML = html;
  if (document.getElementById('logout')) document.getElementById('logout').addEventListener('click', () => { localStorage.removeItem('token'); renderNav(); showHome(); });
  if (document.getElementById('homeLogin')) document.getElementById('homeLogin').addEventListener('click', showLogin);
  if (document.getElementById('adminBtn')) document.getElementById('adminBtn').addEventListener('click', showAdmin);
}

function showHome() {
  main.innerHTML = `
    <div class="card">
      <h2>Welcome to CampusVault</h2>
      <p><button id="btn-docs">Browse Documents</button> <button id="btn-signup">Sign Up</button> <button id="btn-login">Log In</button></p>
    </div>
  `;
  document.getElementById('btn-docs').addEventListener('click', () => { renderNav(); showDocs(); });
  document.getElementById('btn-signup').addEventListener('click', showSignup);
  document.getElementById('btn-login').addEventListener('click', showLogin);
}

renderNav();

async function showDocs() {
  main.innerHTML = '<div class="card"><h3>Documents</h3><div id="docs-list">Loading…</div></div>';
  const json = await api('/documents');
  const container = document.getElementById('docs-list');
  if (json.ok) {
    container.innerHTML = json.docs.map(d => `<div class="card"><h4>${d.title}</h4><p>${d.description||''}</p><p><button data-id="${d.id}" class="viewBtn">Open</button></p></div>`).join('');
    document.querySelectorAll('.viewBtn').forEach(b => b.addEventListener('click', (e) => showDocDetails(e.target.dataset.id)));
    // show upload button to faculty/admin
    const me = await api('/auth/me').catch(()=>null);
    if (me && me.ok && (me.user.role === 'faculty' || me.user.role === 'admin')) {
      const btn = document.createElement('button'); btn.textContent = 'Upload Document'; btn.addEventListener('click', showUpload);
      container.prepend(btn);
    }
  } else container.textContent = 'Error fetching documents';
}

function showUpload() {
  main.innerHTML = `
    <div class="card">
      <h3>Upload Document</h3>
      <label>Title<input id="title"></label>
      <label>Description<textarea id="description"></textarea></label>
      <label>File<input id="file" type="file"></label>
      <label>Public<select id="isPublic"><option value="true">Public</option><option value="false">Private</option></select></label>
      <p><button id="doUpload">Upload</button> <button id="cancel">Cancel</button></p>
    </div>
  `;
  document.getElementById('cancel').addEventListener('click', showDocs);
  document.getElementById('doUpload').addEventListener('click', async () => {
    const title = document.getElementById('title').value;
    const description = document.getElementById('description').value;
    const file = document.getElementById('file').files[0];
    const isPublic = document.getElementById('isPublic').value;
    if (!file) return alert('File required');
    const form = new FormData(); form.append('file', file); form.append('title', title); form.append('description', description); form.append('isPublic', isPublic);
    const token = localStorage.getItem('token');
    const res = await fetch(`${API}/documents`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: form });
    const json = await res.json();
    if (json.ok) { alert('Uploaded'); showDocs(); } else alert('Upload failed');
  });
}

async function showAdmin() {
  main.innerHTML = '<div class="card"><h3>Admin Dashboard</h3><div id="admin-area">Loading…</div></div>';
  const usersRes = await api('/users');
  const logsRes = await api('/users/access-logs/all');
  const area = document.getElementById('admin-area');
  let html = '<h4>Users</h4>';
  if (usersRes.ok) html += usersRes.users.map(u => `<div class="card">${u.fullName} (${u.email}) - ${u.role} <button data-id="${u.id}" class="delUser">Delete</button></div>`).join('');
  html += '<h4>Recent Logs</h4>';
  if (logsRes.ok) html += logsRes.logs.map(l => `<div class="card">${l.action} user:${l.userId} doc:${l.documentId} at ${l.createdAt}</div>`).join('');
  area.innerHTML = html;
  document.querySelectorAll('.delUser').forEach(b => b.addEventListener('click', async (e) => {
    if (!confirm('Delete user?')) return;
    const id = e.target.dataset.id;
    const res = await fetch(`${API}/users/${id}`, { method: 'DELETE', headers: {'Authorization': `Bearer ${localStorage.getItem('token')}`} });
    const j = await res.json(); if (j.ok) { alert('Deleted'); showAdmin(); } else alert('Failed');
  }));
}

async function showDocDetails(id) {
  main.innerHTML = '<div class="card">Loading…</div>';
  const [docRes, commentsRes] = await Promise.all([api(`/documents/${id}/view`), api(`/comments/${id}`)]);
  if (!docRes.ok) return main.textContent = 'Not found or forbidden';
  const doc = docRes.fileUrl ? { fileUrl: docRes.fileUrl } : {};
  const comments = commentsRes.ok ? commentsRes.comments : [];
  main.innerHTML = `
    <div class="card">
      <h3>Document ${id}</h3>
      <p><a href="${doc.fileUrl || '#'}" target="_blank">Open file</a></p>
      <div id="comments">
        <h4>Comments</h4>
        <div id="comments-list">${comments.map(c=>`<div class="card"><b>${c.author ? c.author.fullName : 'User'}</b><p>${c.body}</p></div>`).join('') || '<p>No comments</p>'}</div>
        <div id="add-comment"><textarea id="commentBody" placeholder="Ask a question or comment"></textarea><p><button id="postComment">Post</button></p></div>
      </div>
      <p><button id="back">Back</button></p>
    </div>
  `;
  document.getElementById('back').addEventListener('click', showDocs);
  document.getElementById('postComment').addEventListener('click', async () => {
    const body = document.getElementById('commentBody').value;
    const res = await api(`/comments/${id}`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ body }) });
    if (res.ok) { alert('Posted'); showDocDetails(id); } else alert('Failed');
  });
}

function showSignup() {
  main.innerHTML = `
    <div class="card">
      <h3>Sign Up</h3>
      <div id="signup-steps">
        <div id="step1">
          <label>Full name<input id="fullName"></label>
          <label>College ID<input id="collegeId"></label>
          <label>Email<input id="email"></label>
          <label>Phone<input id="phone"></label>
          <p><button id="requestOtp">Request OTP</button></p>
        </div>
        <div id="step2" style="display:none">
          <label>OTP<input id="otp"></label>
          <label>Password<input id="password" type="password"></label>
          <p><button id="verifyOtp">Complete Signup</button></p>
        </div>
      </div>
      <p><a href="#" id="back">Back</a></p>
    </div>
  `;
  document.getElementById('back').addEventListener('click', (e) => { e.preventDefault(); showHome(); });
  document.getElementById('requestOtp').addEventListener('click', async () => {
    const phone = document.getElementById('phone').value;
    const res = await api('/auth/request-otp', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ phone }) });
    if (res.ok) {
      document.getElementById('step1').style.display = 'none';
      document.getElementById('step2').style.display = 'block';
      alert('OTP sent (demo)');
    } else alert('Error');
  });
  document.getElementById('verifyOtp').addEventListener('click', async () => {
    const fullName = document.getElementById('fullName').value;
    const collegeId = document.getElementById('collegeId').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const code = document.getElementById('otp').value;
    const password = document.getElementById('password').value;
    const res = await api('/auth/verify-otp', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ fullName, collegeId, email, phone, code, password }) });
    if (res.ok) { alert('Signup complete — please login'); showLogin(); } else console.error(res);
  });
}

function showLogin() {
  main.innerHTML = `
    <div class="card">
      <h3>Log In</h3>
      <label>Email<input id="loginEmail"></label>
      <label>Password<input id="loginPassword" type="password"></label>
      <p><button id="doLogin">Log In</button></p>
      <p><a href="#" id="back2">Back</a></p>
    </div>
  `;
  document.getElementById('back2').addEventListener('click', (e) => { e.preventDefault(); showHome(); });
  document.getElementById('doLogin').addEventListener('click', async () => {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const res = await api('/auth/login', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email, password }) });
    if (res.token) { localStorage.setItem('token', res.token); alert('Logged in'); showDocs(); }
    else alert('Invalid credentials');
  });
}

showHome();