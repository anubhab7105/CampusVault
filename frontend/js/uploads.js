document.getElementById('upload-form')?.addEventListener('submit', async e=>{
  e.preventDefault();
  const title = document.getElementById('title').value;
  const file = document.getElementById('file').files[0];
  if(!file) return alert('Pick a file');
  const fd = new FormData();
  fd.append('file', file);
  fd.append('title', title);
  // demo: optionally add faculty_unique_id if you want server to record it
  fd.append('faculty_unique_id', 'F000001');
  const res = await api.postForm('/uploads', fd);
  if(res && res.id) alert('Uploaded');
  fetchLibrary();
});

async function fetchLibrary(){
  const list = await api.get('/uploads');
  const target = document.getElementById('library-list');
  if(!target) return;
  if(!list || list.length===0) target.textContent = 'No uploads yet.';
  else target.innerHTML = list.map(u=>`<div class="card"><h4>${u.title}</h4><p>By: ${u.faculty_unique_id}</p><a href="/uploads/${u.filename}" download>Download</a></div>`).join('');
}
