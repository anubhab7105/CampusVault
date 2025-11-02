import { API_BASE as _API_BASE } from '../config.js';
import { fetchLibrary as _fetchLibrary } from '../api.js';
import Paginator from '../components/paginator.js';
import { createFileCard } from '../components/fileCard.js';
import { qs, qsa, el, debounce } from '../lib/dom.js'; // small DOM helpers (assumed)

const API_BASE = typeof _API_BASE !== 'undefined' ? _API_BASE : '/api';
const fetchLibrary = typeof _fetchLibrary === 'function' ? _fetchLibrary : fallbackFetchLibrary;

const ELEMENTS = {
  form: qs('#library-filter'),
  q: qs('#q'),
  filterType: qs('#filter-type'),
  searchBtn: qs('#search-btn'),
  list: qs('#library-list'),
  pager: qs('#library-pager'),
};

const DEFAULTS = {
  page: 1,
  perPage: 12,
  sort: 'newest'
};

let state = {
  q: '',
  type: '',
  page: DEFAULTS.page,
  perPage: DEFAULTS.perPage,
  total: 0,
  loading: false,
};

/* --------------- Initialization --------------- */
function init() {
  attachEvents();
  loadFromUrl();
  fetchAndRender();
  makeKeyboardShortcuts();
}

function attachEvents() {
  // submit handler (prevent full page reload)
  ELEMENTS.form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    state.page = 1;
    readFormToState();
    pushUrl();
    fetchAndRender();
  });

  // debounce input search
  ELEMENTS.q.addEventListener('input', debounce((ev) => {
    state.page = 1;
    state.q = ev.target.value.trim();
    pushUrl();
    fetchAndRender();
  }, 350));

  ELEMENTS.filterType.addEventListener('change', (ev) => {
    state.page = 1;
    state.type = ev.target.value;
    pushUrl();
    fetchAndRender();
  });

  // delegate click in list for accessibility (open/download)
  ELEMENTS.list.addEventListener('click', (ev) => {
    const card = ev.target.closest('[data-file-id]');
    if (!card) return;
    const fileId = card.dataset.fileId;
    openFile(fileId);
  });
}

/* --------------- Fetch & render --------------- */
async function fetchAndRender() {
  const { q, type, page, perPage } = state;
  setLoading(true);
  try {
    const res = await fetchLibrary({
      q,
      type,
      page,
      perPage
    });

    // Expect: { items: [...], total: N } — fallbacks handled in fetchLibrary
    const items = Array.isArray(res.items) ? res.items : [];
    const total = typeof res.total === 'number' ? res.total : items.length;

    state.total = total;
    renderList(items);
    renderPager({ total, page, perPage });
    if (!items.length) renderEmpty();
  } catch (err) {
    console.error('Library fetch error', err);
    renderError(err);
  } finally {
    setLoading(false);
  }
}

function renderList(items = []) {
  const container = ELEMENTS.list;
  container.innerHTML = '';

  const fragment = document.createDocumentFragment();
  items.forEach(file => {
    // create a wrapper element that your fileCard expects
    const cardEl = el('div', { className: 'file-card-wrap', attributes: { 'data-file-id': file.id || file._id || '' } });
    // Use createFileCard — it should render content inside the passed element and return it
    try {
      createFileCard(cardEl, file, { onOpen: () => openFile(file.id || file._id) });
    } catch (e) {
      // If createFileCard isn't available or failed, fallback to a minimal card
      cardEl.innerHTML = fallbackFileCardHtml(file);
    }
    fragment.appendChild(cardEl);
  });

  container.appendChild(fragment);
}

function renderPager({ total, page, perPage }) {
  const pagerEl = ELEMENTS.pager;
  pagerEl.innerHTML = '';

  if (typeof Paginator === 'function') {
    // try to instantiate / call the Paginator component
    try {
      const paginator = new Paginator({
        container: pagerEl,
        total,
        page,
        perPage,
        onPage: (p) => {
          state.page = p;
          pushUrl();
          fetchAndRender();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
      paginator.render && paginator.render();
      return;
    } catch (e) {
      // fall through to fallback pager
      console.warn('Paginator component failed, using fallback pager', e);
    }
  }

  // fallback simple pager
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  pagerEl.innerHTML = fallbackPagerHtml(page, totalPages);
  pagerEl.querySelectorAll('button[data-page]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.page = Number(btn.dataset.page);
      pushUrl();
      fetchAndRender();
    });
  });
}

function renderEmpty() {
  ELEMENTS.list.innerHTML = `
    <div class="cv-empty">
      <p>No files found for your query.</p>
      <p class="muted">Try removing filters or search terms.</p>
    </div>
  `;
}

function renderError(err) {
  ELEMENTS.list.innerHTML = `
    <div class="cv-error">
      <strong>Failed to load library.</strong>
      <p>${escapeHtml(String(err.message || err))}</p>
    </div>
  `;
}

/* --------------- Actions --------------- */
function openFile(fileId) {
  if (!fileId) return;
  // Ideally your backend exposes /library/:id/download or a url in item.downloadUrl.
  // We'll attempt to find the card's attached data (if createFileCard stored it) or request an endpoint.
  const card = qs(`[data-file-id="${CSS.escape(fileId)}"]`);
  let downloadUrl = card?.dataset?.downloadUrl;
  if (downloadUrl) {
    window.open(downloadUrl, '_blank');
    return;
  }
  // fallback: open /library/{id}
  window.open(`${API_BASE.replace(/\/$/, '')}/library/${fileId}`, '_blank');
}

/* --------------- Utilities --------------- */
function setLoading(loading) {
  state.loading = loading;
  if (loading) {
    ELEMENTS.list.classList.add('loading');
    // show spinner if not present
    if (!qs('.cv-loader', ELEMENTS.list)) {
      const spinner = el('div', { className: 'cv-loader', innerHTML: `<div class="dot-spinner" aria-hidden="true"></div>` });
      ELEMENTS.list.appendChild(spinner);
    }
  } else {
    ELEMENTS.list.classList.remove('loading');
    const s = qs('.cv-loader', ELEMENTS.list);
    if (s) s.remove();
  }
}

function readFormToState() {
  state.q = ELEMENTS.q.value.trim();
  state.type = ELEMENTS.filterType.value;
}

function pushUrl() {
  // keep state in URL so refreshing / sharing preserves filters
  const params = new URLSearchParams();
  if (state.q) params.set('q', state.q);
  if (state.type) params.set('type', state.type);
  if (state.page && state.page !== 1) params.set('page', state.page);
  const url = `${location.pathname}?${params.toString()}`;
  history.replaceState({}, '', url);
}

function loadFromUrl() {
  const params = new URLSearchParams(location.search);
  state.q = params.get('q') || '';
  state.type = params.get('type') || '';
  state.page = parseInt(params.get('page'), 10) || DEFAULTS.page;

  ELEMENTS.q.value = state.q;
  ELEMENTS.filterType.value = state.type;
}

function makeKeyboardShortcuts() {
  // Focus search on "/" press
  window.addEventListener('keydown', (ev) => {
    if (ev.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      ev.preventDefault();
      ELEMENTS.q.focus();
    }
  });
}

/* --------------- Fallback helpers --------------- */

async function fallbackFetchLibrary({ q = '', type = '', page = 1, perPage = 12 } = {}) {
  // Basic fallback: GET /api/library?q=...&type=...&page=...&perPage=...
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (type) params.set('type', type);
  params.set('page', page);
  params.set('perPage', perPage);

  const url = `${API_BASE.replace(/\/$/, '')}/library?${params.toString()}`;
  const resp = await fetch(url, { credentials: 'same-origin' });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`HTTP ${resp.status} ${text}`);
  }
  return resp.json();
}

function fallbackFileCardHtml(file = {}) {
  const title = escapeHtml(file.title || file.name || 'Untitled');
  const type = escapeHtml(file.type || '');
  const size = escapeHtml(file.size ? humanFileSize(file.size) : '');
  const faculty = escapeHtml(file.faculty || file.author || '');
  const uploaded = escapeHtml(file.uploadedAt ? new Date(file.uploadedAt).toLocaleDateString() : '');
  const download = escapeHtml(file.downloadUrl || `${API_BASE}/library/${file.id || file._id}`);
  return `
    <article class="file-card">
      <div class="file-card-meta">
        <div class="file-icon">${fileIcon(type)}</div>
        <div class="file-info">
          <h3 class="file-title">${title}</h3>
          <div class="file-sub">${faculty} • ${type.toUpperCase()} • ${size}</div>
        </div>
      </div>
      <div class="file-card-actions">
        <a class="cv-btn cv-btn-ghost" href="${download}" target="_blank" rel="noopener">Open</a>
      </div>
      <time class="file-time" datetime="${escapeHtml(file.uploadedAt || '')}">${uploaded}</time>
    </article>
  `;
}

function fallbackPagerHtml(page, totalPages) {
  const prevDisabled = page <= 1 ? 'disabled' : '';
  const nextDisabled = page >= totalPages ? 'disabled' : '';
  let pageButtons = '';
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let p = start; p <= end; p++) {
    pageButtons += `<button class="cv-pager-btn ${p === page ? 'active' : ''}" data-page="${p}" aria-current="${p === page ? 'page' : 'false'}">${p}</button>`;
  }
  return `
    <div class="cv-pager-inner" role="navigation" aria-label="Pagination">
      <button class="cv-pager-nav" ${prevDisabled} data-page="${Math.max(1, page - 1)}">&larr; Prev</button>
      ${pageButtons}
      <button class="cv-pager-nav" ${nextDisabled} data-page="${Math.min(totalPages, page + 1)}">Next &rarr;</button>
    </div>
  `;
}

function fileIcon(type) {
  const t = (type || '').toLowerCase();
  if (t.includes('pdf')) return '📄';
  if (t.includes('ppt')) return '📊';
  if (t.includes('xls') || t.includes('csv')) return '📈';
  if (t.includes('doc')) return '📝';
  return '📁';
}

function humanFileSize(bytes, si = true) {
  const thresh = si ? 1000 : 1024;
  if (Math.abs(bytes) < thresh) return bytes + ' B';
  const units = si ? ['kB','MB','GB','TB','PB','EB','ZB','YB'] : ['KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB'];
  let u = -1;
  do {
    bytes /= thresh;
    ++u;
  } while (Math.abs(bytes) >= thresh && u < units.length - 1);
  return bytes.toFixed(1) + ' ' + units[u];
}

function escapeHtml(s = '') {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/* --------------- Kickoff --------------- */
document.addEventListener('DOMContentLoaded', init);

// Export for tests or external use
export { fetchAndRender, state };
