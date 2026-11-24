/* Модуль тестирования: перенесён из ProjectSHAD_Diplom_testirovanie (Vanilla JS) в одно ES-модуль.
   Страницы строят DOM и монтируются Vue-хостом (ui/pages/testing). Хост задаёт транспорт и навигацию
   через configureTesting(); всплывающие окна добавляются в контейнер .pp с общими стилями ProjectProgon. */

const host = { request: null, navigate: () => {}, rerender: () => {} };
let leaveGuard = null; // возвращает текст предупреждения, если есть несохранённые изменения

export function configureTesting(options) { Object.assign(host, options); }
export function leaveMessage() { try { return leaveGuard ? leaveGuard() : ''; } catch { return ''; } }
export function resetLeaveGuard() { leaveGuard = null; }

let portalNode = null;
function portal() {
  if (!portalNode || !portalNode.isConnected) {
    portalNode = document.createElement('div');
    portalNode.className = 'pp pp-portal';
    document.body.append(portalNode);
  }
  return portalNode;
}

/* Общие помощники интерфейса: элементы, значки, уведомления, API, перетаскивание. */

function el(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith('aria-')) { node.setAttribute(k, String(v)); continue; }
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'html') node.innerHTML = v; // только константы-иконки и очищенный сервером HTML
    else if (k === 'value') node.value = v;
    else if (k === 'checked' || k === 'disabled' || k === 'selected') node[k] = !!v;
    else if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (v === true) node.setAttribute(k, '');
    else node.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

const _svg = (inner) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
const ICONS = {
  user: _svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
  post: _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>'),
  layers: _svg('<path d="M12 2l10 5-10 5L2 7z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>'),
  flag: _svg('<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>'),
  edit: _svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>'),
  plus: _svg('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 8v8M8 12h8"/>'),
  eye: _svg('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'),
  logout: _svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>'),
  sun: _svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  moon: _svg('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'),
  trash: _svg('<path d="M3 6h18"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'),
  check: _svg('<path d="M20 6L9 17l-5-5"/>'),
  open: _svg('<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6M10 14L21 3"/>'),
  x: _svg('<path d="M18 6L6 18M6 6l12 12"/>'),
  add: _svg('<path d="M12 5v14M5 12h14"/>'),
  up: _svg('<path d="M18 15l-6-6-6 6"/>'),
  down: _svg('<path d="M6 9l6 6 6-6"/>'),
  left: _svg('<path d="M15 18l-6-6 6-6"/>'),
  right: _svg('<path d="M9 18l6-6-6-6"/>'),
  copy: _svg('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  grip: _svg('<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>'),
  key: _svg('<path d="M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.8 7.8 5.5 5.5 0 0 1 7.8-7.8zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>'),
  chart: _svg('<path d="M18 20V10M12 20V4M6 20v-6"/>'),
};
const icon = (name) => el('span', { class: 'icon', 'data-icon': name, html: ICONS[name] || '' });

function ibtn({ icon: name, tip, onclick, danger = false, on = false, bordered = false, href, disabled = false }) {
  const props = { class: `ibtn${danger ? ' danger' : ''}${on ? ' on' : ''}${bordered ? ' bordered' : ''}`, 'data-tip': tip, 'aria-label': tip };
  if (href) return el('a', { ...props, href }, icon(name));
  return el('button', { ...props, type: 'button', onclick, disabled }, icon(name));
}

function toast(message, kind = '') {
  let box = document.getElementById('toasts');
  if (!box) { box = el('div', { id: 'toasts', class: 'toasts', 'aria-live': 'polite' }); portal().append(box); }
  const t = el('div', { class: `toast ${kind}`, text: message });
  box.append(t);
  setTimeout(() => t.remove(), kind === 'error' ? 6000 : 3500);
}

/* ---------- диалоги в стиле интерфейса (вместо системных confirm/prompt) ---------- */
function openDialog({ title, message, input = null, okText = 'Подтвердить', cancelText = 'Отмена', danger = false }) {
  return new Promise((resolve) => {
    const field = input ? el('input', { type: 'text', value: input.value || '', placeholder: input.placeholder || '', 'aria-label': title }) : null;
    const err = el('p', { class: 'error-text', role: 'alert' });
    const dlg = el('dialog', { class: 'dlg', 'aria-labelledby': 'dlg-title' });
    let done = false;
    const close = (value) => { if (done) return; done = true; dlg.close(); dlg.remove(); resolve(value); };
    const ok = el('button', { type: 'submit', class: `btn ${danger ? 'danger' : 'primary'}`, text: okText });
    const form = el('form', { method: 'dialog', class: 'stack-sm', onsubmit: (e) => {
      e.preventDefault();
      if (!field) { close(true); return; }
      const v = field.value.trim();
      const problem = input.validate?.(v);
      if (problem) { err.textContent = problem; field.focus(); return; }
      close(v || null);
    } },
      el('h2', { id: 'dlg-title', text: title }),
      message ? el('p', { class: 'muted pre', text: message }) : null,
      field, err,
      el('div', { class: 'row dlg-actions' }, el('button', { type: 'button', class: 'btn ghost', text: cancelText, onclick: () => close(field ? null : false) }), ok));
    dlg.append(form);
    dlg.addEventListener('cancel', (e) => { e.preventDefault(); close(field ? null : false); });
    dlg.addEventListener('click', (e) => { if (e.target === dlg) close(field ? null : false); });
    portal().append(dlg);
    dlg.showModal();
    (field || ok).focus();
  });
}
const askConfirm = (title, message, opts = {}) => openDialog({ title, message, ...opts });
const askText = (title, input, opts = {}) => openDialog({ title, input, okText: 'Вставить', ...opts });

/* ---------- API: через транспорт приложения (токен, обновление сессии) ---------- */
class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

/* Перевод ошибок проверки сервера в понятный русский текст. */
const FIELD_NAMES = { title: 'название', description: 'описание', tasks: 'задания', prompt: 'вопрос', username: 'логин', password: 'пароль',
  full_name: 'имя', role: 'роль', good_percent: 'порог «хорошо»', excellent_percent: 'порог «замечательно»', teacher_comment: 'комментарий', teacher_grade: 'оценка' };
function humanizeError(d) {
  const msg = String(d.msg || '');
  if (msg.startsWith('Value error, ')) return msg.slice(13);
  const key = [...(d.loc || [])].reverse().find(k => typeof k === 'string' && FIELD_NAMES[k]);
  const name = key ? FIELD_NAMES[key] : 'поле';
  if (/at least 1 (character|item)/.test(msg)) return `${name}: заполните`;
  if (/at least (\d+) character/.test(msg)) return `${name}: не короче ${msg.match(/at least (\d+)/)[1]} символов`;
  if (/at most (\d+)/.test(msg)) return `${name}: не длиннее ${msg.match(/at most (\d+)/)[1]}`;
  if (/should match pattern/.test(msg)) return `${name}: недопустимые символы`;
  if (/greater than or equal|less than or equal/.test(msg)) return `${name}: значение вне допустимого диапазона`;
  if (/Input should be/.test(msg)) return `${name}: недопустимое значение`;
  return `${name}: некорректное значение`;
}

const API_PREFIX = [['/teacher/', '/testing/tutor/'], ['/student/', '/testing/student/']];

async function api(path, { method = 'GET', body } = {}) {
  const [from, to] = API_PREFIX.find(([p]) => path.startsWith(p)) || ['', ''];
  const target = '/api/v1' + (from ? to + path.slice(from.length) : path);
  try {
    return await host.request(target, { method, body });
  } catch (error) {
    const data = error.payload;
    let message = data?.error?.message || error.message || 'Запрос не выполнен';
    if (error.status === 422 && Array.isArray(data?.error?.details)) {
      message = 'Проверьте поля: ' + data.error.details.map(humanizeError).filter(Boolean).slice(0, 3).join('; ');
    }
    if (error.status === 0) message = 'Сервер недоступен. Проверьте подключение';
    throw new ApiError(message, error.status);
  }
}

/* ---------- перетаскивание указателем (мышь, касание) с запасным выбором кликом ---------- */
/* Источник: dragSource(el, payload, ctx). Цель: dropTarget(el, key, ctx). ctx.onDrop(key, payload). */
function dndContext(onDrop) {
  const ctx = { onDrop, picked: null };
  ctx.pick = (payload, node) => {
    document.querySelectorAll('.dnd-picked').forEach(n => n.classList.remove('dnd-picked'));
    if (ctx.picked && ctx.picked.payload === payload) { ctx.picked = null; return; }
    ctx.picked = { payload, node };
    node.classList.add('dnd-picked');
  };
  return ctx;
}

function dragSource(node, payload, ctx) {
  node.classList.add('dnd-source');
  node.tabIndex = 0;
  node.setAttribute('role', 'button');
  node.setAttribute('aria-label', (node.textContent || '').trim() + ': выбрать для переноса');
  let start = null, ghost = null, moved = false;
  node.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    start = { x: e.clientX, y: e.clientY }; moved = false;
    node.setPointerCapture(e.pointerId);
  });
  node.addEventListener('pointermove', (e) => {
    if (!start) return;
    if (!moved && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 6) return;
    if (!moved) {
      moved = true;
      ghost = node.cloneNode(true);
      ghost.classList.add('dnd-ghost');
      ghost.style.width = node.offsetWidth + 'px';
      portal().append(ghost);
      node.classList.add('dnd-dragging');
    }
    ghost.style.left = e.clientX - node.offsetWidth / 2 + 'px';
    ghost.style.top = e.clientY - 16 + 'px';
    document.querySelectorAll('.dnd-over').forEach(n => n.classList.remove('dnd-over'));
    const t = targetAt(e.clientX, e.clientY, ghost);
    if (t) t.classList.add('dnd-over');
  });
  const finish = (e) => {
    if (!start) return;
    start = null;
    document.querySelectorAll('.dnd-over').forEach(n => n.classList.remove('dnd-over'));
    node.classList.remove('dnd-dragging');
    if (moved) {
      const t = targetAt(e.clientX, e.clientY, ghost);
      ghost?.remove(); ghost = null;
      if (t && t._dndCtx === ctx) { ctx.picked = null; ctx.onDrop(t._dndKey, payload); }
    } else ctx.pick(payload, node);
  };
  node.addEventListener('pointerup', finish);
  node.addEventListener('pointercancel', () => { start = null; ghost?.remove(); ghost = null; node.classList.remove('dnd-dragging'); });
  node.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ctx.pick(payload, node); } });
}

function targetAt(x, y, ghost) {
  if (ghost) ghost.style.display = 'none';
  const hit = document.elementFromPoint(x, y);
  if (ghost) ghost.style.display = '';
  return hit ? hit.closest('[data-drop]') : null;
}

function dropTarget(node, key, ctx) {
  node.setAttribute('data-drop', '');
  node._dndKey = key; node._dndCtx = ctx;
  node.addEventListener('click', (e) => {
    if (!ctx.picked || e.target.closest('.dnd-source') && e.target.closest('.dnd-source') !== node) return;
    const payload = ctx.picked.payload; ctx.picked = null;
    ctx.onDrop(key, payload);
  });
}

/* Сортируемый список: перетаскивание элемента за ручку. onChange(newOrderIds). */
function sortable(list, axis, onChange) {
  let dragging = null;
  list.addEventListener('pointerdown', (e) => {
    const handle = e.target.closest('[data-handle]');
    if (!handle || !list.contains(handle) || e.button !== 0) return;
    dragging = handle.closest('[data-id]');
    dragging.classList.add('dnd-dragging');
    handle.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  list.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const items = [...list.children].filter(n => n !== dragging);
    const pos = axis === 'x' ? e.clientX : e.clientY;
    let before = null;
    for (const item of items) {
      const r = item.getBoundingClientRect();
      const mid = axis === 'x' ? r.left + r.width / 2 : r.top + r.height / 2;
      if (axis === 'x' && (e.clientY < r.top || e.clientY > r.bottom)) continue;
      if (pos < mid) { before = item; break; }
    }
    if (before !== dragging.nextSibling) list.insertBefore(dragging, before);
  });
  const end = () => {
    if (!dragging) return;
    dragging.classList.remove('dnd-dragging'); dragging = null;
    onChange([...list.children].map(n => n.dataset.id));
  };
  list.addEventListener('pointerup', end);
  list.addEventListener('pointercancel', end);
}

const GRADES = ['удовлетворительно', 'хорошо', 'замечательно'];
function gradePill(grade, fallback = 'нет оценки') {
  const cls = { 'удовлетворительно': 'pill-amber', 'хорошо': 'pill-blue', 'замечательно': 'pill-green' }[grade] || 'pill-gray';
  return el('span', { class: `pill ${cls}`, text: grade || fallback });
}
function fmtDate(value) {
  try { return new Date(value).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return value; }
}
function fmtNum(n) { return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100); }

/* Безопасный Markdown для описаний заданий и тестов.
   Весь текст сначала экранируется; создаются только известные теги, ссылки — только http(s)/mailto.
   Медиа не хранятся в системе: картинки, видео и аудио подключаются по внешним URL. */

const MD_ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const mdEscape = (s) => String(s).replace(/[&<>"']/g, (c) => MD_ESC[c]);
const mdUnescape = (s) => String(s).replace(/&(amp|lt|gt|quot|#39);/g, (m) => ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" })[m]);

function mdSafeUrl(escaped, { mail = false } = {}) {
  const raw = mdUnescape(escaped).trim();
  try {
    const url = new URL(raw);
    if (url.protocol === 'https:' || url.protocol === 'http:' || (mail && url.protocol === 'mailto:')) return mdEscape(url.href);
  } catch {}
  return null;
}

const MD_IMAGE = /\.(png|jpe?g|gif|webp|svg|avif|bmp)(\?.*)?$/i;
const MD_VIDEO = /\.(mp4|webm|ogv|mov)(\?.*)?$/i;
const MD_AUDIO = /\.(mp3|wav|ogg|oga|m4a|flac|aac)(\?.*)?$/i;

/* Встраиваемые видео только с известных площадок. */
function mdEmbed(href) {
  let url;
  try { url = new URL(mdUnescape(href)); } catch { return null; }
  const host = url.hostname.replace(/^www\.|^m\./, '');
  let id;
  if (host === 'youtube.com' && url.pathname === '/watch') id = url.searchParams.get('v');
  else if (host === 'youtu.be') id = url.pathname.slice(1);
  else if (host === 'youtube.com' && /^\/(embed|shorts)\//.test(url.pathname)) id = url.pathname.split('/')[2];
  if (id && /^[\w-]{6,20}$/.test(id)) return `https://www.youtube-nocookie.com/embed/${id}`;
  if (host === 'vimeo.com' && /^\/\d+$/.test(url.pathname)) return `https://player.vimeo.com/video${url.pathname}`;
  if (host === 'rutube.ru') { const m = url.pathname.match(/^\/video\/([0-9a-f]{32})/); if (m) return `https://rutube.ru/play/embed/${m[1]}`; }
  return null;
}

/* Медиа-блок по ссылке: картинка, видео, аудио, встраиваемый плеер. */
function mdMedia(href, alt = '') {
  const plain = mdUnescape(href);
  const embed = mdEmbed(href);
  if (embed) return `<div class="md-video"><iframe src="${mdEscape(embed)}" title="${alt || 'Видео'}" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" sandbox="allow-scripts allow-same-origin allow-presentation" allow="fullscreen; picture-in-picture" allowfullscreen></iframe></div>`;
  if (MD_VIDEO.test(plain)) return `<video class="md-media" controls preload="metadata" src="${href}"></video>`;
  if (MD_AUDIO.test(plain)) return `<audio class="md-audio" controls preload="none" src="${href}"></audio>`;
  return `<img class="md-media" src="${href}" alt="${alt}" loading="lazy" referrerpolicy="no-referrer">`;
}

function mdInline(text) {
  // Готовые фрагменты (код, ссылки, медиа) прячутся в метки, чтобы следующие замены их не трогали.
  const codes = [];
  const keep = (html) => { codes.push(html); return `\u0000${codes.length - 1}\u0000`; };
  let s = text.replace(/`([^`]+)`/g, (_, c) => keep(`<code>${c}</code>`));
  // ![alt](url) — медиа по ссылке
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt, url) => { const href = mdSafeUrl(url); return href ? keep(mdMedia(href, alt)) : m; });
  // [текст](url)
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, label, url) => {
    const href = mdSafeUrl(url, { mail: true });
    return href ? keep(`<a href="${href}" target="_blank" rel="noopener noreferrer nofollow">`) + label + keep('</a>') : m;
  });
  // голые ссылки
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<\u0000]+[^\s<.,;:!?)\]\u0000])/g, (m, pre, url) => {
    const href = mdSafeUrl(url);
    return href ? pre + keep(`<a href="${href}" target="_blank" rel="noopener noreferrer nofollow">${url}</a>`) : m;
  });
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/__(.+?)__/g, '<strong>$1</strong>')
    .replace(/(^|[^*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)/g, '$1<em>$2</em>').replace(/(^|[^\w])_(?!\s)(.+?)(?<!\s)_(?!\w)/g, '$1<em>$2</em>')
    .replace(/~~(.+?)~~/g, '<del>$1</del>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => codes[i]);
}

/* Строка целиком — ссылка на картинку/видео/аудио или поддерживаемый плеер. */
function mdIsMediaLine(line) {
  const m = line.trim().match(/^(https?:\/\/\S+)$/);
  if (!m) return false;
  const href = mdSafeUrl(m[1]), plain = mdUnescape(m[1]);
  return !!href && !!(mdEmbed(href) || MD_IMAGE.test(plain) || MD_VIDEO.test(plain) || MD_AUDIO.test(plain));
}

function renderMarkdown(source) {
  const lines = mdEscape(String(source || '').replace(/\r\n?/g, '\n')).split('\n');
  const out = [];
  let i = 0;
  const isTableSep = (l) => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(l);
  const cells = (l) => l.trim().replace(/^\||\|$/g, '').split('|').map(c => mdInline(c.trim()));
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    let m;
    if ((m = line.match(/^```\s*([\w-]*)\s*$/))) {
      const code = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) code.push(lines[i++]);
      i++;
      out.push(`<pre><code>${code.join('\n')}</code></pre>`);
      continue;
    }
    if ((m = line.match(/^(#{1,4})\s+(.+)$/))) { out.push(`<h${m[1].length + 1}>${mdInline(m[2])}</h${m[1].length + 1}>`); i++; continue; }
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { out.push('<hr>'); i++; continue; }
    // ссылка на медиа отдельной строкой — встроить
    if (mdIsMediaLine(line)) { out.push(mdMedia(mdSafeUrl(line.trim()))); i++; continue; }
    if (/^&gt;\s?/.test(line)) {
      const quote = [];
      while (i < lines.length && /^&gt;\s?/.test(lines[i])) quote.push(lines[i++].replace(/^&gt;\s?/, ''));
      out.push(`<blockquote>${renderMarkdownEscaped(quote)}</blockquote>`);
      continue;
    }
    if (/^\s*([-*+]|\d+[.)])\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]/.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
        let text = lines[i++].replace(/^\s*([-*+]|\d+[.)])\s+/, '');
        const task = text.match(/^\[([ xX])\]\s+(.*)$/);
        if (task) text = `${task[1] === ' ' ? '☐' : '☑'} ${task[2]}`;
        items.push(`<li>${mdInline(text)}</li>`);
      }
      out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`);
      continue;
    }
    if (line.includes('|') && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const headerCells = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      out.push(`<div class="table-wrap md-table"><table><thead><tr>${headerCells.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${headerCells.map((_, k) => `<td>${r[k] ?? ''}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|&gt;|\s*([-*+]|\d+[.)])\s+)/.test(lines[i]) && !(para.length && mdIsMediaLine(lines[i]))) para.push(lines[i++]);
    if (!para.length) para.push(lines[i++]);
    out.push(`<p>${para.map(mdInline).join('<br>')}</p>`);
  }
  return out.join('\n');
}

/* Вложенный рендер для цитат: строки уже экранированы. */
function renderMarkdownEscaped(lines) { return renderMarkdown(lines.map(mdUnescape).join('\n')); }

/* Краткий текст без разметки — для карточек и списков. */
function markdownPlain(source) {
  return String(source || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}(#{1,6}\s+|>\s?|[-*+]\s+|\d+[.)]\s+)/gm, '')
    .replace(/(\*\*|__|~~|`)/g, '').replace(/(^|\W)[*_](\S[^*_]*?)[*_](?=\W|$)/g, '$1$2')
    .replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
}

/* Элемент с отрендеренным Markdown (HTML собран только из экранированного текста). */
function markdownBlock(source, cls = '') {
  const box = el('div', { class: `prose md ${cls}`.trim(), html: renderMarkdown(source) });
  // Недоступное внешнее медиа заменяется понятной ссылкой вместо пустой рамки.
  box.querySelectorAll('img.md-media, video.md-media, audio.md-audio').forEach((node) => {
    node.addEventListener('error', () => {
      const src = node.getAttribute('src');
      node.replaceWith(el('a', { class: 'media-link', href: src, target: '_blank', rel: 'noopener noreferrer nofollow' },
        el('span', {}, 'Не удалось загрузить медиа по ссылке', el('small', { text: src }))));
    }, { once: true });
  });
  return box;
}

/* Отображение заданий ученику. renderTask(task, {value, onChange, readonly}) → элемент.
   Ответ ученика — объект; формат совпадает с проверкой на сервере (app/scenarios/tasks.py). */

const KIND_NAMES = {
  choice: 'Выбор ответа', matching: 'Сопоставление', fill: 'Заполнение полей', open: 'Свободный ответ',
  ordering: 'Упорядочивание', categorize: 'Классификация', selection: 'Выделение и обозначение',
  connecting: 'Соединение элементов', editing: 'Редактирование и исправление',
};
const VARIANT_NAMES = {
  choice: { single: 'Одиночный выбор', multiple: 'Множественный выбор', binary: 'Бинарный выбор', dropdown: 'Выпадающий список', multi_dropdown: 'Множественный выпадающий список' },
  matching: { columns: 'Две колонки', dropdown: 'Через выпадающие списки', drag: 'Перетаскиванием', lines: 'Соединительными линиями', multi: 'Множественные связи' },
  fill: { single: 'Одно текстовое поле', multi: 'Несколько полей', inline: 'Пропуски в тексте', inline_select: 'Пропуски с выбором', number: 'Числовое поле', formula: 'Формула', table: 'Заполнение таблицы' },
  open: { short: 'Краткий ответ', long: 'Развёрнутый ответ', number: 'Числовой ответ', rich: 'С форматированием', blocks: 'Несколько блоков' },
  ordering: { vertical: 'Вертикальный список', horizontal: 'Горизонтальный список', buttons: 'Кнопками', numbered: 'Пронумерованные позиции', slots: 'Через слоты' },
  categorize: { two: 'Две категории', many: 'Несколько категорий', drag: 'Перетаскиванием', dropdown: 'Выбор категории', multi: 'Множественное распределение' },
  selection: { one: 'Выбор одного элемента', many: 'Выбор нескольких', position: 'Выбор позиции', place_labels: 'Размещение меток', name: 'Подпись элементов', scheme: 'Элементы схемы' },
  connecting: { single: 'Одна связь', many: 'Несколько связей', hub: 'С общим узлом', network: 'Сеть связей', directed: 'Направленные связи' },
  editing: { rewrite: 'Редактирование текста', highlight: 'Выделение ошибок', replace: 'Замена элементов', delete: 'Удаление элементов', reorder: 'Исправление структуры', insert: 'Вставка пропущенного' },
};
const FIELD_RE = /\{\{([A-Za-z0-9_-]{1,40})\}\}/g;
const clone = (v) => JSON.parse(JSON.stringify(v ?? {}));

function renderTask(task, opts = {}) {
  const ctx = { task, data: task.data, ro: !!opts.readonly, st: clone(opts.value), emit: () => opts.onChange?.(clone(ctx.st)) };
  const body = el('div', { class: 'task-body' });
  const fn = WIDGETS[task.kind];
  try { body.append(fn ? fn(ctx) : el('p', { class: 'muted', text: 'Неизвестный тип задания' })); }
  catch (error) { console.error(error); body.append(el('p', { class: 'error-text', text: 'Не удалось отобразить задание' })); }
  return body;
}

/* ---------- 1. Выбор ответа ---------- */
function wChoice(c) {
  const { options } = c.data, v = c.task.variant;
  c.st.selected ??= [];
  const set = (i, on, single) => {
    c.st.selected = single ? (on ? [i] : []) : (on ? [...new Set([...c.st.selected, i])] : c.st.selected.filter(x => x !== i)).sort((a, b) => a - b);
    c.emit();
  };
  const name = 'c' + Math.random().toString(36).slice(2);
  if (v === 'dropdown') {
    return el('select', { disabled: c.ro, 'aria-label': 'Ответ', onchange: (e) => set(Number(e.target.value), e.target.value !== '', true) },
      el('option', { value: '', text: '— выберите —' }),
      options.map((o, i) => el('option', { value: i, text: o, selected: c.st.selected.includes(i) })));
  }
  if (v === 'multi_dropdown') return multiSelect(options, c.st.selected, c.ro, (sel) => { c.st.selected = sel; c.emit(); });
  if (v === 'binary') {
    const wrap = el('div', { class: 'binary', role: 'radiogroup' });
    const draw = () => wrap.replaceChildren(...options.map((o, i) => el('button', {
      type: 'button', class: 'binary-opt', disabled: c.ro, 'aria-pressed': c.st.selected.includes(i) ? 'true' : 'false', text: o,
      onclick: () => { set(i, true, true); draw(); },
    })));
    draw();
    return wrap;
  }
  const multi = v === 'multiple';
  return el('div', { class: 'opt-list' }, options.map((o, i) => el('label', { class: 'opt' },
    el('input', { type: multi ? 'checkbox' : 'radio', name, disabled: c.ro, checked: c.st.selected.includes(i),
      onchange: (e) => set(i, e.target.checked, !multi) }),
    el('span', { text: o }))));
}

function multiSelect(options, selected, ro, onChange) {
  let sel = [...selected];
  const chips = el('span', { class: 'ms-chips' });
  const draw = () => chips.replaceChildren(...(sel.length ? sel.map(i => el('span', { class: 'chip', text: options[i] })) : [el('span', { class: 'muted', text: '— выберите —' })]));
  const panel = el('div', { class: 'ms-panel' }, options.map((o, i) => el('label', { class: 'opt' },
    el('input', { type: 'checkbox', disabled: ro, checked: sel.includes(i), onchange: (e) => {
      sel = e.target.checked ? [...sel, i].sort((a, b) => a - b) : sel.filter(x => x !== i); draw(); onChange(sel);
    } }), el('span', { text: o }))));
  draw();
  return el('details', { class: 'ms' }, el('summary', { class: 'ms-summary' }, chips), panel);
}

/* ---------- 2. Сопоставление ---------- */
function wMatching(c) {
  const { left, right } = c.data, v = c.task.variant;
  c.st.pairs ??= [];
  const rightOf = (l) => c.st.pairs.filter(p => p[0] === l).map(p => p[1]);
  const setPair = (l, r) => { c.st.pairs = c.st.pairs.filter(p => p[0] !== l); if (r) c.st.pairs.push([l, r]); c.emit(); };
  const textOf = (list, id) => list.find(x => x.id === id)?.text ?? '';

  if (v === 'dropdown') {
    return el('div', { class: 'match-dd' }, left.map(l => el('div', { class: 'match-row' },
      el('span', { class: 'match-left', text: l.text }),
      el('select', { disabled: c.ro, 'aria-label': 'Соответствие для ' + l.text, onchange: (e) => setPair(l.id, e.target.value) },
        el('option', { value: '', text: '—' }), right.map(r => el('option', { value: r.id, text: r.text, selected: rightOf(l.id)[0] === r.id }))))));
  }
  if (v === 'multi') {
    return el('div', { class: 'table-wrap' }, el('table', { class: 'grid-table' },
      el('thead', {}, el('tr', {}, el('th', {}), right.map(r => el('th', { text: r.text })))),
      el('tbody', {}, left.map(l => el('tr', {}, el('th', { text: l.text }), right.map(r => el('td', {},
        el('input', { type: 'checkbox', disabled: c.ro, 'aria-label': `${l.text} — ${r.text}`, checked: rightOf(l.id).includes(r.id),
          onchange: (e) => {
            c.st.pairs = c.st.pairs.filter(p => !(p[0] === l.id && p[1] === r.id));
            if (e.target.checked) c.st.pairs.push([l.id, r.id]);
            c.emit();
          } }))))))));
  }
  if (v === 'drag') {
    const wrap = el('div', { class: 'match-drag' });
    const ctx = dndContext((key, rid) => {
      if (c.ro) return;
      c.st.pairs = c.st.pairs.filter(p => p[1] !== rid && (key === '__pool' || p[0] !== key));
      if (key !== '__pool') c.st.pairs.push([key, rid]);
      c.emit(); draw();
    });
    const draw = () => {
      const used = new Set(c.st.pairs.map(p => p[1]));
      const pool = el('div', { class: 'pool' }, right.filter(r => !used.has(r.id)).map(r => { const n = el('span', { class: 'chip', text: r.text }); if (!c.ro) dragSource(n, r.id, ctx); return n; }));
      const rows = left.map(l => {
        const slot = el('div', { class: 'slot' });
        const rid = rightOf(l.id)[0];
        if (rid) {
          const chip = el('span', { class: 'chip on', text: textOf(right, rid) });
          if (!c.ro) dragSource(chip, rid, ctx);
          slot.append(chip);
        } else slot.append(el('span', { class: 'muted', text: 'перетащите сюда' }));
        if (!c.ro) dropTarget(slot, l.id, ctx);
        return el('div', { class: 'match-row' }, el('span', { class: 'match-left', text: l.text }), slot);
      });
      const poolBox = el('div', { class: 'pool-box' }, el('div', { class: 'cap', text: 'Варианты' }), pool);
      if (!c.ro) dropTarget(poolBox, '__pool', ctx);
      wrap.replaceChildren(el('div', { class: 'match-rows' }, rows), poolBox);
    };
    draw();
    return wrap;
  }
  // columns / lines: щелчок слева, затем справа
  return linkBoard({
    left, right, pairs: () => c.st.pairs, ro: c.ro, lines: v === 'lines',
    toggle: (l, r) => {
      const exists = c.st.pairs.some(p => p[0] === l && p[1] === r);
      c.st.pairs = c.st.pairs.filter(p => p[0] !== l && p[1] !== r);
      if (!exists) c.st.pairs.push([l, r]);
      c.emit();
    },
  });
}

function linkBoard({ left, right, pairs, ro, lines, toggle }) {
  const board = el('div', { class: 'link-board' });
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'link-svg'); svg.setAttribute('aria-hidden', 'true');
  let active = null;
  const colL = el('div', { class: 'link-col' }), colR = el('div', { class: 'link-col' });
  const draw = () => {
    const ps = pairs();
    const numL = new Map(ps.map((p, i) => [p[0], i + 1]));
    const numR = new Map(ps.map((p, i) => [p[1], i + 1]));
    const item = (x, side) => {
      const n = (side === 'l' ? numL : numR).get(x.id);
      return el('button', { type: 'button', class: `link-item${active === x.id && side === 'l' ? ' active' : ''}${n ? ' linked' : ''}`, 'data-id': x.id, 'data-side': side, disabled: ro,
        onclick: () => {
          if (side === 'l') { active = active === x.id ? null : x.id; draw(); return; }
          if (!active) { toast('Сначала выберите элемент левой колонки'); return; }
          toggle(active, x.id); active = null; draw();
        } }, n && !lines ? el('span', { class: 'link-num', text: n }) : null, el('span', { text: x.text }));
    };
    colL.replaceChildren(...left.map(x => item(x, 'l')));
    colR.replaceChildren(...right.map(x => item(x, 'r')));
    requestAnimationFrame(drawLines);
  };
  const drawLines = () => {
    svg.replaceChildren();
    if (!lines) return;
    const box = board.getBoundingClientRect();
    svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
    for (const [l, r] of pairs()) {
      const a = colL.querySelector(`[data-id="${CSS.escape(l)}"]`), b = colR.querySelector(`[data-id="${CSS.escape(r)}"]`);
      if (!a || !b) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', ra.right - box.left); line.setAttribute('y1', ra.top + ra.height / 2 - box.top);
      line.setAttribute('x2', rb.left - box.left); line.setAttribute('y2', rb.top + rb.height / 2 - box.top);
      svg.append(line);
    }
  };
  board.append(colL, el('div', { class: 'link-gap' }), colR, svg);
  new ResizeObserver(() => drawLines()).observe(board);
  draw();
  if (!ro) board.prepend(el('p', { class: 'hint', text: 'Выберите элемент слева, затем соответствующий справа. Повторный выбор пары удаляет связь.' }));
  return board;
}

/* ---------- 3. Заполнение полей ---------- */
function wFill(c) {
  const v = c.task.variant, fields = c.data.fields;
  c.st.fields ??= {};
  const input = (f, extra = {}) => {
    const props = { type: 'text', disabled: c.ro, value: c.st.fields[f.id] ?? '', 'aria-label': f.label || 'Поле ' + f.id,
      oninput: (e) => { c.st.fields[f.id] = e.target.value; c.emit(); }, ...extra };
    if (v === 'number') Object.assign(props, { inputmode: 'decimal', placeholder: 'Число' });
    if (v === 'formula') Object.assign(props, { class: 'mono', placeholder: 'Например: (a+b)^2/2', spellcheck: 'false' });
    if (v === 'inline_select') {
      return el('select', { class: 'inline-ctl', disabled: c.ro, 'aria-label': 'Пропуск ' + f.id, onchange: (e) => { c.st.fields[f.id] = e.target.value; c.emit(); } },
        el('option', { value: '', text: '—' }), f.options.map(o => el('option', { value: o, text: o, selected: c.st.fields[f.id] === o })));
    }
    return el('input', props);
  };
  const withBlanks = (text, cls) => {
    const parts = []; let last = 0;
    for (const m of text.matchAll(FIELD_RE)) {
      parts.push(text.slice(last, m.index));
      const f = fields.find(x => x.id === m[1]);
      parts.push(f ? input(f, { class: cls }) : m[0]);
      last = m.index + m[0].length;
    }
    parts.push(text.slice(last));
    return parts;
  };
  if (v === 'inline' || v === 'inline_select') return el('div', { class: 'inline-text' }, withBlanks(c.data.text, 'inline-ctl'));
  if (v === 'table') {
    return el('div', { class: 'table-wrap' }, el('table', { class: 'grid-table' },
      el('thead', {}, el('tr', {}, c.data.columns.map(h => el('th', { text: h })))),
      el('tbody', {}, c.data.rows.map(row => el('tr', {}, row.map(cell => el('td', {}, withBlanks(cell, 'cell-input'))))))));
  }
  return el('div', { class: 'fields' }, fields.map(f => el('label', {}, f.label || (fields.length > 1 ? 'Поле ' + f.id : 'Ответ'), input(f))));
}

/* ---------- 4. Свободный ответ ---------- */
function wOpen(c) {
  const v = c.task.variant, ph = c.data.placeholder || '';
  if (v === 'short') return el('input', { type: 'text', disabled: c.ro, value: c.st.text ?? '', placeholder: ph, 'aria-label': 'Ответ', oninput: (e) => { c.st.text = e.target.value; c.emit(); } });
  if (v === 'number') {
    const err = el('div', { class: 'error-text' });
    return el('div', {}, el('input', { type: 'text', inputmode: 'decimal', disabled: c.ro, value: c.st.text ?? '', placeholder: ph || 'Число', 'aria-label': 'Числовой ответ',
      oninput: (e) => {
        const ok = /^\s*-?\d+([.,]\d+)?\s*$/.test(e.target.value) || e.target.value === '';
        err.textContent = ok ? '' : 'Введите число, например 12 или 3,5';
        c.st.text = e.target.value; c.emit();
      } }), err);
  }
  if (v === 'long') return el('textarea', { rows: 6, disabled: c.ro, placeholder: ph, 'aria-label': 'Ответ', value: c.st.text ?? '', oninput: (e) => { c.st.text = e.target.value; c.emit(); } });
  if (v === 'rich') {
    // HTML очищается сервером при сохранении попытки; здесь показывается введённое учеником или очищенное сервером.
    const area = el('div', { class: 'rich-area', contenteditable: c.ro ? 'false' : 'true', role: 'textbox', 'aria-multiline': 'true', 'aria-label': 'Ответ с форматированием', html: c.st.html || '' });
    area.addEventListener('input', () => { c.st.html = area.innerHTML; c.emit(); });
    const cmd = (name, label, tip) => el('button', { type: 'button', class: 'rich-btn', 'aria-label': tip, title: tip, disabled: c.ro,
      onmousedown: (e) => e.preventDefault(), onclick: () => { document.execCommand(name); area.focus(); c.st.html = area.innerHTML; c.emit(); } }, el('span', { html: label }));
    return el('div', { class: 'rich' }, c.ro ? null : el('div', { class: 'rich-bar' },
      cmd('bold', '<b>Ж</b>', 'Жирный'), cmd('italic', '<i>К</i>', 'Курсив'), cmd('underline', '<u>П</u>', 'Подчёркнутый'),
      cmd('insertUnorderedList', '• —', 'Маркированный список'), cmd('insertOrderedList', '1.', 'Нумерованный список')), area);
  }
  // blocks
  c.st.blocks ??= [''];
  const max = c.data.max_blocks || 5;
  const wrap = el('div', { class: 'blocks' });
  const draw = () => wrap.replaceChildren(...c.st.blocks.map((b, i) => el('div', { class: 'block-row' },
    el('label', {}, `Блок ${i + 1}`, el('textarea', { rows: 3, disabled: c.ro, value: b, placeholder: ph, oninput: (e) => { c.st.blocks[i] = e.target.value; c.emit(); } })),
    c.ro || c.st.blocks.length < 2 ? null : ibtn({ icon: 'trash', tip: 'Удалить блок', danger: true, onclick: () => { c.st.blocks.splice(i, 1); c.emit(); draw(); } }))),
    c.ro || c.st.blocks.length >= max ? '' : el('button', { type: 'button', class: 'btn small ghost', onclick: () => { c.st.blocks.push(''); c.emit(); draw(); } }, icon('add'), 'Добавить блок'));
  draw();
  return wrap;
}

/* ---------- 5. Упорядочивание ---------- */
function orderWidget(c, items, variant) {
  const byId = new Map(items.map(i => [i.id, i]));
  if (!Array.isArray(c.st.order) || c.st.order.length !== items.length || !c.st.order.every(id => byId.has(id))) {
    // Начальный (перемешанный) порядок не считается ответом, пока ученик его не изменит.
    c.st.order = variant === 'slots' || variant === 'numbered' ? (c.st.order || []).filter(id => byId.has(id)) : items.map(i => i.id);
  }
  if (variant === 'numbered') {
    c.st.nums ??= {};
    const n = items.length;
    const update = () => {
      const assigned = items.filter(i => c.st.nums[i.id]);
      c.st.order = assigned.length === n ? [...items].sort((a, b) => c.st.nums[a.id] - c.st.nums[b.id]).map(i => i.id) : [];
      c.emit();
    };
    return el('div', { class: 'opt-list' }, items.map(i => el('div', { class: 'num-row' },
      el('select', { class: 'num-select', disabled: c.ro, 'aria-label': 'Позиция для ' + i.text, onchange: (e) => { c.st.nums[i.id] = Number(e.target.value) || 0; update(); } },
        el('option', { value: '', text: '№' }), Array.from({ length: n }, (_, k) => el('option', { value: k + 1, text: k + 1, selected: c.st.nums[i.id] === k + 1 }))),
      el('span', { text: i.text }))));
  }
  if (variant === 'slots') {
    const wrap = el('div', { class: 'slots-wrap' });
    const ctx = dndContext(() => {});
    const draw = () => {
      const placed = new Set(c.st.order.filter(Boolean));
      const slots = items.map((_, k) => {
        const id = c.st.order[k];
        const slot = el('div', { class: 'slot numbered' }, el('span', { class: 'slot-num', text: k + 1 }));
        if (id) { const chip = el('span', { class: 'chip on', text: byId.get(id).text }); if (!c.ro) dragSource(chip, id, ctx); slot.append(chip); }
        if (!c.ro) dropTarget(slot, k, ctx);
        return slot;
      });
      const pool = el('div', { class: 'pool' }, items.filter(i => !placed.has(i.id)).map(i => { const n = el('span', { class: 'chip', text: i.text }); if (!c.ro) dragSource(n, i.id, ctx); return n; }));
      const poolBox = el('div', { class: 'pool-box' }, el('div', { class: 'cap', text: 'Элементы' }), pool);
      if (!c.ro) dropTarget(poolBox, 'pool', ctx);
      wrap.replaceChildren(el('div', { class: 'slots' }, slots), poolBox);
    };
    ctx.onDrop = (key, id) => {
      const order = Array.from({ length: items.length }, (_, k) => c.st.order[k] || null).map(x => (x === id ? null : x));
      if (key !== 'pool') order[key] = id;
      c.st.order = order;
      c.emit(); draw();
    };
    draw();
    return wrap;
  }
  const horizontal = variant === 'horizontal';
  const list = el('ol', { class: `sort-list${horizontal ? ' horizontal' : ''}` });
  const move = (idx, delta) => {
    const j = idx + delta;
    if (j < 0 || j >= c.st.order.length) return;
    [c.st.order[idx], c.st.order[j]] = [c.st.order[j], c.st.order[idx]];
    c.emit(); draw();
  };
  const draw = () => list.replaceChildren(...c.st.order.map((id, idx) => el('li', { class: 'sort-item', 'data-id': id },
    variant === 'buttons' || c.ro ? null : el('span', { class: 'grip', 'data-handle': '', 'aria-hidden': 'true', html: ICONS.grip }),
    el('span', { class: 'sort-text', text: byId.get(id).text }),
    c.ro ? null : el('span', { class: 'sort-btns' },
      ibtn({ icon: horizontal ? 'left' : 'up', tip: horizontal ? 'Левее' : 'Выше', onclick: () => move(idx, -1), disabled: idx === 0 }),
      ibtn({ icon: horizontal ? 'right' : 'down', tip: horizontal ? 'Правее' : 'Ниже', onclick: () => move(idx, 1), disabled: idx === c.st.order.length - 1 })))));
  if (!c.ro && variant !== 'buttons') sortable(list, horizontal ? 'x' : 'y', (order) => { c.st.order = order; c.emit(); draw(); });
  draw();
  return list;
}
const wOrdering = (c) => orderWidget(c, c.data.items, c.task.variant);

/* ---------- 6. Классификация ---------- */
function wCategorize(c) {
  const { items, categories } = c.data, v = c.task.variant;
  c.st.map ??= {};
  const catsOf = (id) => c.st.map[id] || [];
  if (v === 'dropdown') {
    return el('div', { class: 'match-dd' }, items.map(i => el('div', { class: 'match-row' }, el('span', { class: 'match-left', text: i.text }),
      el('select', { disabled: c.ro, 'aria-label': 'Категория для ' + i.text, onchange: (e) => { c.st.map[i.id] = e.target.value ? [e.target.value] : []; c.emit(); } },
        el('option', { value: '', text: '—' }), categories.map(k => el('option', { value: k.id, text: k.text, selected: catsOf(i.id)[0] === k.id }))))));
  }
  if (v === 'multi') {
    return el('div', { class: 'table-wrap' }, el('table', { class: 'grid-table' },
      el('thead', {}, el('tr', {}, el('th', {}), categories.map(k => el('th', { text: k.text })))),
      el('tbody', {}, items.map(i => el('tr', {}, el('th', { text: i.text }), categories.map(k => el('td', {},
        el('input', { type: 'checkbox', disabled: c.ro, 'aria-label': `${i.text} — ${k.text}`, checked: catsOf(i.id).includes(k.id),
          onchange: (e) => { const s = new Set(catsOf(i.id)); e.target.checked ? s.add(k.id) : s.delete(k.id); c.st.map[i.id] = [...s].sort(); c.emit(); } }))))))));
  }
  const wrap = el('div', { class: 'cat-wrap' });
  const ctx = dndContext((key, id) => { if (c.ro) return; c.st.map[id] = key === 'pool' ? [] : [key]; c.emit(); draw(); });
  const chip = (i, on) => { const n = el('span', { class: `chip${on ? ' on' : ''}`, text: i.text }); if (!c.ro) dragSource(n, i.id, ctx); return n; };
  const draw = () => {
    const pool = el('div', { class: 'pool-box' }, el('div', { class: 'cap', text: 'Элементы' }),
      el('div', { class: 'pool' }, items.filter(i => !catsOf(i.id).length).map(i => chip(i, false))));
    if (!c.ro) dropTarget(pool, 'pool', ctx);
    const boxes = categories.map(k => {
      const box = el('div', { class: 'cat-box' }, el('div', { class: 'cap', text: k.text }),
        el('div', { class: 'pool' }, items.filter(i => catsOf(i.id).includes(k.id)).map(i => chip(i, true))));
      if (!c.ro) dropTarget(box, k.id, ctx);
      return box;
    });
    wrap.replaceChildren(pool, el('div', { class: 'cat-grid' }, boxes));
  };
  draw();
  return wrap;
}

/* ---------- 7. Выделение и обозначение ---------- */
function canvasBox(data, children) {
  const box = el('div', { class: 'canvas' + (data.image ? ' has-image' : '') });
  if (data.image) box.append(el('img', { src: data.image, alt: '', draggable: 'false', referrerpolicy: 'no-referrer' }));
  box.append(...children);
  return box;
}
const at = (x, y) => ({ left: x + '%', top: y + '%' });

function wSelection(c) {
  const v = c.task.variant, d = c.data;
  if (v === 'position') {
    c.st.point ??= null;
    const marker = el('span', { class: 'pos-marker', hidden: !c.st.point });
    const place = () => { if (c.st.point) { Object.assign(marker.style, at(c.st.point.x, c.st.point.y)); marker.hidden = false; } };
    const box = canvasBox(d, [marker]);
    box.classList.add('clickable');
    if (!c.ro) box.addEventListener('click', (e) => {
      const r = box.getBoundingClientRect();
      c.st.point = { x: Math.round((e.clientX - r.left) / r.width * 1000) / 10, y: Math.round((e.clientY - r.top) / r.height * 1000) / 10 };
      place(); c.emit();
    });
    place();
    return el('div', {}, c.ro ? null : el('p', { class: 'hint', text: 'Нажмите на нужное место рабочей области.' }), box);
  }
  const elements = d.elements;
  const nums = new Map(elements.map((e, i) => [e.id, i + 1]));
  if (v === 'name') {
    c.st.names ??= {};
    return el('div', { class: 'stack-sm' }, canvasBox(d, elements.map(e => el('span', { class: 'marker', style: at(e.x, e.y), text: nums.get(e.id) }))),
      el('div', { class: 'fields two' }, elements.map(e => el('label', {}, `Элемент ${nums.get(e.id)}`,
        el('input', { type: 'text', disabled: c.ro, value: c.st.names[e.id] ?? '', oninput: (ev) => { c.st.names[e.id] = ev.target.value; c.emit(); } })))));
  }
  if (v === 'place_labels') {
    c.st.map ??= {};
    const wrap = el('div', { class: 'stack-sm' });
    const ctx = dndContext((key, label) => {
      if (c.ro) return;
      for (const k of Object.keys(c.st.map)) if (c.st.map[k] === label) delete c.st.map[k];
      if (key !== 'pool') c.st.map[key] = label;
      c.emit(); draw();
    });
    const draw = () => {
      const used = new Set(Object.values(c.st.map));
      const spots = elements.map(e => {
        const label = c.st.map[e.id];
        const spot = el('div', { class: 'label-spot' + (label ? ' filled' : ''), style: at(e.x, e.y) });
        if (label) { const chip = el('span', { class: 'chip on', text: label }); if (!c.ro) dragSource(chip, label, ctx); spot.append(chip); }
        else spot.append(el('span', { class: 'marker', text: nums.get(e.id) }));
        if (!c.ro) dropTarget(spot, e.id, ctx);
        return spot;
      });
      const pool = el('div', { class: 'pool-box' }, el('div', { class: 'cap', text: 'Метки' }),
        el('div', { class: 'pool' }, d.labels.filter(l => !used.has(l)).map(l => { const n = el('span', { class: 'chip', text: l }); if (!c.ro) dragSource(n, l, ctx); return n; })));
      if (!c.ro) dropTarget(pool, 'pool', ctx);
      wrap.replaceChildren(canvasBox(d, spots), pool);
    };
    draw();
    return wrap;
  }
  // one / many / scheme
  c.st.selected ??= [];
  const single = v === 'one';
  const box = canvasBox(d, []);
  if (v === 'scheme') box.append(edgesSvg(elements, d.edges || [], true));
  const draw = () => {
    box.querySelectorAll('.node').forEach(n => n.remove());
    box.append(...elements.map(e => el('button', { type: 'button', class: 'node' + (v === 'scheme' ? ' block' : '') + (c.st.selected.includes(e.id) ? ' selected' : ''),
      style: at(e.x, e.y), disabled: c.ro, 'aria-pressed': c.st.selected.includes(e.id) ? 'true' : 'false', text: e.text,
      onclick: () => {
        const on = c.st.selected.includes(e.id);
        c.st.selected = single ? (on ? [] : [e.id]) : (on ? c.st.selected.filter(x => x !== e.id) : [...c.st.selected, e.id]);
        c.emit(); draw();
      } })));
  };
  draw();
  return box;
}

function edgesSvg(nodes, edges, directed) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'edge-svg'); svg.setAttribute('viewBox', '0 0 100 100'); svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  const pos = new Map(nodes.map(n => [n.id, n]));
  for (const [a, b] of edges) {
    const p = pos.get(a), q = pos.get(b);
    if (!p || !q) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', p.x); line.setAttribute('y1', p.y); line.setAttribute('x2', q.x); line.setAttribute('y2', q.y);
    line.setAttribute('vector-effect', 'non-scaling-stroke');
    svg.append(line);
    if (directed) {
      // стрелка в 65% пути, чтобы не пряталась под узлом
      const mx = p.x + (q.x - p.x) * .65, my = p.y + (q.y - p.y) * .65;
      const head = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      head.setAttribute('cx', mx); head.setAttribute('cy', my); head.setAttribute('r', '1.1'); head.setAttribute('class', 'arrow-dot');
      svg.append(head);
    }
  }
  return svg;
}

/* ---------- 8. Соединение элементов ---------- */
function wConnecting(c) {
  const d = c.data, directed = !!d.directed, max = d.max_edges || Infinity;
  c.st.edges ??= [];
  let active = null;
  const wrap = el('div', { class: 'stack-sm' });
  const label = new Map(d.nodes.map(n => [n.id, n.text]));
  const same = (e, a, b) => (e[0] === a && e[1] === b) || (!directed && e[0] === b && e[1] === a);
  const draw = () => {
    const box = canvasBox({}, [edgesSvg(d.nodes, c.st.edges, directed)]);
    box.append(...d.nodes.map(n => el('button', { type: 'button', class: 'node' + (active === n.id ? ' active' : ''), style: at(n.x, n.y), disabled: c.ro, text: n.text,
      'aria-pressed': active === n.id ? 'true' : 'false',
      onclick: () => {
        if (!active) { active = n.id; draw(); return; }
        if (active === n.id) { active = null; draw(); return; }
        const exists = c.st.edges.some(e => same(e, active, n.id));
        if (exists) c.st.edges = c.st.edges.filter(e => !same(e, active, n.id));
        else if (c.st.edges.length >= max) c.st.edges = [[active, n.id]];
        else c.st.edges.push([active, n.id]);
        active = null; c.emit(); draw();
      } })));
    const list = el('ul', { class: 'edge-list' }, c.st.edges.map(e => el('li', {},
      el('span', { text: `${label.get(e[0])} ${directed ? '→' : '—'} ${label.get(e[1])}` }),
      c.ro ? null : ibtn({ icon: 'x', tip: 'Удалить связь', danger: true, onclick: () => { c.st.edges = c.st.edges.filter(x => x !== e); c.emit(); draw(); } }))));
    wrap.replaceChildren(c.ro ? '' : el('p', { class: 'hint', text: directed ? 'Нажмите узел-начало, затем узел-конец. Повторное соединение удаляет связь.' : 'Нажмите два узла, чтобы соединить их. Повторное соединение удаляет связь.' }),
      box, c.st.edges.length ? list : el('p', { class: 'muted small', text: 'Связей пока нет' }));
  };
  draw();
  return wrap;
}

/* ---------- 9. Редактирование ---------- */
function wEditing(c) {
  const v = c.task.variant, d = c.data;
  if (v === 'reorder') return orderWidget(c, d.lines, 'vertical');
  if (v === 'rewrite') {
    c.st.text ??= d.text;
    return el('textarea', { rows: 5, disabled: c.ro, value: c.st.text, 'aria-label': 'Исправьте текст', oninput: (e) => { c.st.text = e.target.value; c.emit(); } });
  }
  const words = d.tokens;
  const wrap = el('div', { class: 'tokens' });
  if (v === 'highlight' || v === 'delete') {
    c.st.indices ??= [];
    const cls = v === 'highlight' ? 'hl' : 'struck';
    const draw = () => wrap.replaceChildren(...words.map((w, i) => el('button', { type: 'button', class: 'token' + (c.st.indices.includes(i) ? ' ' + cls : ''), disabled: c.ro,
      'aria-pressed': c.st.indices.includes(i) ? 'true' : 'false', text: w,
      onclick: () => { c.st.indices = c.st.indices.includes(i) ? c.st.indices.filter(x => x !== i) : [...c.st.indices, i].sort((a, b) => a - b); c.emit(); draw(); } })));
    draw();
    return el('div', {}, c.ro ? null : el('p', { class: 'hint', text: v === 'highlight' ? 'Нажмите на слова с ошибками.' : 'Нажмите на лишние слова, чтобы удалить их.' }), wrap);
  }
  if (v === 'replace') {
    c.st.replacements ??= {};
    let editing = null;
    const draw = () => wrap.replaceChildren(...words.map((w, i) => {
      const key = String(i), rep = c.st.replacements[key];
      if (editing === i) {
        const inp = el('input', { type: 'text', class: 'token-input', value: rep ?? w, 'aria-label': 'Замена для ' + w,
          onkeydown: (e) => { if (e.key === 'Enter') inp.blur(); if (e.key === 'Escape') { editing = null; draw(); } },
          onblur: () => { const val = inp.value.trim(); if (!val || val === w) delete c.st.replacements[key]; else c.st.replacements[key] = val; editing = null; c.emit(); draw(); } });
        setTimeout(() => inp.focus(), 0);
        return inp;
      }
      return el('button', { type: 'button', class: 'token' + (rep ? ' replaced' : ''), disabled: c.ro, title: rep ? 'Было: ' + w : 'Заменить',
        onclick: () => { editing = i; draw(); } }, rep ? el('span', {}, el('s', { class: 'muted', text: w }), ' ', rep) : w);
    }));
    draw();
    return el('div', {}, c.ro ? null : el('p', { class: 'hint', text: 'Нажмите на слово, чтобы заменить его.' }), wrap);
  }
  // insert
  c.st.inserts ??= {};
  let editing = null;
  const gap = (i) => {
    const key = String(i), val = c.st.inserts[key];
    if (editing === i) {
      const inp = el('input', { type: 'text', class: 'token-input', value: val ?? '', 'aria-label': 'Вставка',
        onkeydown: (e) => { if (e.key === 'Enter') inp.blur(); },
        onblur: () => { const t = inp.value.trim(); t ? (c.st.inserts[key] = t) : delete c.st.inserts[key]; editing = null; c.emit(); draw(); } });
      setTimeout(() => inp.focus(), 0);
      return inp;
    }
    if (val) return el('button', { type: 'button', class: 'token inserted', disabled: c.ro, text: val, onclick: () => { editing = i; draw(); } });
    return c.ro ? '' : el('button', { type: 'button', class: 'gap', 'aria-label': 'Вставить здесь', title: 'Вставить здесь', onclick: () => { editing = i; draw(); } }, '+');
  };
  const draw = () => { const parts = []; for (let i = 0; i <= words.length; i++) { parts.push(gap(i)); if (i < words.length) parts.push(el('span', { class: 'token static', text: words[i] })); } wrap.replaceChildren(...parts); };
  draw();
  return el('div', {}, c.ro ? null : el('p', { class: 'hint', text: 'Нажмите «+» между словами, чтобы вставить пропущенное.' }), wrap);
}

const WIDGETS = { choice: wChoice, matching: wMatching, fill: wFill, open: wOpen, ordering: wOrdering, categorize: wCategorize, selection: wSelection, connecting: wConnecting, editing: wEditing };

/* Описание правильного ответа (для репетитора). */
function describeAnswer(task) {
  const a = task.answer, d = task.data;
  if (!a) return 'Проверяет репетитор';
  const t = (list, id) => list?.find(x => x.id === id)?.text ?? id;
  switch (task.kind) {
    case 'choice': return a.correct.map(i => d.options[i]).join('; ');
    case 'matching': return a.pairs.map(([l, r]) => `${t(d.left, l)} → ${t(d.right, r)}`).join('; ');
    case 'fill': return Object.entries(a.fields).map(([k, v]) => `${k}: ${v.join(' / ')}`).join('; ') + (a.tolerance ? ` (допуск ${a.tolerance})` : '');
    case 'open': return a.accepted ? a.accepted.join(' / ') : `${a.value}${a.tolerance ? ' ± ' + a.tolerance : ''}`;
    case 'ordering': return a.order.map(id => t(d.items, id)).join(' → ');
    case 'categorize': return Object.entries(a.map).filter(([, v]) => v.length).map(([k, v]) => `${t(d.items, k)}: ${v.map(x => t(d.categories, x)).join(', ')}`).join('; ');
    case 'selection':
      if (a.selected) return a.selected.map(id => t(d.elements, id)).join(', ');
      if (a.region) return `область x ${a.region.x}–${a.region.x + a.region.w}%, y ${a.region.y}–${a.region.y + a.region.h}%`;
      if (a.map) return Object.entries(a.map).map(([k, v]) => `${t(d.elements, k)}: ${v}`).join('; ');
      return Object.entries(a.names).map(([k, v]) => `${t(d.elements, k)}: ${v.join(' / ')}`).join('; ');
    case 'connecting': return a.edges.map(([x, y]) => `${t(d.nodes, x)} ${d.directed ? '→' : '—'} ${t(d.nodes, y)}`).join('; ');
    case 'editing':
      if (a.order) return a.order.map(id => t(d.lines, id)).join(' / ');
      if (a.indices) return a.indices.map(i => d.tokens[i]).join(', ');
      return a.text;
  }
  return '';
}

/* Конструктор заданий. Каждый редактор возвращает {node, collect()} → {data, answer}.
   Правильный ответ везде необязателен: без него задание проверяет репетитор. */

const lines = (text) => String(text || '').split('\n').map(s => s.trim()).filter(Boolean);
const alts = (text) => String(text || '').split('|').map(s => s.trim()).filter(Boolean);
const field = (label, control, hint) => el('label', {}, label, control, hint ? el('span', { class: 'hint', text: hint }) : null);
const ta = (value, rows = 4, extra = {}) => el('textarea', { rows, value: value ?? '', ...extra });
const inp = (value, extra = {}) => el('input', { type: 'text', value: value ?? '', ...extra });
/* Панель вставки Markdown: оборачивает выделение или вставляет шаблон в позицию курсора. */
function mdToolbar(area) {
  const wrap = (before, after = before, placeholder = 'текст') => () => {
    const { selectionStart: a, selectionEnd: b, value } = area;
    const sel = value.slice(a, b) || placeholder;
    area.setRangeText(before + sel + after, a, b, 'end');
    area.setSelectionRange(a + before.length, a + before.length + sel.length);
    area.focus(); area.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const line = (prefix) => () => {
    const a = area.selectionStart, start = area.value.lastIndexOf('\n', a - 1) + 1;
    area.setRangeText(prefix, start, start, 'end'); area.focus(); area.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const media = (label) => async () => {
    const a = area.selectionStart, end = area.selectionEnd;
    const url = await askText(label === 'изображение' ? 'Изображение по ссылке' : 'Видео или аудио по ссылке', {
      placeholder: 'https://…',
      validate: (v) => (/^https?:\/\/\S+$/i.test(v) ? '' : 'Ссылка должна начинаться с http:// или https://'),
    }, { message: label === 'изображение' ? 'Файл не загружается в систему — ученик увидит картинку по этой ссылке.' : 'YouTube, Vimeo, RuTube или прямая ссылка на mp4/webm/mp3. Файл не хранится в системе.' });
    if (!url) { area.focus(); return; }
    area.setSelectionRange(a, end);
    const text = (a && area.value[a - 1] !== '\n' ? '\n' : '') + (label === 'изображение' ? `![](${url.trim()})` : url.trim()) + '\n';
    area.setRangeText(text, a, area.selectionEnd, 'end'); area.focus(); area.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const b = (labelHtml, tip, fn) => el('button', { type: 'button', class: 'rich-btn', 'aria-label': tip, title: tip, onmousedown: (e) => e.preventDefault(), onclick: fn }, el('span', { html: labelHtml }));
  return el('div', { class: 'rich-bar md-bar' },
    b('<b>Ж</b>', 'Жирный', wrap('**')), b('<i>К</i>', 'Курсив', wrap('*')), b('<s>З</s>', 'Зачёркнутый', wrap('~~')),
    b('H', 'Заголовок', line('### ')), b('• —', 'Список', line('- ')), b('1.', 'Нумерованный список', line('1. ')),
    b('❝', 'Цитата', line('> ')), b('&lt;/&gt;', 'Код', wrap('`')),
    b('Ссылка', 'Ссылка', wrap('[', '](https://)', 'текст ссылки')),
    b('Изобр.', 'Изображение по ссылке', media('изображение')), b('Видео', 'Видео или аудио по ссылке (YouTube, Vimeo, RuTube, mp4, mp3…)', media('видео или аудио')));
}

const autoBox =(on, text = 'Проверять автоматически') => { const box = el('input', { type: 'checkbox', checked: on }); return { box, node: el('label', { class: 'check' }, box, text) }; };

/* ---------- 1. Выбор ---------- */
function edChoice(variant, task) {
  const binary = variant === 'binary', single = ['single', 'binary', 'dropdown'].includes(variant);
  let rows = (task.data?.options || (binary ? ['Да', 'Нет'] : ['', ''])).map((t, i) => ({ text: t, ok: !!task.answer?.correct?.includes(i) }));
  if (binary) rows = rows.slice(0, 2);
  const list = el('div', { class: 'ed-rows' });
  const name = 'ok' + Math.random().toString(36).slice(2);
  const draw = () => list.replaceChildren(...rows.map((r, i) => el('div', { class: 'list-row' },
    el('input', { type: single ? 'radio' : 'checkbox', name, checked: r.ok, 'aria-label': 'Правильный вариант', title: 'Правильный вариант',
      onchange: (e) => { if (single) rows.forEach(x => (x.ok = false)); r.ok = e.target.checked; } }),
    inp(r.text, { placeholder: `Вариант ${i + 1}`, oninput: (e) => (r.text = e.target.value) }),
    binary || rows.length <= 2 ? null : ibtn({ icon: 'trash', tip: 'Удалить вариант', danger: true, onclick: () => { rows.splice(i, 1); draw(); } }))),
    binary ? '' : el('button', { type: 'button', class: 'btn small ghost', onclick: () => { rows.push({ text: '', ok: false }); draw(); } }, icon('add'), 'Вариант'));
  draw();
  return {
    node: el('div', {}, el('p', { class: 'hint', text: 'Отметьте правильный вариант (необязательно).' }), list),
    collect: () => {
      const correct = rows.map((r, i) => (r.ok ? i : -1)).filter(i => i >= 0);
      return { data: { options: rows.map(r => r.text) }, answer: correct.length ? { correct } : null };
    },
  };
}

/* ---------- 2. Сопоставление ---------- */
function edMatching(variant, task) {
  const L = ta((task.data?.left || []).map(x => x.text).join('\n'), 4, { placeholder: 'Элемент слева\nпо одному в строке' });
  const R = ta((task.data?.right || []).map(x => x.text).join('\n'), 4, { placeholder: 'Элемент справа\nпо одному в строке' });
  const leftIds = (task.data?.left || []).map(x => x.id), rightIds = (task.data?.right || []).map(x => x.id);
  let checks = new Set((task.answer?.pairs || []).map(([l, r]) => `${leftIds.indexOf(l)}:${rightIds.indexOf(r)}`));
  const grid = el('div', { class: 'table-wrap' });
  const drawGrid = () => {
    const ls = lines(L.value), rs = lines(R.value);
    if (!ls.length || !rs.length) { grid.replaceChildren(el('p', { class: 'muted small pad', text: 'Заполните обе колонки' })); return; }
    grid.replaceChildren(el('table', { class: 'grid-table' },
      el('thead', {}, el('tr', {}, el('th', {}), rs.map(r => el('th', { text: r })))),
      el('tbody', {}, ls.map((l, i) => el('tr', {}, el('th', { text: l }), rs.map((_, j) => el('td', {},
        el('input', { type: 'checkbox', checked: checks.has(`${i}:${j}`), 'aria-label': `${l} — ${rs[j]}`, onchange: (e) => {
          if (e.target.checked && variant !== 'multi') checks = new Set([...checks].filter(k => !k.startsWith(i + ':')));
          e.target.checked ? checks.add(`${i}:${j}`) : checks.delete(`${i}:${j}`);
          drawGrid();
        } }))))))));
  };
  L.addEventListener('input', drawGrid); R.addEventListener('input', drawGrid);
  drawGrid();
  return {
    node: el('div', { class: 'stack-sm' }, el('div', { class: 'grid2' }, field('Левая колонка', L), field('Правая колонка', R, 'Можно добавить лишние варианты')),
      el('div', { class: 'hint', text: variant === 'multi' ? 'Правильные связи (несколько на элемент):' : 'Правильные связи (по одной на элемент слева, необязательно):' }), grid),
    collect: () => {
      const ls = lines(L.value), rs = lines(R.value);
      const pairs = [...checks].map(k => k.split(':').map(Number)).filter(([i, j]) => i < ls.length && j < rs.length).map(([i, j]) => ['L' + (i + 1), 'R' + (j + 1)]);
      return { data: { left: ls.map((t, i) => ({ id: 'L' + (i + 1), text: t })), right: rs.map((t, i) => ({ id: 'R' + (i + 1), text: t })) }, answer: pairs.length ? { pairs } : null };
    },
  };
}

/* ---------- 3. Заполнение полей ---------- */
const BLANK_RE = /\[\[([^\]]*)\]\]/g;
function edFill(variant, task) {
  const d = task.data || {}, a = task.answer?.fields || {};
  if (variant === 'inline' || variant === 'inline_select' || variant === 'table') {
    const toSyntax = (text) => String(text || '').replace(FIELD_RE, (_, id) => {
      const f = (d.fields || []).find(x => x.id === id) || {};
      if (variant === 'inline_select') return '[[' + (f.options || []).map(o => ((a[id] || []).includes(o) ? '*' : '') + o).join('|') + ']]';
      return '[[' + (a[id] || []).join('|') + ']]';
    });
    let initial = '';
    if (variant === 'table' && d.columns) initial = [d.columns.join(' | '), ...d.rows.map(r => r.map(toSyntax).join(' | '))].join('\n');
    else if (d.text) initial = toSyntax(d.text);
    const help = {
      inline: 'Пропуск — [[ответ]] или [[ответ|другой вариант]]; без ответа — [[]].',
      inline_select: 'Пропуск — [[*правильный|вариант|вариант]]; звёздочка отмечает правильный (необязательно).',
      table: 'Первая строка — заголовки, ячейки разделяются «|». Поле ввода — [[ответ]] или [[]].',
    }[variant];
    const area = ta(initial, 6, { placeholder: variant === 'table' ? 'x | x²\n2 | [[4]]\n3 | [[9]]' : 'Столица Франции — [[Париж]].' });
    const tol = null;
    return {
      node: el('div', { class: 'stack-sm' }, field(variant === 'table' ? 'Таблица' : 'Текст', area, help)),
      collect: () => {
        const fields = [], answers = {};
        let n = 0;
        const conv = (s) => s.replace(BLANK_RE, (_, inner) => {
          const id = String(++n);
          const parts = alts(inner);
          if (variant === 'inline_select') {
            fields.push({ id, options: parts.map(p => p.replace(/^\*/, '')) });
            const ok = parts.filter(p => p.startsWith('*')).map(p => p.slice(1));
            if (ok.length) answers[id] = ok;
          } else { fields.push({ id }); if (parts.length) answers[id] = parts; }
          return `{{${id}}}`;
        });
        let data;
        if (variant === 'table') {
          const rows = lines(area.value).map(r => r.split('|').map(s => s.trim()));
          const columns = rows.shift() || [];
          data = { columns, rows: rows.map(r => conv(r.join('\u0001')).split('\u0001')).map(r => columns.map((_, i) => r[i] ?? '')), fields };
        } else data = { text: conv(area.value), fields };
        return { data, answer: Object.keys(answers).length ? { fields: answers, tolerance: tol } : null };
      },
    };
  }
  let rows = (d.fields || [{ id: '1', label: '' }]).map(f => ({ label: f.label || '', ans: (a[f.id] || []).join(' | ') }));
  const list = el('div', { class: 'ed-rows' });
  const multi = variant === 'multi';
  const tol = inp(task.answer?.tolerance ?? '', { inputmode: 'decimal', placeholder: '0' });
  const draw = () => list.replaceChildren(...rows.map((r, i) => el('div', { class: 'grid2' },
    field(multi ? `Подпись поля ${i + 1}` : 'Подпись поля', inp(r.label, { oninput: (e) => (r.label = e.target.value), placeholder: 'Необязательно' })),
    el('div', { class: 'row nowrap' }, field('Правильный ответ', inp(r.ans, { oninput: (e) => (r.ans = e.target.value), placeholder: variant === 'formula' ? 'a^2+b^2 | b^2+a^2' : 'Варианты через |', class: variant === 'formula' ? 'mono' : '' })),
      multi && rows.length > 1 ? ibtn({ icon: 'trash', tip: 'Удалить поле', danger: true, onclick: () => { rows.splice(i, 1); draw(); } }) : null))),
    multi ? el('button', { type: 'button', class: 'btn small ghost', onclick: () => { rows.push({ label: '', ans: '' }); draw(); } }, icon('add'), 'Поле') : '');
  draw();
  return {
    node: el('div', { class: 'stack-sm' }, list, variant === 'number' ? field('Допустимая погрешность', tol) : null),
    collect: () => {
      const fields = rows.map((r, i) => ({ id: String(i + 1), label: r.label }));
      const answers = {};
      rows.forEach((r, i) => { const v = alts(r.ans); if (v.length) answers[String(i + 1)] = v; });
      return { data: { fields }, answer: Object.keys(answers).length ? { fields: answers, tolerance: tol.value || 0 } : null };
    },
  };
}

/* ---------- 4. Свободный ответ ---------- */
function edOpen(variant, task) {
  const d = task.data || {}, a = task.answer || {};
  const ph = inp(d.placeholder, { placeholder: 'Подсказка в поле (необязательно)' });
  const nodes = [field('Подсказка', ph)];
  let collectAnswer = () => null;
  if (variant === 'short') {
    const acc = inp((a.accepted || []).join(' | '), { placeholder: 'Варианты через |' });
    nodes.push(field('Правильный ответ', acc, 'Необязательно; регистр и лишние пробелы не учитываются'));
    collectAnswer = () => (alts(acc.value).length ? { accepted: alts(acc.value) } : null);
  } else if (variant === 'number') {
    const val = inp(a.value ?? '', { inputmode: 'decimal' }), tol = inp(a.tolerance ?? '', { inputmode: 'decimal', placeholder: '0' });
    nodes.push(el('div', { class: 'grid2' }, field('Правильное число', val, 'Необязательно'), field('Погрешность', tol)));
    collectAnswer = () => (val.value.trim() ? { value: val.value, tolerance: tol.value || 0 } : null);
  } else {
    let max = null;
    if (variant === 'blocks') { max = inp(d.max_blocks ?? 5, { inputmode: 'numeric' }); nodes.push(field('Максимум блоков', max)); }
    nodes.push(el('p', { class: 'hint', text: 'Развёрнутый ответ проверяет репетитор.' }));
    return { node: el('div', { class: 'stack-sm' }, nodes), collect: () => ({ data: { placeholder: ph.value, ...(max ? { max_blocks: Number(max.value) || 5 } : {}) }, answer: null }) };
  }
  return { node: el('div', { class: 'stack-sm' }, nodes), collect: () => ({ data: { placeholder: ph.value }, answer: collectAnswer() }) };
}

/* ---------- 5. Упорядочивание ---------- */
function edOrdering(variant, task, key = 'items', label = 'Элементы в правильном порядке') {
  const area = ta((task.data?.[key] || []).map(x => x.text).join('\n'), 5, { placeholder: 'Первый\nВторой\nТретий' });
  const auto = autoBox(task.id ? !!task.answer : true, 'Проверять порядок автоматически');
  return {
    node: el('div', { class: 'stack-sm' }, field(label, area, 'По одному в строке; ученик получит их перемешанными'), auto.node),
    collect: () => ({ data: { [key]: lines(area.value).map((t, i) => ({ id: 'i' + (i + 1), text: t })) }, answer: auto.box.checked ? { enabled: true } : null }),
  };
}

/* ---------- 6. Классификация ---------- */
function edCategorize(variant, task) {
  const d = task.data || {}, map = task.answer?.map || {};
  const catName = new Map((d.categories || []).map(c => [c.id, c.text]));
  const cats = ta((d.categories || []).map(c => c.text).join('\n') || (variant === 'two' ? 'Категория 1\nКатегория 2' : ''), 3, { placeholder: 'Категория по одной в строке' });
  const items = ta((d.items || []).map(i => i.text + ((map[i.id] || []).length ? ' => ' + map[i.id].map(id => catName.get(id)).join(', ') : '')).join('\n'), 6,
    { placeholder: 'Яблоко => Фрукты\nМорковь => Овощи' });
  return {
    node: el('div', { class: 'grid2' }, field('Категории', cats, variant === 'two' ? 'Ровно две' : variant === 'many' ? 'Три и более' : ''),
      field('Элементы', items, variant === 'multi' ? 'Правильные категории после «=>» через запятую (необязательно)' : 'Правильная категория после «=>» (необязательно)')),
    collect: () => {
      const cs = lines(cats.value).map((t, i) => ({ id: 'c' + (i + 1), text: t }));
      const byName = new Map(cs.map(c => [c.text.toLowerCase(), c.id]));
      const answer = {}; let any = false;
      const its = lines(items.value).map((line, i) => {
        const [text, right] = line.split('=>');
        const id = 'i' + (i + 1);
        answer[id] = (right ? right.split(',').map(s => byName.get(s.trim().toLowerCase())).filter(Boolean) : []);
        if (answer[id].length) any = true;
        return { id, text: text.trim() };
      });
      return { data: { items: its, categories: cs }, answer: any ? { map: answer } : null };
    },
  };
}

/* ---------- 7–8. Рабочая область с элементами ---------- */
function parsePoints(text, prefix) {
  return lines(text).map((line, i) => {
    const star = line.startsWith('*');
    const [label, x, y] = line.replace(/^\*/, '').split(';').map(s => s.trim());
    return { id: prefix + (i + 1), text: label, x: clamp(x, 10 + (i * 17) % 80), y: clamp(y, 15 + Math.floor(i / 5) * 20 % 70), star };
  });
}
const clamp = (v, d) => { const n = parseFloat(String(v ?? '').replace(',', '.')); return Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : d; };
function parseEdges(text, nodes) {
  const ids = nodes.map(n => n.id);
  return lines(text).map(l => l.split(/\s*(?:->|→|-|—)\s*/).map(s => ids[Number(s) - 1])).filter(e => e.length === 2 && e[0] && e[1] && e[0] !== e[1]);
}
function pointsPreview(area, getImage, onClick) {
  const box = el('div', { class: 'canvas clickable small' });
  const draw = () => {
    const pts = parsePoints(area.value, 'p');
    const img = getImage();
    box.replaceChildren(...(img ? [el('img', { src: img, alt: '', draggable: 'false', referrerpolicy: 'no-referrer' })] : []),
      ...pts.map((p, i) => el('span', { class: 'node static-node' + (p.star ? ' selected' : ''), style: at(p.x, p.y), text: `${i + 1}. ${p.text}` })));
  };
  box.addEventListener('click', (e) => {
    const r = box.getBoundingClientRect();
    onClick(Math.round((e.clientX - r.left) / r.width * 100), Math.round((e.clientY - r.top) / r.height * 100));
    draw();
  });
  area.addEventListener('input', draw);
  draw();
  return { box, draw };
}

function edSelection(variant, task) {
  const d = task.data || {}, a = task.answer || {};
  const image = inp(d.image, { placeholder: 'https://… (необязательно)' });
  const nodes = [field('Фоновое изображение', image)];
  if (variant === 'position') {
    const r = a.region || {};
    const ins = ['x', 'y', 'w', 'h'].map(k => inp(r[k] ?? '', { inputmode: 'decimal', 'aria-label': k }));
    const rect = el('span', { class: 'region' });
    const box = el('div', { class: 'canvas clickable small' });
    let first = null;
    const draw = () => {
      const [x, y, w, h] = ins.map(i => parseFloat(i.value));
      box.replaceChildren(...(image.value ? [el('img', { src: image.value, alt: '', referrerpolicy: 'no-referrer' })] : []), rect);
      rect.hidden = ![x, y, w, h].every(Number.isFinite);
      Object.assign(rect.style, { left: x + '%', top: y + '%', width: w + '%', height: h + '%' });
    };
    box.addEventListener('click', (e) => {
      const b = box.getBoundingClientRect();
      const p = { x: Math.round((e.clientX - b.left) / b.width * 100), y: Math.round((e.clientY - b.top) / b.height * 100) };
      if (!first) { first = p; toast('Теперь нажмите противоположный угол области'); return; }
      const vals = [Math.min(first.x, p.x), Math.min(first.y, p.y), Math.abs(p.x - first.x), Math.abs(p.y - first.y)];
      ins.forEach((i, k) => (i.value = vals[k])); first = null; draw();
    });
    ins.forEach(i => i.addEventListener('input', draw)); image.addEventListener('change', draw);
    draw();
    nodes.push(el('p', { class: 'hint', text: 'Правильная область (в процентах). Нажмите на два противоположных угла на поле ниже или введите вручную. Пустые значения — без автопроверки.' }),
      el('div', { class: 'grid4' }, ['X', 'Y', 'Ширина', 'Высота'].map((l, k) => field(l, ins[k]))), box);
    return { node: el('div', { class: 'stack-sm' }, nodes), collect: () => {
      const v = ins.map(i => i.value.trim());
      return { data: { image: image.value }, answer: v.every(Boolean) ? { region: { x: v[0], y: v[1], w: v[2], h: v[3] } } : null };
    } };
  }
  const els = d.elements || [];
  let initial;
  if (variant === 'place_labels') initial = els.map(e => `${a.map?.[e.id] ?? e.text}; ${e.x}; ${e.y}`);
  else if (variant === 'name') initial = els.map(e => `${(a.names?.[e.id] || [e.text]).join(' | ')}; ${e.x}; ${e.y}`);
  else initial = els.map(e => `${(a.selected || []).includes(e.id) ? '*' : ''}${e.text}; ${e.x}; ${e.y}`);
  const area = ta(initial.join('\n'), 5, { class: 'mono' });
  const help = {
    one: 'Строка: «Подпись; x; y» (x, y — проценты). Звёздочка в начале — правильный элемент.',
    many: 'Строка: «Подпись; x; y». Звёздочкой отметьте правильные элементы.',
    scheme: 'Строка: «Блок; x; y». Звёздочкой отметьте правильные блоки.',
    place_labels: 'Строка: «Правильная метка; x; y» — позиция и метка, которую туда нужно поместить.',
    name: 'Строка: «Правильная подпись | вариант; x; y». Ученик видит только номер.',
  }[variant];
  const preview = pointsPreview(area, () => image.value, (x, y) => { area.value = (area.value.trim() ? area.value.trim() + '\n' : '') + `Элемент; ${x}; ${y}`; });
  image.addEventListener('change', preview.draw);
  nodes.push(field('Элементы', area, help + ' Нажмите на поле ниже, чтобы добавить элемент в этой точке.'), preview.box);
  let edges = null, extra = null, auto = null;
  if (variant === 'scheme') {
    const idx = new Map(els.map((e, i) => [e.id, i + 1]));
    edges = ta((d.edges || []).map(([x, y]) => `${idx.get(x)} -> ${idx.get(y)}`).join('\n'), 3, { class: 'mono', placeholder: '1 -> 2' });
    nodes.push(field('Связи схемы (для отображения)', edges, 'Номера блоков: «1 -> 2»'));
  }
  if (variant === 'place_labels') {
    const used = new Set(Object.values(a.map || {}));
    extra = ta((d.labels || []).filter(l => !used.has(l)).join('\n'), 2, { placeholder: 'Лишние метки по одной в строке' });
    nodes.push(field('Дополнительные метки', extra, 'Необязательно'));
  }
  if (variant === 'place_labels' || variant === 'name') { auto = autoBox(task.id ? !!task.answer : true); nodes.push(auto.node); }
  return {
    node: el('div', { class: 'stack-sm' }, nodes),
    collect: () => {
      const pts = parsePoints(area.value, 'e');
      if (variant === 'place_labels') {
        const labels = [...new Set([...pts.map(p => p.text), ...lines(extra.value)])];
        const map = Object.fromEntries(pts.map(p => [p.id, p.text]));
        return { data: { image: image.value, elements: pts.map((p, i) => ({ id: p.id, text: 'Позиция ' + (i + 1), x: p.x, y: p.y })), labels }, answer: auto.box.checked ? { map } : null };
      }
      if (variant === 'name') {
        const names = Object.fromEntries(pts.map(p => [p.id, alts(p.text)]));
        return { data: { image: image.value, elements: pts.map((p, i) => ({ id: p.id, text: 'Элемент ' + (i + 1), x: p.x, y: p.y })) }, answer: auto.box.checked ? { names } : null };
      }
      const data = { image: image.value, elements: pts.map(({ id, text, x, y }) => ({ id, text, x, y })) };
      if (edges) data.edges = parseEdges(edges.value, pts);
      const selected = pts.filter(p => p.star).map(p => p.id);
      return { data, answer: selected.length ? { selected } : null };
    },
  };
}

function edConnecting(variant, task) {
  const d = task.data || {};
  const ns = d.nodes || [];
  const idx = new Map(ns.map((n, i) => [n.id, i + 1]));
  const arrow = variant === 'directed' ? ' -> ' : ' - ';
  const area = ta(ns.map(n => `${n.text}; ${n.x}; ${n.y}`).join('\n'), 5, { class: 'mono', placeholder: 'Узел A; 20; 30\nУзел B; 70; 60' });
  const edges = ta((task.answer?.edges || []).map(([a, b]) => idx.get(a) + arrow + idx.get(b)).join('\n'), 3, { class: 'mono', placeholder: '1' + arrow + '2' });
  const preview = pointsPreview(area, () => '', (x, y) => { area.value = (area.value.trim() ? area.value.trim() + '\n' : '') + `Узел; ${x}; ${y}`; });
  return {
    node: el('div', { class: 'stack-sm' },
      field('Узлы', area, 'Строка: «Подпись; x; y» (проценты). Нажмите на поле ниже, чтобы добавить узел.'), preview.box,
      field('Правильные связи', edges, `Номера узлов, по одной связи в строке: «1${arrow}2». Необязательно.`)),
    collect: () => {
      const pts = parsePoints(area.value, 'n');
      const es = parseEdges(edges.value, pts);
      return { data: { nodes: pts.map(({ id, text, x, y }) => ({ id, text, x, y })) }, answer: es.length ? { edges: es } : null };
    },
  };
}

/* ---------- 9. Редактирование ---------- */
function edEditing(variant, task) {
  if (variant === 'reorder') return edOrdering(variant, task, 'lines', 'Строки в правильном порядке');
  const d = task.data || {}, a = task.answer || {};
  if (variant === 'highlight' || variant === 'delete') {
    const words = d.tokens || [];
    const marked = new Set(a.indices || []);
    const src = ta(words.map((w, i) => (marked.has(i) ? `[${w}]` : w)).join(' '), 4, { placeholder: 'Мама мыла [рамма] раму' });
    return {
      node: field('Текст', src, variant === 'highlight' ? 'Слова с ошибками возьмите в квадратные скобки (необязательно).' : 'Лишние слова возьмите в квадратные скобки (необязательно).'),
      collect: () => {
        const toks = src.value.split(/\s+/).filter(Boolean);
        const indices = toks.map((t, i) => (/^\[.*\]$/.test(t) ? i : -1)).filter(i => i >= 0);
        return { data: { text: toks.map(t => t.replace(/^\[(.*)\]$/, '$1')).join(' ') }, answer: indices.length ? { indices } : null };
      },
    };
  }
  const src = ta(d.text, 4), target = ta(a.text, 4);
  const hint = { rewrite: 'Ученик правит текст целиком.', replace: 'Ученик заменяет отдельные слова.', insert: 'Ученик вставляет пропущенные слова между существующими.' }[variant];
  return {
    node: el('div', { class: 'grid2' }, field('Исходный текст', src, hint), field('Правильный итоговый текст', target, 'Необязательно')),
    collect: () => ({ data: { text: src.value }, answer: target.value.trim() ? { text: target.value } : null }),
  };
}

const EDITORS = { choice: edChoice, matching: edMatching, fill: edFill, open: edOpen, ordering: edOrdering, categorize: edCategorize, selection: edSelection, connecting: edConnecting, editing: edEditing };

/* Карточка задания в конструкторе. */
function taskEditor(task, { onRemove, onMove, index, total }) {
  const state = { kind: task.kind || 'choice', variant: task.variant || 'single', id: task.id };
  const kindSel = el('select', { 'aria-label': 'Тип задания' }, Object.entries(KIND_NAMES).map(([k, n]) => el('option', { value: k, text: n, selected: k === state.kind })));
  const varSel = el('select', { 'aria-label': 'Вариант задания' });
  const prompt = ta(task.prompt, 3, { placeholder: 'Текст вопроса или инструкции. Поддерживается Markdown: **жирный**, *курсив*, [ссылка](https://…), ![](https://…/картинка.png)', maxlength: 20000 });
  const points = inp(task.points ?? 1, { inputmode: 'decimal', class: 'points' });
  const holder = el('div', { class: 'ed-specific' });
  const previewBox = el('div', { class: 'preview-box', hidden: true });
  let editor;
  const fillVariants = () => varSel.replaceChildren(...Object.entries(VARIANT_NAMES[state.kind]).map(([v, n]) => el('option', { value: v, text: n, selected: v === state.variant })));
  const build = (source) => { editor = EDITORS[state.kind](state.variant, source); holder.replaceChildren(editor.node); previewBox.hidden = true; };
  kindSel.onchange = () => { state.kind = kindSel.value; state.variant = Object.keys(VARIANT_NAMES[state.kind])[0]; fillVariants(); build({}); };
  varSel.onchange = () => {
    let source = {};
    try { const c = editor.collect(); source = { id: state.id, data: c.data, answer: c.answer }; } catch {}
    state.variant = varSel.value;
    try { build(source); } catch { build({}); }
  };
  fillVariants();
  build(task);
  const card = {
    collect: () => {
      const c = editor.collect();
      return { id: state.id, kind: state.kind, variant: state.variant, prompt: prompt.value, points: Number(String(points.value).replace(',', '.')) || 0, data: c.data, answer: c.answer };
    },
  };
  const togglePreview = () => {
    if (!previewBox.hidden) { previewBox.hidden = true; return; }
    const t = card.collect();
    const data = { ...t.data };
    if (t.kind === 'editing' && data.text) data.tokens = data.text.split(/\s+/).filter(Boolean);
    previewBox.replaceChildren(el('div', { class: 'cap', text: 'Так задание увидит ученик' }), markdownBlock(t.prompt, 'task-prompt'), renderTask({ ...t, data }, {}));
    previewBox.hidden = false;
  };
  card.node = el('section', { class: 'task-card editor' },
    el('div', { class: 'task-head' }, el('span', { class: 'task-num', text: index + 1 }),
      el('div', { class: 'grow row' }, kindSel, varSel),
      el('span', { class: 'row nowrap' },
        ibtn({ icon: 'eye', tip: 'Предпросмотр', onclick: togglePreview }),
        ibtn({ icon: 'up', tip: 'Выше', onclick: () => onMove(-1), disabled: index === 0 }),
        ibtn({ icon: 'down', tip: 'Ниже', onclick: () => onMove(1), disabled: index === total - 1 }),
        ibtn({ icon: 'trash', tip: 'Удалить задание', danger: true, onclick: onRemove }))),
    el('div', { class: 'grid-prompt' },
      el('label', {}, 'Вопрос', mdToolbar(prompt), prompt, el('span', { class: 'hint', text: 'Markdown; медиа подключаются по ссылкам и не хранятся в системе. Как это выглядит — в предпросмотре.' })),
      field('Баллы', points, 'За верный ответ')),
    holder, previewBox);
  return card;
}

const head = (title, lead, ...extra) => el('div', { class: 'toolbar' }, el('div', {}, el('h1', { text: title }), lead ? el('p', { class: 'muted lead', text: lead }) : null), extra.length ? el('div', { class: 'row' }, extra) : null);
const empty = (text, ...extra) => el('div', { class: 'empty' }, el('p', { class: 'muted', text }), ...extra);
async function busy(button, fn) {
  button.disabled = true;
  try { return await fn(); } finally { button.disabled = false; }
}

/* ---------- репетитор ---------- */
async function pageTeacherTests() {
  const { items } = await api('/teacher/tests');
  const add = el('a', { class: 'btn primary', href: '/testing/new' }, icon('add'), 'Создать тест');
  if (!items.length) return el('div', {}, head('Мои тесты', 'Создавайте тесты и выдавайте доступ ученикам'), empty('Тестов пока нет.', add));
  return el('div', {}, head('Мои тесты', 'Создавайте тесты и выдавайте доступ ученикам', add),
    el('div', { class: 'cards' }, items.map(t => el('article', { class: 'tcard' },
      el('h2', {}, el('a', { class: 'card-link', href: `/testing/${t.id}`, text: t.title })),
      t.description ? el('p', { class: 'muted clamp2', text: markdownPlain(t.description) }) : null,
      el('div', { class: 'meta-row' },
        el('span', { text: `${t.task_count} ${plural(t.task_count, 'задание', 'задания', 'заданий')}` }),
        el('span', { text: `${fmtNum(t.max_points)} б. автопроверки` }),
        el('span', { text: `доступ: ${t.access_count}` }), el('span', { text: `попыток: ${t.attempt_count}` }),
        el('span', { class: 'pill pill-gray', text: 'версия ' + t.version })),
      el('div', { class: 'card-actions' },
        ibtn({ icon: 'edit', tip: 'Изменить', href: `/testing/${t.id}/edit` }),
        ibtn({ icon: 'open', tip: 'Доступ и результаты', href: `/testing/${t.id}` }))))));
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many;
}

async function pageTestEditor(id) {
  const test = id ? await api(`/teacher/tests/${id}`) : { title: '', description: '', tasks: [], good_percent: 60, excellent_percent: 85 };
  const title = el('input', { type: 'text', maxlength: 200, value: test.title, required: true });
  const description = el('textarea', { rows: 3, maxlength: 20000, value: test.description });
  const good = el('input', { type: 'number', min: 1, max: 99, value: test.good_percent });
  const excellent = el('input', { type: 'number', min: 2, max: 100, value: test.excellent_percent });
  const list = el('div', { class: 'stack' });
  const err = el('div', { class: 'notice error', hidden: true, role: 'alert' });
  let cards = [];
  let snapshot = '';
  const collectAll = () => ({ title: title.value, description: description.value, good_percent: Number(good.value), excellent_percent: Number(excellent.value), tasks: cards.map(c => c.collect()) });
  const draw = () => {
    const tasks = cards.map(c => { try { return c.collect(); } catch { return {}; } });
    cards = tasks.map((t, i) => taskEditor(t, {
      index: i, total: tasks.length,
      onRemove: async () => { if (await askConfirm('Удалить задание?', `Задание ${i + 1} будет удалено из теста после сохранения.`, { okText: 'Удалить', danger: true })) { cards.splice(i, 1); draw(); } },
      onMove: (d) => { const j = i + d; [cards[i], cards[j]] = [cards[j], cards[i]]; draw(); },
    }));
    list.replaceChildren(...cards.map(c => c.node), ...(cards.length ? [] : [empty('Добавьте первое задание')]));
  };
  cards = test.tasks.map(t => ({ collect: () => t }));
  draw();
  setTimeout(() => { try { snapshot = JSON.stringify(collectAll()); } catch {} }, 0);
  leaveGuard = () => { try { return JSON.stringify(collectAll()) !== snapshot ? 'Есть несохранённые изменения. Уйти со страницы?' : ''; } catch { return ''; } };
  const addTask = () => { cards.push({ collect: () => ({ kind: 'choice', variant: 'single', points: 1, prompt: '' }) }); draw(); cards.at(-1).node.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
  const save = el('button', { type: 'button', class: 'btn primary' }, icon('check'), 'Сохранить');
  save.onclick = () => busy(save, async () => {
    err.hidden = true;
    try {
      const body = collectAll();
      const problem = !body.title.trim() ? 'Укажите название теста.' : !body.tasks.length ? 'Добавьте хотя бы одно задание.'
        : body.tasks.findIndex(t => !String(t.prompt || '').trim()) >= 0 ? `Задание ${body.tasks.findIndex(t => !String(t.prompt || '').trim()) + 1}. Заполните вопрос.` : '';
      if (problem) { err.textContent = problem; err.hidden = false; err.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
      if (id && !(await askConfirm('Сохранить новую версию теста?', 'После изменения ученики перестанут видеть свои прежние результаты по этому тесту.', { okText: 'Сохранить' }))) return;
      const saved = await api(id ? `/teacher/tests/${id}` : '/teacher/tests', { method: id ? 'PUT' : 'POST', body });
      snapshot = JSON.stringify(collectAll());
      leaveGuard = null;
      toast('Тест сохранён', 'ok');
      host.navigate(`/testing/${saved.id}`);
    } catch (error) { err.textContent = error.message; err.hidden = false; err.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  });
  return el('div', { class: 'stack' },
    head(id ? 'Редактирование теста' : 'Новый тест', id ? 'Сохранение создаёт новую версию теста' : 'Соберите тест из заданий разных типов',
      el('a', { class: 'btn ghost', href: id ? `/testing/${id}` : '/testing', text: 'Отмена' }), save),
    el('section', { class: 'form-card stack-sm' },
      el('label', {}, 'Название', title), el('label', {}, 'Описание', mdToolbar(description), description, el('span', { class: 'hint', text: 'Поддерживается Markdown' })),
      el('div', { class: 'grid2' },
        el('label', {}, 'Порог «хорошо», %', good, el('span', { class: 'hint', text: 'Ниже — «удовлетворительно»' })),
        el('label', {}, 'Порог «замечательно», %', excellent)),
      el('p', { class: 'hint', text: 'Оценка выставляется автоматически по доле баллов за задания с правильным ответом. Задания без правильного ответа оценивает репетитор.' })),
    err, list,
    el('div', { class: 'row' }, el('button', { type: 'button', class: 'btn ghost', onclick: addTask }, icon('add'), 'Добавить задание')));
}

async function pageTestOverview(id) {
  const [test, access, results] = await Promise.all([api(`/teacher/tests/${id}`), api(`/teacher/tests/${id}/access`), api(`/teacher/tests/${id}/results`)]);
  const accessList = el('div', { class: 'table-wrap' });
  const drawAccess = () => accessList.replaceChildren(access.items.length ? el('table', {},
    el('thead', {}, el('tr', {}, el('th', { text: 'Ученик' }), el('th', { text: 'Попыток' }), el('th', { text: 'Доступ' }))),
    el('tbody', {}, access.items.map(s => el('tr', {},
      el('td', {}, el('div', { text: s.full_name }), el('div', { class: 'muted small', text: s.username })),
      el('td', { text: s.attempts }),
      el('td', {}, el('label', { class: 'switch' }, el('input', { type: 'checkbox', role: 'switch', checked: s.enabled, 'aria-label': 'Доступ для ' + s.full_name,
        onchange: async (e) => {
          const box = e.target; box.disabled = true;
          try { Object.assign(s, await api(`/teacher/tests/${id}/access/${s.student_id}`, { method: 'PUT', body: { enabled: box.checked } })); toast(box.checked ? 'Доступ открыт' : 'Доступ закрыт', 'ok'); }
          catch (error) { box.checked = !box.checked; toast(error.message, 'error'); }
          finally { box.disabled = false; }
        } }), el('span', { class: 'switch-ui' }))))))) : el('p', { class: 'muted pad', text: 'Связанных учеников пока нет. Добавьте их в разделе «Ученики».' }));
  drawAccess();
  const setAll = async (enabled) => {
    for (const s of access.items.filter(x => x.enabled !== enabled)) {
      try { Object.assign(s, await api(`/teacher/tests/${id}/access/${s.student_id}`, { method: 'PUT', body: { enabled } })); } catch (error) { toast(error.message, 'error'); break; }
    }
    drawAccess();
  };
  const del = el('button', { type: 'button', class: 'btn danger' }, icon('trash'), 'Удалить тест');
  del.onclick = () => busy(del, async () => {
    if (!(await askConfirm(`Удалить тест «${test.title}»?`, 'Все результаты по нему будут удалены безвозвратно.', { okText: 'Удалить', danger: true }))) return;
    try { await api(`/teacher/tests/${id}`, { method: 'DELETE' }); toast('Тест удалён', 'ok'); host.navigate('/testing'); } catch (error) { toast(error.message, 'error'); }
  });
  return el('div', { class: 'stack' },
    head(test.title, `Версия ${test.version} · ${test.tasks.length} ${plural(test.tasks.length, 'задание', 'задания', 'заданий')} · пороги: хорошо ${test.good_percent}%, замечательно ${test.excellent_percent}%`,
      el('a', { class: 'btn ghost', href: `/testing/${id}/edit` }, icon('edit'), 'Изменить'), del),
    el('section', { class: 'stack-sm' }, el('div', { class: 'toolbar slim' }, el('h2', { text: 'Доступ учеников' }),
      el('div', { class: 'row' }, el('button', { type: 'button', class: 'btn small ghost', onclick: () => setAll(true), text: 'Открыть всем' }), el('button', { type: 'button', class: 'btn small ghost', onclick: () => setAll(false), text: 'Закрыть всем' }))), accessList),
    el('section', { class: 'stack-sm' }, el('h2', { text: 'Результаты' }), resultsTable(results.items, true)));
}

function resultsTable(items, teacher) {
  if (!items.length) return el('p', { class: 'muted', text: 'Результатов пока нет.' });
  return el('div', { class: 'table-wrap' }, el('table', {},
    el('thead', {}, el('tr', {}, el('th', { text: teacher ? 'Ученик' : 'Тест' }), el('th', { text: 'Дата' }), el('th', { text: 'Баллы' }), el('th', { text: 'Автооценка' }), el('th', { text: 'Оценка репетитора' }), el('th', {}))),
    el('tbody', {}, items.map(r => el('tr', {},
      el('td', {}, el('div', { text: teacher ? r.student_name : r.test_title }), r.outdated ? el('span', { class: 'pill pill-gray', text: 'прежняя версия теста' }) : null),
      el('td', { class: 'nowrap', text: fmtDate(r.submitted_at) }),
      el('td', { class: 'nowrap', text: r.max_score ? `${fmtNum(r.score)} / ${fmtNum(r.max_score)}` : '—' }),
      el('td', {}, gradePill(r.auto_grade, 'ждёт проверки')),
      el('td', {}, r.teacher_grade ? gradePill(r.teacher_grade) : el('span', { class: 'muted', text: r.teacher_comment ? 'комментарий' : '—' })),
      el('td', {}, ibtn({ icon: 'open', tip: 'Открыть', href: teacher ? `/testing/results/${r.id}` : `/testing/results/${r.id}` })))))));
}


const STATUS = { correct: ['верно', 'pill-green'], wrong: ['неверно', 'pill-red'], manual: ['проверяет репетитор', 'pill-violet'], empty: ['нет ответа', 'pill-gray'] };

function attemptView(a, teacher) {
  const header = el('section', { class: 'form-card result-head' },
    el('div', { class: 'result-grid' },
      el('div', {}, el('div', { class: 'cap', text: 'Баллы' }), el('div', { class: 'big', text: a.max_score ? `${fmtNum(a.score)} из ${fmtNum(a.max_score)}` : '—' })),
      el('div', {}, el('div', { class: 'cap', text: 'Автооценка' }), gradePill(a.auto_grade, 'ждёт проверки')),
      el('div', {}, el('div', { class: 'cap', text: 'Оценка репетитора' }), a.teacher_grade ? gradePill(a.teacher_grade) : el('span', { class: 'muted', text: 'нет' })),
      el('div', {}, el('div', { class: 'cap', text: 'Сдано' }), el('div', { text: fmtDate(a.submitted_at) }))),
    a.teacher_comment && !teacher ? el('div', { class: 'teacher-note' }, el('div', { class: 'cap', text: 'Комментарий репетитора' }), el('p', { class: 'pre', text: a.teacher_comment })) : null);
  const tasks = a.tasks.map((t, i) => {
    const r = a.results[t.id] || { status: 'empty', points: 0 };
    const [label, cls] = STATUS[r.status] || STATUS.empty;
    const given = a.answers[t.id];
    return el('section', { class: 'task-card' },
      el('div', { class: 'task-head' }, el('span', { class: 'task-num', text: i + 1 }), el('div', { class: 'grow' }, el('div', { class: 'cap', text: `${KIND_NAMES[t.kind]} · ${VARIANT_NAMES[t.kind][t.variant]}` })),
        el('span', { class: `pill ${cls}`, text: label }), (t.graded ?? t.answer) && t.points ? el('span', { class: 'muted small nowrap', text: `${fmtNum(r.points)} / ${fmtNum(t.points)} б.` }) : null),
      markdownBlock(t.prompt, 'task-prompt'),
      renderTask(t, { value: given, readonly: true }),
      teacher ? el('p', { class: 'answer-key' }, el('span', { class: 'cap', text: 'Правильный ответ: ' }), describeAnswer(t)) : null);
  });
  return el('div', { class: 'stack' }, header, ...tasks);
}

async function pageTeacherResult(id) {
  const a = await api(`/teacher/results/${id}`);
  const grade = el('select', { 'aria-label': 'Оценка' }, el('option', { value: '', text: 'Без оценки' }), GRADES.map(g => el('option', { value: g, text: g, selected: a.teacher_grade === g })));
  const comment = el('textarea', { rows: 4, maxlength: 5000, value: a.teacher_comment, placeholder: 'Комментарий для ученика' });
  const save = el('button', { type: 'submit', class: 'btn primary', text: 'Сохранить оценку' });
  const review = el('form', { class: 'form-card stack-sm', onsubmit: (e) => { e.preventDefault(); busy(save, async () => {
    try { await api(`/teacher/results/${id}/review`, { method: 'PUT', body: { teacher_grade: grade.value || null, teacher_comment: comment.value } }); toast('Оценка сохранена', 'ok'); host.rerender(); }
    catch (error) { toast(error.message, 'error'); }
  }); } }, el('h2', { text: 'Оценка репетитора' }), el('label', {}, 'Оценка', grade), el('label', {}, 'Комментарий', comment), el('div', {}, save));
  return el('div', { class: 'stack' },
    head(`${a.student_name}`, a.test_title, el('a', { class: 'btn ghost', href: `/testing/${a.test_id}`, text: 'К тесту' })),
    a.outdated ? el('div', { class: 'notice' }, 'Тест изменён после прохождения: ученик больше не видит этот результат, подробные ответы недоступны.') : null,
    attemptView(a, true), review);
}

/* ---------- ученик ---------- */
async function pageAvailable() {
  const { items } = await api('/student/tests');
  if (!items.length) return el('div', {}, head('Тесты', 'Здесь появятся тесты, к которым репетитор откроет доступ'), empty('Доступных тестов пока нет.'));
  return el('div', {}, head('Тесты', 'Тесты, к которым у вас есть доступ'),
    el('div', { class: 'cards' }, items.map(t => el('article', { class: 'tcard' },
      el('h2', {}, el('a', { class: 'card-link', href: `/testing/take/${t.id}`, text: t.title })),
      t.description ? el('p', { class: 'muted clamp2', text: markdownPlain(t.description) }) : null,
      el('div', { class: 'meta-row' }, t.owner_name ? el('span', { text: t.owner_name }) : null, el('span', { text: `${t.task_count} ${plural(t.task_count, 'задание', 'задания', 'заданий')}` }),
        t.my_attempts ? el('span', { text: `попыток: ${t.my_attempts}` }) : el('span', { text: 'ещё не проходили' }),
        t.my_attempts ? gradePill(t.my_last_grade, 'ждёт проверки') : null),
      el('div', { class: 'card-actions' }, el('a', { class: 'btn small primary', href: `/testing/take/${t.id}`, text: t.my_attempts ? 'Пройти ещё раз' : 'Начать' }))))));
}

async function pageTake(id) {
  const test = await api(`/student/tests/${id}`);
  const answers = {};
  let dirty = false;
  const progress = el('span', { class: 'muted small' });
  const updateProgress = () => { progress.textContent = `Отвечено: ${Object.keys(answers).filter(k => filled(answers[k])).length} из ${test.tasks.length}`; };
  const cards = test.tasks.map((t, i) => el('section', { class: 'task-card' },
    el('div', { class: 'task-head' }, el('span', { class: 'task-num', text: i + 1 }), el('div', { class: 'grow' }, el('div', { class: 'cap', text: VARIANT_NAMES[t.kind][t.variant] })),
      t.graded && t.points ? el('span', { class: 'muted small nowrap', text: `${fmtNum(t.points)} б.` }) : null),
    markdownBlock(t.prompt, 'task-prompt'),
    renderTask(t, { onChange: (v) => { answers[t.id] = v; dirty = true; updateProgress(); } })));
  updateProgress();
  leaveGuard = () => (dirty ? 'Ответы не отправлены. Уйти со страницы?' : '');
  const submit = el('button', { type: 'button', class: 'btn primary' }, icon('check'), 'Завершить тест');
  submit.onclick = () => busy(submit, async () => {
    const left = test.tasks.length - Object.keys(answers).filter(k => filled(answers[k])).length;
    if (!(await askConfirm('Завершить тест?', left ? `Не отвечено заданий: ${left}. После отправки изменить ответы нельзя.` : 'После отправки изменить ответы нельзя.', { okText: 'Отправить ответы' }))) return;
    try {
      const res = await api(`/student/tests/${id}/attempts`, { method: 'POST', body: { version: test.version, answers } });
      dirty = false; leaveGuard = null;
      toast('Ответы отправлены', 'ok');
      host.navigate(`/testing/results/${res.id}`);
    } catch (error) { toast(error.message, 'error'); }
  });
  return el('div', { class: 'stack' }, head(test.title), test.description ? markdownBlock(test.description, 'test-desc') : '',
    ...cards, el('div', { class: 'submit-bar' }, progress, submit));
}

function filled(v) {
  if (v === null || v === undefined || v === '') return false;
  if (Array.isArray(v)) return v.some(filled);
  if (typeof v === 'object') return Object.values(v).some(filled);
  return true;
}

async function pageMyResults() {
  const { items } = await api('/student/results');
  return el('div', {}, head('Мои результаты', 'Результаты по действующим версиям тестов'), resultsTable(items, false));
}

async function pageMyResult(id) {
  const a = await api(`/student/results/${id}`);
  return el('div', { class: 'stack' }, head(a.test_title, 'Результат прохождения', el('a', { class: 'btn ghost', href: '/testing/results', text: 'Все результаты' })), attemptView(a, false));
}

export const testingPages = {
  teacherTests: pageTeacherTests, testEditor: pageTestEditor, testOverview: pageTestOverview,
  teacherResult: pageTeacherResult, available: pageAvailable, take: pageTake, myResults: pageMyResults,
  myResult: pageMyResult,
};
export { renderTask, markdownBlock, mdToolbar, toast, askConfirm, el, icon, ibtn };
