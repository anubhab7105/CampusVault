const API = 'http://localhost:4000/api';

const main = document.getElementById('main');

// Simple SPA: show home, signup, login
function showHome() {
  main.innerHTML = `
    <div class="card">
      <h2>Welcome to CampusVault</h2>
      <p><button id="btn-docs">Browse Documents</button> <button id="btn-signup">Sign Up</button> <button id="btn-login">Log In</button></p>
    </div>
  `;
  document.getElementById('btn-docs').addEventListener('click', showDocs);
  document.getElementById('btn-signup').addEventListener('click', showSignup);
  document.getElementById('btn-login').addEventListener('click', showLogin);
}

async function showDocs() {
  main.innerHTML = '<div class="card"><h3>Documents</h3><div id="docs-list">Loading…</div></div>';
  const res = await fetch(`${API}/documents`, { headers: { 'Accept': 'application/json' } });
  const json = await res.json();
  const container = document.getElementById('docs-list');
  if (json.ok) {
    container.innerHTML = json.docs.map(d => `<div class="card"><h4>${d.title}</h4><p>${d.description||''}</p><a href='${d.fileUrl}' target='_blank'>View</a></div>`).join('');
  } else container.textContent = 'Error fetching documents';
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
    const res = await fetch(`${API}/auth/request-otp`, { method: 'POST', headers: { 'Content-Type':'application/json'}, body: JSON.stringify({ phone }) });
    const json = await res.json();
    if (json.ok) {
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
    const res = await fetch(`${API}/auth/verify-otp`, { method: 'POST', headers: { 'Content-Type':'application/json'}, body: JSON.stringify({ fullName, collegeId, email, phone, code, password }) });
    const json = await res.json();
    if (json.ok) {
      alert('Signup complete — please login');
      showLogin();
    } else console.error(json);
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
    const res = await fetch(`${API}/auth/login`, { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ email, password }) });
    const json = await res.json();
    if (json.token) { localStorage.setItem('token', json.token); alert('Logged in'); showDocs(); }
    else alert('Invalid credentials');
  });
}

showHome();