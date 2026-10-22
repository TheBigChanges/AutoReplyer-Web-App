import { tr, getLanguage, getLocale, setLanguage, normalizeLanguage, weekDays, translateChrome, languageSelector } from './i18n.js';
import {animatePage, animateNotice, showDialog, closeDialog, initInteractions, updateMobileNavigation} from './interactions.js';
import {requestJSON, trustedApiBase} from './api-client.js';
const paths = {
  reply: 'M9 10V4L2 11l7 7v-6h5c4 0 6 3 6 7 3-9-1-13-11-13',
  dashboard: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  message: 'M21 11a8 8 0 0 1-8 8H6l-4 3V11a9 9 0 0 1 19 0Z M7 8h10 M7 12h7',
  sparkles: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z M20 2v4 M18 4h4',
  book: 'M12 5C8 2 4 3 2 4v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-2-10 1Z M12 5v16',
  calendar: 'M4 5h16v16H4z M8 2v6 M16 2v6 M4 10h16 M8 14h2 M14 14h2 M8 17h2',
  chart: 'M4 3v17h17 M8 16v-5 M13 16V7 M18 16V4',
  moon: 'M20 15A9 9 0 0 1 9 3a9 9 0 1 0 11 12Z',
  settings: 'm9 3-1 3-3 1-2 4 2 3v3l4 3 3-1 3 1 4-3v-3l2-3-2-4-3-1-1-3Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  help: 'M12 17h.01 M9 9a3 3 0 1 1 5 2c-2 1-2 1-2 3 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
  globe: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z M2 12h20 M12 2c6 6 6 14 0 20-6-6-6-14 0-20Z',
  chevrons: 'm9 8 3-3 3 3 M9 16l3 3 3-3',
  flask: 'M9 3h6 M10 3v7L4 20h16l-6-10V3 M7 15h10',
  arrow: 'M5 12h14 m-5-5 5 5-5 5',
  up: 'm6 14 5-5 4 4 5-7 M15 6h5v5',
  inbox: 'M4 4h16l2 13v3H2v-3Z M2 15h6l2 3h4l2-3h6',
  send: 'm22 2-7 20-4-9-9-4Z M22 2 11 13',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z M12 6v6l4 2',
  plus: 'M12 5v14 M5 12h14',
  check: 'm5 12 4 4L19 6',
  close: 'm6 6 12 12 M6 18 18 6',
  external: 'M14 3h7v7 M21 3 10 14 M10 3H3v18h18v-7',
  shield: 'm12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6Z m-5 10 3 3 5-6',
  users: 'M16 21v-3c0-4-12-4-12 0v3 M14 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z M18 4c5 0 5 7 0 7 M18 14c4 0 4 3 4 6',
  copy: 'M8 8h13v13H8z M16 8V3H3v13h5',
  save: 'M3 3h15l3 3v15H3Z M7 3v6h10V3 M7 21v-7h10v7',
  logout: 'M9 3H3v18h6 M8 12h13 m-5-5 5 5-5 5',
  sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z M12 1v3 M12 20v3 M1 12h3 M20 12h3 M4 4l2 2 M18 18l2 2 M4 20l2-2 M18 6l2-2',
  crown: 'm2 5 5 5 5-8 5 8 5-5-3 15H5Z',
  edit: 'm15 3 6 6 M3 21l5-1L21 7l-4-4L4 16Z',
  trash: 'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7'
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.message}"/></svg>`;
const e = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
})[c]);
const num = n => Number(n || 0).toLocaleString(getLocale());
const time = n => `${String(Math.floor(n / 60)).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`;
const minutes = s => s.split(':').reduce((h, m) => Number(h) * 60 + Number(m));
let days = weekDays();
const navigationKeys = [['dashboard', 'dashboard', 'Umumiy ko‘rinish'], ['replies', 'message', 'Avtojavob'], ['ai', 'sparkles', 'AI yordamchi', 'ULTRA'], ['faq', 'book', 'Smart FAQ'], ['knowledge', 'book', 'Bilimlar bazasi'], ['scheduler', 'calendar', 'Smart jadval'], ['analytics', 'chart', 'Statistika'], ['sleep', 'moon', 'Uyqu rejimi'], ['profile', 'clock', 'Profil vositalari'], ['settings', 'settings', 'Sozlamalar']];
const tg = window.Telegram?.WebApp;
let apiBase = localStorage.getItem('ar-api') || '';
let mode = tg?.initData ? 'loading' : 'demo',
  period = 7,
  page = 'dashboard',
  toastTimer;
const seed = {
  user: {
    id: 0,
    first_name: 'Dilshodbek'
  },
  plan: 'ultra',
  connection: {
    is_enabled: true,
    can_reply: true
  },
  settings: {
    offline: true,
    cooldown_hours: 3,
    auto_reply_text: 'Assalomu alaykum! Xabaringiz uchun rahmat. Hozir biroz bandman, imkon bo‘lishi bilan javob beraman. 🌿',
    sleep_mode_enabled: true,
    sleep_start_minutes: 1380,
    sleep_end_minutes: 420,
    sleep_reply_text: 'Xabaringiz uchun rahmat! Hozir dam olyapman. Ertalab sizga albatta javob beraman. 🌙',
    ai_enabled: true,
    ai_role: 'assistant',
    ai_info: 'Muloyim va qisqa javob bering. Aniq bilmagan ma’lumotlaringizni to‘qib chiqarmang.',
    faq_enabled: true,
    kb_enabled: true,
    scheduler_enabled: true,
    name_clock_enabled: false,
    name_clock_tz: 'Asia/Tashkent'
  },
  faq: [{
    id: 1,
    question: 'Ish vaqtingiz qanday?',
    keywords: ['ish vaqti', 'soat nechada'],
    answer: 'Dushanbadan jumagacha, soat 09:00 dan 18:00 gacha ishlaymiz.',
    is_enabled: true
  }, {
    id: 2,
    question: 'Yetkazib berish bormi?',
    keywords: ['yetkazib berish', 'dostavka'],
    answer: 'Ha, Toshkent bo‘ylab yetkazib beramiz. Manzilingizni yozib qoldiring.',
    is_enabled: true
  }, {
    id: 3,
    question: 'Siz bilan qanday bog‘lansam bo‘ladi?',
    keywords: ['bog‘lanish', 'telefon'],
    answer: 'Shu yerda xabaringizni qoldiring. Tez orada siz bilan bog‘lanamiz.',
    is_enabled: true
  }],
  knowledge: [{
    id: 1,
    title: 'Biznes haqida',
    keywords: ['xizmat', 'biznes'],
    content: 'Biz mijozlarga Telegram orqali yordam beramiz. Ish vaqti: dushanba–juma 09:00–18:00. Dam olish kunlari murojaatlar keyingi ish kunida ko‘rib chiqiladi.',
    is_enabled: true
  }],
  schedules: [{
    id: 1,
    days: 31,
    start_min: 540,
    end_min: 1080,
    text: 'Hozir ish bilan bandman. Tez orada javob beraman!',
    is_enabled: true
  }, {
    id: 2,
    days: 96,
    start_min: 0,
    end_min: 1440,
    text: 'Bugun dam olish kuni. Xabaringizga keyingi ish kunida javob beraman.',
    is_enabled: true
  }],
  ai_usage: 18
};
let state;
try {
  state = JSON.parse(localStorage.getItem('ar-demo-v1')) || structuredClone(seed);
} catch {
  state = structuredClone(seed);
}
// Recover malformed demo storage before rendering either account mode.
if (typeof state?.user?.first_name !== 'string' || !state?.settings || !['faq', 'knowledge', 'schedules'].every(key => Array.isArray(state[key]))) state = structuredClone(seed);
let renderedKey;
let summaryRequest = 0;
let connectionRequest = 0;
const pendingForms = new WeakSet();
function paintIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
}
function toast(message) {
  const t = document.querySelector('#toast');
  t.textContent = message;
  t.classList.add('visible');
  animateNotice(t);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('visible'), 4200);
}
function persist() {
  if (mode === 'demo') localStorage.setItem('ar-demo-v1', JSON.stringify(state));
}
async function api(path, method = 'GET', body) {
  try {
    return await requestJSON(apiBase, path, {method, body, initData: tg?.initData || '', language: getLanguage()});
  } catch (error) {
    if (error.status) throw error;
    throw Error(tr("API ulanmagan. Sozlamalarda API manzilini kiriting."));
  }
}
async function loadLive() {
  const request = ++connectionRequest;
  const loaded = await api('/api/bootstrap');
  if (request !== connectionRequest) return;
  state = loaded;
  summaryRequest++;
  // An explicit Web App choice wins; otherwise start in the bot's saved language.
  const initialLanguage = normalizeLanguage(localStorage.getItem('ar-language')) || normalizeLanguage(state.language);
  if (initialLanguage) setLanguage(initialLanguage);
  mode = 'live';
  period = 1;
  summary = {
    incoming: 0,
    sent: 0,
    kinds: {
      ai: 0,
      faq: 0,
      static: 0,
      sleep: 0
    },
    peak: null,
    skipped: 0,
    series: null
  };
  render();
}
function switchControl(field, label = field) {
  return `<label class="switch"><input type="checkbox" data-setting="${field}" aria-label="${e(label)}" ${state.settings[field] ? 'checked' : ''}><span></span></label>`;
}
async function saveSettings(fields) {
  if (mode === 'live') await api('/api/settings', 'PATCH', fields);else if (mode !== 'demo') throw Error(tr("Avval botga ulaning."));
  Object.assign(state.settings, fields);
  persist();
}
function head(title, sub, actions = '', eyebrow = tr("SIZNING BOSHQARUV MARKAZINGIZ")) {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subtitle">${sub}</p></div>${actions}</div>`;
}
function button(label, action, ic = 'plus', cls = '') {
  return `<button type="button" class="button ${cls}" data-action="${action}">${icon(ic)}${label}</button>`;
}
function featureRow(ic, title, sub, control) {
  return `<div class="feature-row"><span class="feature-icon">${icon(ic)}</span><div><strong>${title}</strong><small>${sub}</small></div>${control}</div>`;
}
function stat(label, value, ic, foot) {
  return `<div class="stat"><div class="stat-label">${label}<span class="stat-icon">${icon(ic)}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${foot}</div></div>`;
}
const periodButtons = () => `<div class="segmented" aria-label="${tr("Statistika davri")}">${[[1, tr("Bugun")], [7, tr("7 kun")], [30, tr("30 kun")]].map(([n, label]) => `<button class="${period === n ? 'active' : ''}" data-period="${n}">${label}</button>`).join('')}</div>`;
function demoSummary() {
  let inc, sent, labels;
  if (period === 1) {
    inc = [0, 0, 0, 0, 0, 0, 1, 3, 5, 7, 9, 6, 8, 12, 11, 8, 10, 13, 9, 7, 4, 2, 1, 0];
    sent = inc.map(n => Math.max(0, Math.round(n * .8)));
    labels = inc.map((_, i) => String(i).padStart(2, '0'));
  } else {
    const n = period;
    inc = Array.from({
      length: n
    }, (_, i) => [28, 41, 33, 55, 45, 64, 52][i % 7]);
    sent = inc.map((n, i) => Math.round(n * [.75, .85, .8][i % 3]));
    labels = inc.map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - n + i + 1);
      return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
    });
  }
  const incoming = inc.reduce((a, b) => a + b, 0),
    total = sent.reduce((a, b) => a + b, 0);
  return {
    incoming,
    sent: total,
    kinds: {
      ai: Math.round(total * .48),
      faq: Math.round(total * .28),
      static: Math.round(total * .16),
      sleep: total - Math.round(total * .48) - Math.round(total * .28) - Math.round(total * .16)
    },
    peak: [18, 20],
    series: {
      inc,
      sent,
      labels
    },
    skipped: 12
  };
}
let summary = demoSummary();
function chart(s) {
  if (!s.series) return `<div class="empty"><p>${tr("Faollik grafigi Plus tarifidan boshlab mavjud.")}</p><a class="green-link" href="#plans">${tr("Tariflarni ko‘rish ↗")}</a></div>`;
  const {
    inc,
    sent,
    labels
  } = s.series;
  const max = Math.max(...inc, ...sent, 4),
    w = 570,
    h = 150;
  const pos = (n, i) => [37 + i * (w - 44) / Math.max(inc.length - 1, 1), h - 12 - n / max * (h - 30)];
  const pts = arr => arr.map((n, i) => pos(n, i).join(',')).join(' ');
  const area = `M ${pos(inc[0], 0).join(' ')} L ${inc.map((n, i) => pos(n, i).join(' ')).join(' L ')} L ${w - 7} ${h - 12} L 37 ${h - 12} Z`;
  return `<div class="chart-wrap"><svg viewBox="0 0 580 180" role="img" aria-label="${tr("Kelgan xabarlar va yuborilgan javoblar grafigi")}"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#9bcbae" stop-opacity=".3"/><stop offset="1" stop-color="#9bcbae" stop-opacity="0"/></linearGradient></defs>${[0, 1, 2, 3].map(i => `<line x1="37" y1="${18 + i * 40}" x2="570" y2="${18 + i * 40}" stroke="var(--line)" stroke-dasharray="3 4"/><text x="3" y="${21 + i * 40}">${Math.round(max * (1 - i / 3))}</text>`).join('')}<path d="${area}" fill="url(#area)"/><polyline points="${pts(sent)}" fill="none" stroke="#bad7c3" stroke-width="2.2" stroke-linejoin="round"/><polyline points="${pts(inc)}" fill="none" stroke="#418967" stroke-width="2.4" stroke-linejoin="round"/>${labels.map((d, i) => i % Math.max(1, Math.ceil(labels.length / 7)) === 0 ? `<text x="${pos(0, i)[0]}" y="166" text-anchor="middle">${e(d)}</text>` : '').join('')}</svg></div>`;
}
function donut(s) {
  if (mode === 'live' && ['free', 'plus'].includes(state.plan)) return `<div class="empty"><p>${tr("Taqsimot diagrammasi Pro va Ultra tariflarida mavjud.")}</p><a class="green-link" href="#plans">${tr("Tariflarni ko‘rish ↗")}</a></div>`;
  const colors = ['#548d6c', '#a4c4a5', '#bca9d3', '#e5cc9a'];
  const names = [tr("AI yordamchi"), 'Smart FAQ', tr("Oddiy javob"), tr("Uyqu rejimi")];
  const vals = [s.kinds.ai, s.kinds.faq, s.kinds.static, s.kinds.sleep];
  let cumulative = 0;
  const gradient = vals.map((v, i) => {
    const start = cumulative;
    cumulative += s.sent ? v / s.sent * 100 : 0;
    return `${colors[i]} ${start}% ${cumulative}%`;
  }).join(',');
  return `<div class="donut-area"><div class="donut" style="background:${s.sent ? `conic-gradient(${gradient})` : 'var(--line)'}"><div class="donut-text"><strong>${num(s.sent)}</strong><small>${tr("jami javoblar")}</small></div></div><div class="breakdown">${names.map((n, i) => `<div><i style="background:${colors[i]}"></i>${n}<strong>${num(vals[i])}</strong></div>`).join('')}</div></div>`;
}
function dashboard() {
  return head(`${tr("Salom, {0}", {
    0: e(state.user.first_name)
  })} <span style="font-size:24px">☀️</span>`, tr("Sizning vaqtingiz qadrli. Muloqotlaringiz esa ishonchli qo‘llarda."), `<div class="button-group"><a class="button" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${icon('external')}${tr("Botni ochish")}</a>${button(tr("Javobni sinash"), 'test', 'send', 'primary')}</div>`) + `<section class="welcome-card"><div><div class="welcome-label"><i></i> ${tr("SIZNING SHAXSIY YORDAMCHINGIZ")}</div><h2>${tr("Siz band bo‘lsangiz ham, aloqada qoling.")}</h2><p>${tr("Avtojavoblar, aqlli yordamchi va rejalashtirilgan xabarlar.")}<br>${tr("Mijozlaringizning hech bir murojaati e’tiborsiz qolmasin.")}</p><a href="#replies">${tr("Avtojavobni sozlash")} ${icon('arrow')}</a></div><div class="status-control"><div><strong>${tr("Avtojavob {0}", {
    0: state.settings.offline ? tr("yoqilgan") : tr("o‘chirilgan")
  })}</strong><small>${state.settings.offline ? tr("Offline holatda javob beradi") : tr("Online — oddiy avtojavob yo‘q")}</small></div>${switchControl('offline', tr("Avtojavobni yoqish"))}</div></section><section class="stats">${stat(tr("Kelgan xabarlar"), num(summary.incoming), 'inbox', `<span class="positive">↗ ${period === 1 ? tr("Bugun") : `${tr("So‘nggi {0} kun", {
    0: period
  })}`}</span> ${mode === 'demo' ? tr("namuna") : tr("jami xabarlar")}`)}${stat(tr("Yuborilgan javoblar"), num(summary.sent), 'send', `<span class="positive">${tr("Muvaffaqiyatli")}</span> ${tr("yuborilgan")}`)}${stat(tr("AI javoblari"), num(summary.kinds.ai), 'sparkles', tr("Gemini yordamida yuborilgan"))}${stat(tr("Eng faol vaqt"), summary.peak ? `${String(summary.peak[0]).padStart(2, '0')}:00` : '—', 'clock', summary.peak ? `${tr("{0}:00 – {1}:00 oralig‘i", {
    0: String(summary.peak[0]).padStart(2, '0'),
    1: String(summary.peak[1]).padStart(2, '0')
  })}` : tr("Hozircha ma’lumot yo‘q"))}</section><div class="dashboard-grid"><section class="card"><div class="card-head"><h2>${tr("Xabarlar faolligi")}</h2>${periodButtons()}</div><p class="card-desc">${tr("Muloqotlaringiz qanday kechayotganini kuzating.")}</p><div class="chart-legend"><span><b></b>${tr("Kelgan xabarlar")}</span><span><b></b>${tr("Yuborilgan javoblar")}</span></div>${chart(summary)}<div class="chart-footer"><span>${tr("Har bir xabar — yangi imkoniyat.")}</span><a class="green-link" href="#analytics">${tr("Batafsil statistika ↗")}</a></div></section><section class="card"><div class="card-head"><h2>${tr("Javoblar taqsimoti")}</h2><span class="badge gray">${period === 1 ? tr("Bugun") : `${tr("{0} kun", {
    0: period
  })}`}</span></div><p class="card-desc">${tr("Sizga qaysi yordamchi ko‘proq ko‘maklashmoqda?")}</p>${donut(summary)}<div class="note">${icon('shield')} ${tr("Statistika xabarlar matnini saqlamaydi. Faqat umumiy hisoblagichlar.")}</div></section></div><section class="card"><div class="card-head"><h2>${tr("Tezkor amallar")}</h2><span class="subtitle">${tr("Bir qadamda boshqaring")}</span></div><div class="quick-grid">${[['replies', 'message', tr("Javob matni"), tr("Xabaringizni tahrirlang")], ['ai', 'sparkles', tr("AI yordamchi"), tr("Aqlli muloqotni sozlang")], ['faq', 'book', tr("Yangi FAQ"), tr("Tayyor javob qo‘shing")], ['scheduler', 'calendar', tr("Jadval qo‘shish"), tr("Vaqtni rejalashtiring")]].map(([href, ic, t, s]) => `<a class="quick-item" href="#${href}"><span class="quick-icon">${icon(ic)}</span><div><strong>${t}</strong><small>${s}</small></div><span>↗</span></a>`).join('')}</div></section><div class="lower-grid"><section class="card"><div class="card-head"><h2>${tr("Avtomatlashtirish holati")}</h2><a class="green-link" href="#settings">${tr("Boshqarish ↗")}</a></div>${featureRow('sparkles', tr("AI yordamchi"), tr("Mijoz tilida, sizning nomingizdan"), switchControl('ai_enabled', tr("AI yordamchi")))}${featureRow('moon', tr("Uyqu rejimi"), `${time(state.settings.sleep_start_minutes)} — ${time(state.settings.sleep_end_minutes)} · ${e(state.settings.name_clock_tz || 'Asia/Tashkent')}`, switchControl('sleep_mode_enabled', tr("Uyqu rejimi")))}${featureRow('calendar', tr("Smart jadval"), `${tr("{0} ta faol jadval", {
    0: state.schedules.filter(r => r.is_enabled).length
  })}`, switchControl('scheduler_enabled', tr("Smart jadval")))}</section><section class="card"><div class="card-head"><h2>${tr("Sizning hisobingiz")}</h2><span class="badge purple">${e(state.plan.toUpperCase())}</span></div>${featureRow('shield', 'Telegram Business', state.connection?.is_enabled ? tr("Hisob ulangan, javob berishga tayyor") : tr("Hali ulanmagan"), `<span class="badge ${state.connection?.is_enabled ? '' : 'gray'}">${state.connection?.is_enabled ? tr("Ulangan") : tr("Ulanmagan")}</span>`)}${featureRow('sparkles', tr("AI kunlik limiti"), `${tr("{0} / 50 ta javob", {
    0: state.ai_usage || 0
  })}`, `<a class="button small" href="#ai">${tr("Ko‘rish")}</a>`)}${featureRow('crown', tr("Ko‘proq imkoniyatlar"), tr("Biznesingizga mos tarifni tanlang"), `<a class="green-link" style="margin-left:auto" href="#plans">${tr("Tariflar ↗")}</a>`)}</section></div>`;
}
function preview(text) {
  return `<section class="card"><h2>${tr("Xabar qanday ko‘rinadi?")}</h2><p class="card-desc" style="margin-top:9px">${tr("Telegram’dagi javobingizning oldindan ko‘rinishi.")}</p><div class="preview-phone"><div class="preview-head"><span class="avatar">${e(state.user.first_name[0])}</span><div>${e(state.user.first_name)}<small>${tr("AutoReplyer orqali")}</small></div></div><div class="chat-area"><div class="chat-bubble incoming">${tr("Assalomu alaykum!")}<span class="chat-time">12:40</span></div><div class="chat-bubble" id="reply-preview">${e(text)}<span class="chat-time">12:40 ✓✓</span></div></div></div><p class="note">${tr("Bu oldindan ko‘rinish. Hech kimga xabar yuborilmaydi.")}</p></section>`;
}
function replies() {
  const s = state.settings;
  return head(tr("Avtojavob"), tr("Siz yo‘qligingizda ham suhbatni iliq boshlang.")) + `<div class="form-grid"><form class="card" id="settings-form" data-kind="replies"><h2>${tr("Oddiy avtojavob")}</h2>${featureRow('message', tr("Offline rejimi"), tr("Yoqilganda kelgan xabarlarga javob beriladi."), switchControl('offline', tr("Offline rejimi")))}<label class="field"><span>${tr("Javob matni")} <small>${tr("500 belgigacha")}</small></span><textarea name="auto_reply_text" maxlength="500" data-preview>${e(s.auto_reply_text)}</textarea><small>${tr("Matnni o‘zgartirish Plus, Pro va Ultra tariflarida.")}</small></label><label class="field"><span>${tr("Bir suhbatga takroriy javob oralig‘i")}</span><select name="cooldown_hours">${[[1 / 60, tr("1 daqiqa")], [.5, tr("30 daqiqa")], [1, tr("1 soat")], [3, tr("3 soat")], [6, tr("6 soat")], [12, tr("12 soat")], [24, tr("24 soat")], ...(![1 / 60, .5, 1, 3, 6, 12, 24].includes(s.cooldown_hours) ? [[s.cooldown_hours, `${tr("{0} daqiqa", {
    0: Math.round(s.cooldown_hours * 60)
  })}`]] : [])].map(([v, l]) => `<option value="${v}" ${s.cooldown_hours === v ? 'selected' : ''}>${l}</option>`).join('')}</select><small>${tr("Bir suhbatga juda ko‘p javob yuborilishining oldini oladi.")}</small></label><div class="save-row">${button(tr("Javobni sinash"), 'test', 'send')}<button class="button primary" type="submit">${icon('save')}${tr("Saqlash")}</button></div></form>${preview(s.auto_reply_text)}</div><section class="card" style="margin-top:22px"><h2>${tr("Javob tanlash tartibi")}</h2><p class="hint">${tr("Uyqu rejimi → faol jadval / Offline → mos Smart FAQ → AI yordamchi → oddiy javob. Jadval Online holatda ham ishlashi mumkin.")}</p></section>`;
}
function sleep() {
  const s = state.settings;
  return head(tr("Uyqu rejimi"), tr("Dam oling. Mijozlar qachon qaytishingizni bilib turishadi.")) + `<div class="form-grid"><form class="card" id="settings-form" data-kind="sleep"><h2>${tr("Tungi avtojavob")}</h2>${featureRow('moon', tr("Uyqu rejimi"), tr("Belgilangan vaqtda alohida javob yuboriladi."), switchControl('sleep_mode_enabled', tr("Uyqu rejimi")))}<div class="two-fields"><label class="field"><span>${tr("Boshlanish")}</span><input name="sleep_start_minutes" type="time" value="${time(s.sleep_start_minutes)}" required></label><label class="field"><span>${tr("Tugash")}</span><input name="sleep_end_minutes" type="time" value="${time(s.sleep_end_minutes)}" required></label></div><p class="note">${tr("Vaqt zonasi: {0}. Yarim tundan o‘tuvchi vaqtlar qo‘llab-quvvatlanadi. Boshlanish va tugash teng bo‘lsa, uyqu rejimi faol bo‘lmaydi.", {
    0: e(s.name_clock_tz || 'Asia/Tashkent')
  })}</p><label class="field"><span>${tr("Uyqudagi javob matni")}</span><textarea name="sleep_reply_text" maxlength="500" data-preview>${e(s.sleep_reply_text)}</textarea><small>${tr("Maxsus matn Plus tarifidan boshlab mavjud.")}</small></label><div class="save-row"><button class="button primary" type="submit">${icon('save')}${tr("Saqlash")}</button></div></form>${preview(s.sleep_reply_text)}</div>`;
}
function ai() {
  const s = state.settings;
  return head(tr("AI yordamchi"), tr("Sizning uslubingizda javob beradigan aqlli hamroh."), `<span class="badge purple">GEMINI · ULTRA</span>`) + `<div class="form-grid"><form class="card" id="settings-form" data-kind="ai"><h2>${tr("Yordamchini sozlash")}</h2>${featureRow('sparkles', 'Gemini AI', tr("Javoblar mijoz tilida shakllantiriladi."), switchControl('ai_enabled', 'Gemini AI'))}<label class="field"><span>${tr("Yordamchi roli")}</span></label><div class="role-grid">${[['assistant', tr("Shaxsiy yordamchi")], ['seller', tr("Sotuv menejeri")], ['support', tr("Mijozlarga yordam")], ['friend', tr("Do‘stona suhbatdosh")], ['developer', tr("Dasturchi")], ['business', tr("Rasmiy / biznes")]].map(([k, n]) => `<label class="role-option"><input type="radio" name="ai_role" value="${k}" ${s.ai_role === k ? 'checked' : ''}><span>${n}</span></label>`).join('')}</div><label class="field"><span>${tr("Shaxsiy ko‘rsatmalar")}</span><textarea name="ai_info" maxlength="2000" placeholder="${tr("Qanday ohangda javob bersin? Nimalarni bilishi kerak?")}">${e(s.ai_info)}</textarea><small>${tr("Muhim faktlarni Bilimlar bazasiga kiriting.")}</small></label><div class="save-row"><button class="button primary" type="submit">${icon('save')}${tr("Saqlash")}</button></div></form><div class="form-stack"><section class="card"><h2>${tr("Bugungi foydalanish")}</h2><div class="stat-value">${num(state.ai_usage)} <span style="font-size:14px;color:var(--muted)">${tr("/ 50 javob")}</span></div><div class="progress"><span style="width:${Math.min(100, (state.ai_usage || 0) * 2)}%"></span></div><p class="hint">${tr("Ultra uchun kuniga 50 ta AI javob. Administrator uchun alohida qoida mavjud.")}</p><a class="green-link" href="#knowledge">${tr("Bilimlar bazasini boyitish ↗")}</a></section><section class="card"><h2>${tr("Muloqot qanday ishlaydi?")}</h2><p class="hint">${tr("AI so‘nggi suhbat va bilimlar bazasidan foydalanadi. Siz suhbatga qo‘shilsangiz, yordamchi vaqtincha to‘xtaydi. AI ishlamasa, oddiy javob qo‘llanadi.")}</p><div class="note">${tr("AI ishlatilganda xabarlar Google Gemini’ga yuboriladi. AI muhim ma’lumotlarda xato qilishi mumkin.")}</div></section></div></div>`;
}
function entries(kind) {
  const kb = kind === 'knowledge',
    items = state[kb ? 'knowledge' : 'faq'];
  return head(kb ? tr("Bilimlar bazasi") : 'Smart FAQ', kb ? tr("Biznesingiz haqidagi faktlar yordamchingizning xotirasida.") : tr("Ko‘p so‘raladigan savollarga aniq va tezkor javoblar."), button(kb ? tr("Ma’lumot qo‘shish") : tr("Savol qo‘shish"), `add-${kind}`, 'plus', 'primary')) + `<section class="card"><div class="card-head"><h2>${kb ? tr("Shaxsiy ma’lumotlar") : tr("Savol-javoblar")} <span class="badge gray">${items.length} / ${kb ? 55 : {
    free: 0,
    plus: 15,
    pro: 30,
    ultra: 65
  }[state.plan] || 0}</span></h2><div class="button-group"><span class="subtitle">${kb ? tr("AI uchun kontekst") : tr("Avtomatik javoblar")}</span>${switchControl(kb ? 'kb_enabled' : 'faq_enabled', kb ? tr("Bilimlar bazasi") : 'Smart FAQ')}</div></div><p class="card-desc">${kb ? tr("Faktlar javob uchun kontekst bo‘ladi. Ular alohida xabar yubormaydi.") : tr("Kalit so‘zga mos savol topilsa, bot AI’dan oldin tayyor javobni yuboradi.")}</p><div class="list-toolbar"><input class="search" type="text" id="entry-search" placeholder="${tr("{0} qidirish…", {
    0: kb ? tr("Ma’lumot") : tr("Savol yoki kalit so‘z")
  })}" aria-label="${tr("Qidirish")}"><span class="badge ${kb ? 'purple' : 'gray'}">${kb ? 'ULTRA' : tr("PLUS VA YUQORI")}</span></div><div id="entry-list">${items.map(item => entryHTML(item, kind)).join('') || `<div class="empty">${icon('book')}<h3>${kb ? tr("Birinchi ma’lumotni qo‘shing") : tr("Birinchi savolni qo‘shing")}</h3><p>${kb ? tr("Ish vaqti, xizmatlar yoki biznesingiz haqida yozing.") : tr("Mijozlaringiz nimani ko‘p so‘rashadi?")}</p></div>`}</div><p class="hint" id="no-results" hidden>${tr("Qidiruvga mos natija topilmadi.")}</p></section>`;
}
function entryHTML(item, kind) {
  const kb = kind === 'knowledge';
  return `<article class="entry" data-search="${e([item.question, item.title, item.answer, item.content, ...item.keywords].join(' ').toLowerCase())}"><div class="entry-title"><h3>${e(kb ? item.title : item.question)}</h3><span class="badge ${item.is_enabled ? '' : 'gray'}">${item.is_enabled ? tr("Faol") : tr("Pauzada")}</span></div><p>${e(kb ? item.content : item.answer)}</p><div class="chips">${item.keywords.map(k => `<span class="chip">${e(k)}</span>`).join('')}</div><div class="entry-actions">${button(tr("Tahrirlash"), `edit-${kind}:${item.id}`, 'edit', 'small')}${button(tr("O‘chirish"), `delete-${kind}:${item.id}`, 'trash', 'small danger')}<label class="switch"><input type="checkbox" aria-label="${tr("{0} holati", {
    0: e(kb ? item.title : item.question)
  })}" data-toggle="${kind}:${item.id}" ${item.is_enabled ? 'checked' : ''}><span></span></label></div></article>`;
}
function scheduler() {
  return head(tr("Smart jadval"), tr("Javoblar kerakli vaqtda, har hafta avtomatik ishga tushadi."), button(tr("Jadval qo‘shish"), 'add-schedule', 'plus', 'primary')) + `<section class="card"><div class="card-head"><h2>${tr("Haftalik jadvallar")} <span class="badge gray">${state.schedules.length} / ${{
    free: 1,
    plus: 3,
    pro: 10,
    ultra: 30
  }[state.plan]}</span></h2><div class="button-group"><span class="subtitle">${tr("Jadvallarni ishlatish")}</span>${switchControl('scheduler_enabled', tr("Jadvallarni ishlatish"))}</div></div><p class="card-desc">${tr("{0} · Uyqu rejimi jadvaldan ustun turadi. Kesishuvchi jadvallarga ruxsat berilmaydi.", {
    0: e(state.settings.name_clock_tz || 'Asia/Tashkent')
  })}</p><div class="lower-grid">${state.schedules.map(r => `<article class="entry"><div class="entry-title"><h3>${days.filter((_, i) => r.days & 1 << i).join(' · ')}</h3><span class="badge ${r.is_enabled ? '' : 'gray'}">${r.is_enabled ? tr("Faol") : tr("Pauzada")}</span></div><div class="schedule-time">${r.start_min === 0 && r.end_min === 1440 ? tr("Kun bo‘yi") : `${time(r.start_min)} — ${time(r.end_min)}`}</div><p>${e(r.text || tr("Standart avtojavob matni"))}</p>${r.end_min < r.start_min ? `<span class="chip">${tr("Keyingi kunga o‘tadi")}</span>` : ''}<div class="entry-actions">${button(tr("Tahrirlash"), `edit-schedule:${r.id}`, 'edit', 'small')}${button(tr("O‘chirish"), `delete-schedule:${r.id}`, 'trash', 'small danger')}<label class="switch"><input type="checkbox" data-toggle="schedule:${r.id}" aria-label="${tr("Jadval holati")}" ${r.is_enabled ? 'checked' : ''}><span></span></label></div></article>`).join('') || `<div class="empty">${icon('calendar')}<h3>${tr("Hali jadval yo‘q")}</h3><p>${tr("Ish yoki dam olish vaqtlaringiz uchun yangi jadval yarating.")}</p></div>`}</div></section><div class="note" style="margin-top:18px">${tr("API orqali saqlangan jadvallar botda kesh yangilangach, odatda 60 soniya ichida ko‘rinadi.")}</div>`;
}
function analytics() {
  return head(tr("Statistika"), tr("Xabarlar va avtojavoblar haqida aniq tasavvur."), periodButtons()) + `<div class="stats">${stat(tr("Kelgan xabarlar"), num(summary.incoming), 'inbox', tr("Jami kuzatilgan xabarlar"))}${stat(tr("Yuborilgan javoblar"), num(summary.sent), 'send', tr("Muvaffaqiyatli javoblar"))}${stat(tr("Kunlik o‘rtacha"), num(Math.round(summary.incoming / period)), 'chart', tr("Kiruvchi xabarlar"))}${stat(tr("Cooldown tufayli o‘tkazilgan"), summary.skipped === null ? 'Ultra' : num(summary.skipped), 'clock', tr("Takroriy javob cheklovi"))}</div><div class="dashboard-grid"><section class="card"><div class="card-head"><h2>${tr("Xabarlar faolligi")}</h2><span class="badge gray">${tr("{0} kun", {
    0: period
  })}</span></div><div class="chart-legend"><span><b></b>${tr("Kelgan xabarlar")}</span><span><b></b>${tr("Yuborilgan javoblar")}</span></div>${chart(summary)}</section><section class="card"><h2>${tr("Javoblar taqsimoti")}</h2>${donut(summary)}</section></div><section class="card"><h2>${tr("Raqamlar nimani anglatadi?")}</h2><p class="hint">${tr("Kiruvchi xabarlar noyob foydalanuvchilar soni emas. Har bir xabarga javob yuborilishi kafolatlanmaydi: Online rejimi, cooldown va ruxsatlar ta’sir qiladi. Statistika ishga tushirilishidan oldingi suhbatlar hisoblanmaydi.")}</p><p class="note">${tr("{0} Statistika faqat jamlangan hisoblagichlarni saqlaydi. AI suhbat tarixi alohida saqlanadi.", {
    0: mode === 'demo' ? tr("Demo: raqamlar namunaviy.") : tr("Hisoblagichlar kechikib yangilanishi mumkin.")
  })}</p></section>`;
}
function profile() {
  return head(tr("Profil vositalari"), tr("Telegram profilingizni bot orqali bezang.")) + `<div class="form-grid"><section class="card"><h2>${tr("Ism soati")}</h2>${featureRow('clock', tr("Profil nomida vaqt"), tr("Botdagi davriy vazifa bilan yangilanadi."), `<span class="badge ${state.settings.name_clock_enabled ? '' : 'gray'}">${state.settings.name_clock_enabled ? tr("Yoqilgan") : tr("O‘chiq")}</span>`)}<p class="hint">${tr("Ism, shrift va vaqt zonasini sozlash uchun botning “Ism soati” bo‘limidan foydalaning. Bot akkaunt nomini tahrirlash ruxsatini tekshiradi.")}</p><div class="preview-phone" style="text-align:center"><div class="stat-value">${e(state.user.first_name)} <span id="clock-preview">${new Date().toLocaleTimeString(getLocale(), {
    timeZone: state.settings.name_clock_tz || 'Asia/Tashkent',
    hour: '2-digit',
    minute: '2-digit'
  })}</span></div><span class="subtitle">${tr("Ko‘rinish namunasi")}</span></div><a class="button primary" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${icon('external')}${tr("Botda sozlash")}</a></section><section class="card"><h2>${tr("BIO hisoblagich")}</h2><p class="hint">${tr("Yangi yil, Navro‘z yoki tug‘ilgan kuningizgacha qolgan kunlar profilingizda. Pro va Ultra tariflarida mavjud.")}</p><div class="preview-phone"><div class="chat-bubble">${tr("🌷 Navro‘zgacha {0} kun qoldi.", {
    0: Math.ceil((new Date(new Date().getFullYear() + (new Date() > new Date(new Date().getFullYear(), 2, 21) ? 1 : 0), 2, 21) - new Date()) / 86400000)
  })}</div></div><p class="note">${tr("BIO’ni tahrirlash uchun Telegram Business ruxsati kerak. Tadbir va tug‘ilgan kun bot ichida tanlanadi.")}</p><a class="button" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${icon('external')}${tr("Botda sozlash")}</a></section></div>`;
}
function plans() {
  return head(tr("Sizga mos tarif"), tr("Kichik qadamdan katta imkoniyatlargacha.")) + `<div class="plans-grid">${[['free', 'Free', '0', [tr("Oddiy avtojavob va uyqu rejimi"), tr("1 ta haftalik jadval"), tr("Bugungi statistika"), tr("Standart ism soati")]], ['plus', 'Plus', '2 000', [tr("15 ta Smart FAQ"), tr("3 ta haftalik jadval"), tr("Shaxsiy javob matnlari"), tr("7 kunlik statistika"), tr("Reklamasiz foydalanish")]], ['pro', 'Pro', '5 000', [tr("30 ta Smart FAQ"), tr("10 ta haftalik jadval"), tr("30 kunlik statistika"), tr("BIO hisoblagich"), tr("Qo‘shimcha vaqt zonalari")]], ['ultra', 'Ultra', '10 000', [tr("65 ta Smart FAQ"), tr("30 ta haftalik jadval"), tr("Kuniga 50 ta AI javob"), tr("55 ta bilimlar yozuvi"), tr("Barcha statistika grafiklari"), tr("Qo‘shimcha soat shriftlari")]]].map(([key, title, price, features]) => `<section class="card plan-card ${key === 'ultra' ? 'recommended' : ''}"><div class="card-head"><h2>${title}</h2>${state.plan === key ? `<span class="badge">${tr("Joriy tarif")}</span>` : ''}</div><div class="price">${price}<small> ${tr("so‘m")}</small></div><span class="subtitle">${tr("oyiga")}</span><ul>${features.map(f => `<li>${f}</li>`).join('')}</ul><a class="button ${key === 'ultra' ? 'primary' : ''}" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${tr("Botda ko‘rish ↗")}</a></section>`).join('')}</div><p class="note" style="margin-top:22px">${tr("Tarif bot ichida to‘lov tasdig‘ini administratorga yuborish orqali faollashtiriladi. Yakuniy narx va amaldagi tarifni botdan tekshiring.")}</p>`;
}
function settings() {
  return head(tr("Sozlamalar"), tr("Hisobingiz va Web App ulanishini boshqaring.")) + `<div class="form-grid"><div class="form-stack"><section class="card"><h2>Telegram Business</h2>${featureRow('shield', tr("Hisob holati"), mode === 'live' ? state.connection?.is_enabled ? tr("Telegram Business ulangan") : tr("Business hisobini botga ulang") : tr("Hozir namoyish hisobi ochilgan"), `<span class="badge ${mode === 'live' ? '' : 'gray'}">${mode === 'live' ? tr("Haqiqiy hisob") : tr("Demo")}</span>`)}<p class="hint">${tr("Telegram → Sozlamalar → Telegram Business → Chatbotlar → @autoreplyer_dbot. Xabarlarga javob berish ruxsatini bering.")}</p><a class="button" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${icon('external')}${tr("Botni ochish")}</a></section><form class="card" id="connection-form"><h2>${tr("Web App ulanishi")}</h2><label class="field"><span>${tr("API server manzili")}</span><input type="url" name="api" value="${e(apiBase)}" placeholder="https://api.example.com"><small>${tr("Alohida API serveringiz manzili. Web App va API bir serverda bo‘lsa, bo‘sh qoldiring. Bot tokenini bu yerga kiritmang.")}</small></label><p class="note">${tr("Haqiqiy hisobga kirish uchun ilovani Telegram bot menyusidan oching. Telegram tasdiqlagan ma’lumot serverda tekshiriladi.")}</p><div class="save-row"><button class="button primary" type="submit">${icon('shield')}${tr("Ulanishni tekshirish")}</button></div></form></div><div class="form-stack"><section class="card"><h2>${tr("Ko‘rinish")}</h2>${featureRow('moon', tr("Tungi rang mavzusi"), tr("Qurilmada saqlanadi."), button(tr("Almashtirish"), 'theme', 'moon', 'small'))}${featureRow('globe', tr("Interfeys tili"), tr("Tanlov shu qurilmada saqlanadi."), languageSelector("settings-language"))}</section><section class="card"><h2>${tr("Ma’lumotlar")}</h2><p class="hint">${mode === 'demo' ? tr("Demo sozlamalari faqat shu brauzerda saqlanadi. Ular haqiqiy botingizga ta’sir qilmaydi.") : tr("Sozlamalar Telegram hisobingiz bilan bog‘langan umumiy bot bazasiga saqlanadi.")}</p>${mode === 'demo' ? button(tr("Demo ma’lumotlarini tiklash"), 'reset-demo', 'reply') : `<span class="badge">${tr("Telegram orqali tasdiqlangan")}</span>`}</section></div></div>`;
}
function help() {
  return head(tr("Boshlash oson"), tr("AutoReplyer’ni Telegram Business hisobingizga ulang.")) + `<div class="form-grid"><section class="card"><h2>${tr("Uch qadamda tayyor")}</h2>${[[tr("Botni ishga tushiring"), tr("@autoreplyer_dbot’ni ochib /start yuboring. Tilni tanlab boshlang.")], [tr("Telegram Business orqali ulang"), tr("Telegram Sozlamalar → Telegram Business → Chatbotlar bo‘limida @autoreplyer_dbot’ni tanlang. Xabarlarga javob berish ruxsatini yoqing.")], [tr("Avtojavobni yoqing va sinang"), tr("Offline rejimini yoqing. Boshqa Telegram hisobidan sizga xabar yuborib, haqiqiy javobni tekshiring.")]].map(([t, p], i) => `<div class="help-step"><span class="step-number">${i + 1}</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join('')}<a class="button primary" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${tr("Telegram’da boshlash ↗")}</a></section><section class="card"><h2>${tr("Foydali havolalar")}</h2>${featureRow('message', tr("Yordam va takliflar"), tr("Botning yordam bo‘limi"), `<a class="button small" href="https://t.me/autoreplyer_dbot" target="_blank" rel="noopener">${tr("Ochish ↗")}</a>`)}${featureRow('sparkles', tr("Yangiliklar"), tr("AutoReplyer yangilanishlari"), `<a class="button small" href="https://t.me/AutoReplyer_News" target="_blank" rel="noopener">${tr("Ochish ↗")}</a>`)}${featureRow('book', tr("Loyiha hujjatlari"), tr("GitHub’dagi qo‘llanma"), `<a class="button small" href="https://github.com/TheBigChanges/AutoReplyer" target="_blank" rel="noopener">GitHub ↗</a>`)}<p class="note" style="margin-top:22px">${tr("Bu Web App alohida loyiha. Mavjud AutoReplyer kodi o‘zgartirilmagan.")}</p></section></div>`;
}
function render() {
  const route = location.hash.slice(1) || 'dashboard';
  const key = `${route}:${mode}:${state.user.id}`;
  const drafts = renderedKey === key ? captureDrafts() : [];
  const busyForms = renderedKey === key ? [...document.querySelectorAll('#main form')].filter(form => pendingForms.has(form)) : [];
  renderedKey = key;
  translateChrome();
  document.querySelector('#language-control').innerHTML = languageSelector('header-language');
  days = weekDays();
  const navigation = navigationKeys.map(([key, ic, label, badge]) => [key, ic, tr(label), badge]);
  page = location.hash.slice(1) || 'dashboard';
  if (![...navigation.map(n => n[0]), 'plans', 'help'].includes(page)) page = 'dashboard';
  const label = navigation.find(n => n[0] === page)?.[2] || {
    plans: tr("Tariflar"),
    help: tr("Yordam markazi")
  }[page];
  document.title = `${label} — AutoReplyer`;
  document.querySelector('#crumb').textContent = label;
  document.querySelector('#account-label').textContent = mode === 'live' ? `${state.user.first_name} · ${state.plan.toUpperCase()}` : tr("Namoyish hisobi");
  document.querySelector('.top-actions .avatar').textContent = state.user.first_name[0];
  document.querySelector('#navigation').innerHTML = navigation.map(([key, ic, t, b], i) => `${i === 8 ? `<div class="nav-divider"></div>` : ''}<a href="#${key}" class="${page === key ? 'active' : ''}" ${page === key ? 'aria-current="page"' : ''}>${icon(ic)}${t}${b ? `<span class="nav-badge">${b}</span>` : ''}</a>`).join('');
  updateMobileNavigation(document.querySelector('#mobile-nav'), [navigation[0], navigation[1], navigation[5], navigation[6], navigation[9]].map(([key, ic, t]) => `<a href="#${key}" class="${page === key ? 'active' : ''}">${icon(ic)}<span class="mobile-nav-label">${key === 'dashboard' ? tr("Asosiy") : key === 'scheduler' ? tr("Jadval") : t}</span></a>`).join(''));
  const banner = document.querySelector('#mode-banner');
  banner.classList.toggle('live', mode === 'live');
  banner.innerHTML = mode === 'live' ? `<span>${icon('shield')}<strong>${tr("Telegram orqali tasdiqlangan")}</strong><span class="demo-note">${tr("— o‘zgarishlar bot hisobingizga saqlanadi.")}</span></span><a href="#settings">${tr("Hisob ↗")}</a>` : mode === 'error' ? `<span>${icon('shield')}<strong>${tr("Botga ulanish talab etiladi")}</strong></span><a href="#settings">${tr("Ulanishni sozlash ↗")}</a>` : `<span>${icon('flask')}<strong>${tr("Demo rejim")}</strong><span class="demo-note">${tr("— namunaviy ma’lumotlar. O‘zgarishlar faqat shu qurilmada saqlanadi.")}</span></span><a href="#settings">${tr("Botni ulash ↗")}</a>`;
  if (mode === 'loading') {
    document.querySelector('#main').innerHTML = `<div class="empty">${tr("Telegram hisobingiz tekshirilmoqda…")}</div>`;
    return;
  }
  if (mode === 'error' && page !== 'settings' && page !== 'help') {
    document.querySelector('#main').innerHTML = head(tr("Hisobga ulanish"), tr("Haqiqiy sozlamalarni ochish uchun API bilan ulaning.")) + `<section class="card empty">${icon('shield')}<h3>${tr("API bilan aloqa o‘rnatilmadi")}</h3><p>${tr("API manzilini sozlang yoki demo rejimini tanlab ilovani ko‘rib chiqing.")}</p><div class="button-group" style="justify-content:center"><a class="button primary" href="#settings">${tr("Ulanishni sozlash")}</a>${button(tr("Demoni ochish"), 'enter-demo', 'flask')}</div></section>`;
    animatePage(document.querySelector('#main'), `${page}:${getLanguage()}:error`);
    return;
  }
  if (mode === 'demo') summary = demoSummary();
  document.querySelector('#main').innerHTML = {
    dashboard,
    replies,
    sleep,
    ai,
    faq: () => entries('faq'),
    knowledge: () => entries('knowledge'),
    scheduler,
    analytics,
    profile,
    plans,
    settings,
    help
  }[page]();
  if (page === 'settings') document.querySelector('#main').insertAdjacentHTML('beforeend', `<section class="card mobile-sections" style="margin-top:20px"><h2>${tr("Barcha bo‘limlar")}</h2><div class="quick-grid">${[...navigation, ['plans', 'crown', tr("Tariflar")], ['help', 'help', tr("Yordam markazi")]].filter(n => n[0] !== 'settings').map(([key, ic, t]) => `<a class="quick-item" href="#${key}"><span class="quick-icon">${icon(ic)}</span><strong>${t}</strong><span>↗</span></a>`).join('')}</div></section>`);
  for (const form of busyForms) document.getElementById(form.id)?.replaceWith(form);
  restoreDrafts(drafts);
  paintIcons();
  animatePage(document.querySelector('#main'), `${page}:${getLanguage()}`);
}
function captureDrafts() {
  return [...document.querySelectorAll('#main form [name]')].map(el => ({
    form: el.form.id, name: el.name, value: el.value, checked: el.checked, type: el.type,
    focused: document.activeElement === el, start: el.selectionStart, end: el.selectionEnd
  }));
}
function restoreDrafts(drafts) {
  for (const draft of drafts) {
    const form = document.getElementById(draft.form);
    const field = [...(form?.elements || [])].find(el => el.name === draft.name && (!['radio', 'checkbox'].includes(draft.type) || el.value === draft.value));
    if (!field) continue;
    if (['radio', 'checkbox'].includes(draft.type)) field.checked = draft.checked; else field.value = draft.value;
    if (draft.focused) {
      field.focus({preventScroll: true});
      if (typeof draft.start === 'number' && typeof field.setSelectionRange === 'function') field.setSelectionRange(draft.start, draft.end);
    }
  }
  const preview = document.querySelector('#reply-preview');
  const editor = document.querySelector('[data-preview]');
  if (preview && editor) preview.textContent = editor.value;
}
function modal(content) {
  document.querySelector('#modal-content').innerHTML = content;
  showDialog(document.querySelector('#modal'));
}
function modalHead(title) {
  return `<div class="modal-head"><h2>${title}</h2><button class="icon-button" data-action="close-modal" aria-label="${tr("Yopish")}">${icon('close')}</button></div>`;
}
function editor(kind, id) {
  const schedule = kind === 'schedule',
    kb = kind === 'knowledge',
    collection = schedule ? 'schedules' : kind;
  const item = state[collection].find(r => r.id === Number(id)) || {};
  modal(`${modalHead(id ? tr("Tahrirlash") : schedule ? tr("Yangi jadval") : kb ? tr("Yangi ma’lumot") : tr("Yangi savol-javob"))}<form id="entry-form" data-kind="${kind}" data-id="${id || ''}">${schedule ? `<label class="field"><span>${tr("Hafta kunlari")}</span></label><div class="day-picker">${days.map((d, i) => `<label><input type="checkbox" name="day" value="${i}" ${(item.days ?? 31) & 1 << i ? 'checked' : ''}><span>${d}</span></label>`).join('')}</div><div class="two-fields"><label class="field"><span>${tr("Boshlanish")}</span><input type="time" name="start" value="${time(item.start_min ?? 540)}" required></label><label class="field"><span>${tr("Tugash")}</span><input type="time" name="end" value="${time(item.end_min === 1440 ? 0 : item.end_min ?? 1080)}" required></label></div><p class="hint">${tr("Kun bo‘yi uchun ikkala vaqtni ham 00:00 qiling.")}</p><label class="field"><span>${tr("Maxsus javob (ixtiyoriy)")}</span><textarea name="text" maxlength="500" placeholder="${tr("Bo‘sh qoldirsangiz, standart matn ishlatiladi.")}">${e(item.text)}</textarea><small>${tr("Free tarifida standart matn qo‘llanadi.")}</small></label>` : `<label class="field"><span>${kb ? tr("Sarlavha") : tr("Savol")}</span><input type="text" name="title" maxlength="${kb ? 100 : 200}" value="${e(kb ? item.title : item.question)}" required></label><label class="field"><span>${tr("Kalit so‘zlar")}</span><input type="text" name="keywords" value="${e((item.keywords || []).join(', '))}" placeholder="${tr("ish vaqti, soat nechada")}" required><small>${tr("Vergul bilan ajrating. Ko‘pi bilan 10 ta, har biri 40 belgigacha.")}</small></label><label class="field"><span>${kb ? tr("Ma’lumot") : tr("Tayyor javob")}</span><textarea name="content" maxlength="1000" required>${e(kb ? item.content : item.answer)}</textarea></label>`}<p class="error-text" id="form-error" role="alert"></p><div class="save-row"><button class="button" type="button" data-action="close-modal">${tr("Bekor qilish")}</button><button class="button primary" type="submit">${icon('save')}${tr("Saqlash")}</button></div></form>`);
}
function segments(r) {
  const out = [];
  for (let i = 0; i < 7; i++) if (r.days & 1 << i) {
    const a = i * 1440 + r.start_min,
      b = i * 1440 + (r.start_min === r.end_min ? 1440 + r.start_min : r.end_min > r.start_min ? r.end_min : 1440 + r.end_min);
    if (b > 10080) {
      out.push([a, 10080], [0, b - 10080]);
    } else out.push([a, b]);
  }
  return out;
}
function overlap(a, b) {
  return segments(a).some(([s, e]) => segments(b).some(([x, y]) => s < y && x < e));
}
function testModal() {
  modal(`${modalHead(tr("Javobni sinab ko‘ring"))}<p class="hint">${tr("Smart FAQ mosligini va oddiy javobni ko‘ring. Bu sinov hech kimga xabar yubormaydi, AI so‘rovi bajarmaydi.")}</p><form id="test-form"><label class="field"><span>${tr("Mijoz xabari")}</span><input type="text" name="message" placeholder="${tr("Ish vaqtingiz qanday?")}" maxlength="1000" required></label><button class="button primary" type="submit">${icon('send')}${tr("Sinash")}</button></form><div id="test-result" style="margin-top:20px"></div>`);
}
document.addEventListener('click', async event => {
  const el = event.target.closest('[data-action],[data-period]');
  if (!el) return;
  const action = el.dataset.action;
  let busy = false;
  try {
    if (el.dataset.period) {
      const value = Number(el.dataset.period);
      if (mode === 'live') {
        await refreshSummary(value);
      } else {
        period = value;
        render();
      }
      return;
    }
    if (action === 'close-modal') {
      await closeDialog(document.querySelector('#modal'));
      return;
    }
    if (action === 'theme') {
      theme();
      return;
    }
    if (action === 'test') {
      testModal();
      return;
    }
    if (action === 'enter-demo') {
      connectionRequest++;
      summaryRequest++;
      mode = 'demo';
      state = structuredClone(seed);
      render();
      return;
    }
    if (action === 'reset-demo') {
      modal(`${modalHead(tr("Demo ma’lumotlarini tiklash"))}<p class="hint">${tr("Shu qurilmadagi demo o‘zgarishlari o‘chiriladi va dastlabki namuna tiklanadi.")}</p><div class="save-row">${button(tr("Bekor qilish"), 'close-modal', 'close')}${button(tr("Tiklash"), 'confirm-reset', 'reply', 'primary')}</div>`);
      return;
    }
    if (action === 'confirm-reset') {
      state = structuredClone(seed);
      persist();
      await closeDialog(document.querySelector('#modal'));
      render();
      toast(tr("Demo tiklandi"));
      return;
    }
    if (action?.startsWith('add-')) {
      if (!['demo', 'live'].includes(mode)) return;
      editor(action.slice(4));
      return;
    }
    if (action?.startsWith('edit-')) {
      const [kind, id] = action.slice(5).split(':');
      editor(kind, id);
      return;
    }
    if (action?.startsWith('delete-')) {
      const [kind, id] = action.slice(7).split(':');
      modal(`${modalHead(tr("Yozuvni o‘chirish"))}<p class="hint">${tr("Ushbu yozuv o‘chiriladi. Davom etasizmi?")}</p><div class="save-row">${button(tr("Bekor qilish"), 'close-modal', 'close')}${button(tr("O‘chirish"), `confirm-delete:${kind}:${id}`, 'trash', 'danger')}</div>`);
      return;
    }
    if (action?.startsWith('confirm-delete:')) {
      if (el.disabled) return;
      busy = true;
      el.disabled = true;
      el.setAttribute('aria-busy', 'true');
      const [, kind, id] = action.split(':');
      if (mode === 'live') await api(`/api/${kind}/${id}`, 'DELETE');
      const key = kind === 'schedule' ? 'schedules' : kind;
      state[key] = state[key].filter(r => r.id !== Number(id));
      persist();
      if (el.isConnected) await closeDialog(document.querySelector('#modal'));
      render();
      toast(tr("Yozuv o‘chirildi"));
    }
  } catch (err) {
    toast(err.message);
  } finally {
    if (busy) {
      el.disabled = false;
      el.removeAttribute('aria-busy');
    }
  }
});
async function changeLanguage(value) {
  if (!normalizeLanguage(value) || value === getLanguage()) return;
  // Preserve unsaved text while rebuilding labels in the chosen language.
  setLanguage(value, true);
  render();
  toast(tr('Til saqlandi'));
}
document.addEventListener('change', async event => {
  const el = event.target;
  if (!el.dataset.setting && !el.dataset.toggle) return;
  if (!['demo', 'live'].includes(mode)) return;
  el.disabled = true;
  try {
    if (el.dataset.setting) await saveSettings({
      [el.dataset.setting]: el.checked
    });else {
      const [kind, id] = el.dataset.toggle.split(':');
      const key = kind === 'schedule' ? 'schedules' : kind;
      const result = mode === 'live' ? await api(`/api/${kind}/${id}/toggle`, 'POST') : null;
      state[key].find(r => r.id === Number(id)).is_enabled = result?.is_enabled ?? el.checked;
      persist();
    }
    render();
    toast(mode === 'demo' ? tr("Demo qurilmada saqlandi") : tr("Bot sozlamalari saqlandi"));
  } catch (err) {
    el.checked = !el.checked;
    toast(err.message);
  } finally {
    el.disabled = false;
  }
});
document.addEventListener('input', event => {
  const el = event.target;
  if (el.hasAttribute('data-preview')) {
    const preview = document.querySelector('#reply-preview');
    if (preview) preview.textContent = el.value;
  }
  if (el.id === 'entry-search') {
    let visible = 0;
    document.querySelectorAll('[data-search]').forEach(row => {
      row.hidden = !row.dataset.search.includes(el.value.toLowerCase());
      if (!row.hidden) visible++;
    });
    document.querySelector('#no-results').hidden = visible > 0;
  }
});
document.addEventListener('submit', async event => {
  const form = event.target;
  if (!['settings-form', 'entry-form', 'connection-form', 'test-form'].includes(form.id)) return;
  event.preventDefault();
  if (pendingForms.has(form)) return;
  if (form.id !== 'connection-form' && !['demo', 'live'].includes(mode)) return;
  pendingForms.add(form);
  const submittedLanguage = getLanguage();
  const submit = form.querySelector('[type=submit]');
  submit.disabled = true;
  submit.setAttribute('aria-busy', 'true');
  try {
    const data = new FormData(form);
    if (form.id === 'connection-form') {
      let value;
      try { value = await trustedApiBase(data.get('api')); }
      catch { throw Error(tr("API manzili ishonchli ro‘yxatda yo‘q. Administrator bilan bog‘laning.")); }
      apiBase = value;
      localStorage.setItem('ar-api', value);
      if (!tg?.initData) {
        toast(tr("API manzili saqlandi. Haqiqiy hisobga kirish uchun Telegram’dan oching."));
        return;
      }
      await loadLive();
      toast(tr("Telegram hisobiga ulandi"));
      return;
    }
    if (form.id === 'settings-form') {
      let values = Object.fromEntries(data);
      if (form.dataset.kind === 'replies') values.cooldown_hours = Number(values.cooldown_hours);
      if (form.dataset.kind === 'sleep') {
        values.sleep_start_minutes = minutes(values.sleep_start_minutes);
        values.sleep_end_minutes = minutes(values.sleep_end_minutes);
      }
      if (mode === 'live' && !['plus', 'pro', 'ultra'].includes(state.plan) && form.dataset.kind === 'replies') delete values.auto_reply_text;
      if (mode === 'live' && state.plan === 'free' && form.dataset.kind === 'sleep') delete values.sleep_reply_text;
      await saveSettings(values);
      toast(mode === 'demo' ? tr("Demo sozlamalari saqlandi") : tr("Sozlamalar botga saqlandi"));
      return;
    }
    if (form.id === 'test-form') {
      let result;
      if (mode === 'live') result = await api('/api/test', 'POST', {
        message: data.get('message')
      });else {
        const text = String(data.get('message')).toLowerCase();
        const found = state.settings.faq_enabled ? state.faq.find(r => r.is_enabled && r.keywords.some(k => text.includes(k.toLowerCase()))) : null;
        result = {
          source: found ? tr("Smart FAQ (demo)") : tr("Oddiy javob (demo)"),
          text: found?.answer || state.settings.auto_reply_text
        };
      }
      if (form.isConnected) form.nextElementSibling.innerHTML = `<span class="badge">${e(result.source)}</span><p class="chat-bubble" style="margin-top:12px">${e(result.text)}</p>`;
      return;
    }
    if (form.id === 'entry-form') {
      const kind = form.dataset.kind,
        id = Number(form.dataset.id) || null,
        key = kind === 'schedule' ? 'schedules' : kind;
      let values;
      if (kind === 'schedule') {
        const mask = data.getAll('day').reduce((a, n) => a | 1 << Number(n), 0);
        if (!mask) throw Error(tr("Kamida bitta kunni tanlang."));
        values = {
          days: mask,
          start_min: minutes(data.get('start')),
          end_min: minutes(data.get('end')),
          text: String(data.get('text')).trim() || null
        };
        if (values.start_min === 0 && values.end_min === 0) values.end_min = 1440;
        if (values.start_min === values.end_min) throw Error(tr("Boshlanish va tugash vaqti teng bo‘lmasin."));
        if (mode === 'demo' && state.schedules.some(r => r.id !== id && overlap(values, r))) throw Error(tr("Bu vaqt boshqa jadval bilan kesishadi."));
      } else {
        const keywords = String(data.get('keywords')).split(',').map(s => s.trim()).filter(Boolean);
        if (!keywords.length || keywords.length > 10 || keywords.some(k => k.length > 40)) throw Error(tr("1–10 ta kalit so‘z kiriting, har biri 40 belgigacha."));
        values = kind === 'faq' ? {
          question: String(data.get('title')).trim(),
          keywords,
          answer: String(data.get('content')).trim()
        } : {
          title: String(data.get('title')).trim(),
          keywords,
          content: String(data.get('content')).trim()
        };
        if (!String(data.get('title')).trim() || !String(data.get('content')).trim()) throw Error(tr("Maydonlarni to‘ldiring."));
      }
      if (mode === 'live') {
        const result = await api(`/api/${kind}${id ? `/${id}` : ''}`, id ? 'PATCH' : 'POST', values);
        if (id) Object.assign(state[key].find(r => r.id === id), values);else state[key].push({
          ...values,
          id: result.id,
          is_enabled: true
        });
      } else {
        const limits = {
          faq: 65,
          knowledge: 55,
          schedule: 30
        };
        if (!id && state[key].length >= limits[kind]) throw Error(tr("Yozuvlar limiti to‘ldi."));
        if (id) Object.assign(state[key].find(r => r.id === id), values);else state[key].push({
          ...values,
          id: Date.now(),
          is_enabled: true
        });
      }
      persist();
      if (form.isConnected) await closeDialog(document.querySelector('#modal'));
      render();
      toast(tr("Saqlandi"));
    }
  } catch (err) {
    const error = form.querySelector('#form-error');
    if (error) error.textContent = err.message;else toast(err.message);
  } finally {
    pendingForms.delete(form);
    submit.disabled = false;
    submit.removeAttribute('aria-busy');
    if (form.isConnected && submittedLanguage !== getLanguage()) render();
  }
});
async function refreshSummary(value = period) {
  const request = ++summaryRequest;
  const s = await api(`/api/analytics?days=${value}`);
  if (request !== summaryRequest || mode !== 'live') return;
  period = value;
  summary = s;
  render();
}
function theme() {
  const dark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('ar-theme', dark ? 'dark' : 'light');
  document.querySelector('#theme-button').innerHTML = icon(dark ? 'sun' : 'moon');
}
if (localStorage.getItem('ar-theme') === 'dark') document.documentElement.classList.add('dark');
document.querySelector('#theme-button').addEventListener('click', theme);
window.addEventListener('hashchange', () => {
  render();
  window.scrollTo({
    top: 0,
    behavior: 'instant'
  });
  if (mode === 'live' && ['dashboard', 'analytics'].includes(page)) refreshSummary().catch(err => toast(err.message));
});
document.querySelector('#modal').addEventListener('click', ev => {
  if (ev.target === ev.currentTarget) {
    const r = ev.currentTarget.getBoundingClientRect();
    if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) closeDialog(ev.currentTarget);
  }
});
document.querySelector('#modal').addEventListener('cancel', event => {
  event.preventDefault();
  closeDialog(event.currentTarget);
});
initInteractions({changeLanguage, reportError: toast});
tg?.ready();
tg?.expand();
tg?.setHeaderColor?.('#f6f8f7');
tg?.setBackgroundColor?.('#f6f8f7');
translateChrome();
document.title = `AutoReplyer — ${tr('Boshqaruv paneli')}`;
if (tg?.initData) {
  mode = 'loading';
  document.querySelector('#main').innerHTML = `<div class="empty">${tr("Telegram hisobingiz tekshirilmoqda…")}</div>`;
  loadLive().then(() => {
    if (mode === 'live') refreshSummary(1).catch(err => toast(err.message));
  }).catch(() => {
    mode = 'error';
    state = structuredClone(seed);
    render();
  });
} else render();
paintIcons();
