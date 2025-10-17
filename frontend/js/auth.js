document.getElementById('login-form')?.addEventListener('submit', async e=>{
  e.preventDefault();
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const res = await api.post('/auth/login', {email, password});
  if(res && res.ok){
    alert('Login success (demo)');
    location.href = 'dashboard.html';
  } else {
    alert('Login failed. In dev, use backend default credentials or register.');
  }
});
