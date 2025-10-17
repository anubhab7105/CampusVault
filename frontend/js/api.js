/*
  Minimal API wrapper.
  If backend is served under a base path set API_BASE accordingly e.g. 'http://127.0.0.1:8000/api'
*/
const API_BASE = ''; // leave empty if backend on same host and using /api path (starter backend uses /api)

const api = {
  _url(path){
    // if path already absolute, return as-is
    if(path.startsWith('http') || path.startsWith('/')) return (API_BASE || '') + path;
    return (API_BASE || '') + path;
  },
  async get(path){
    try{
      const res = await fetch(this._url(path));
      if(!res.ok) return [];
      return await res.json();
    }catch(e){
      console.error('api.get error', e);
      return [];
    }
  },
  async post(path, body){
    try{
      const res = await fetch(this._url(path), {
        method:'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      return await res.json();
    }catch(e){ console.error('api.post error', e); return null; }
  },
  async postForm(path, formData){
    try{
      const res = await fetch(this._url(path), {method:'POST', body: formData});
      return await res.json();
    }catch(e){ console.error('api.postForm error', e); return null; }
  }
};
