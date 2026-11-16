/**
 * HokieMacros price submissions — Google Apps Script backend.
 *
 * Students send item prices from the app. Obvious junk is denied automatically
 * and filed on the "Auto-denied" tab. Everything else waits on the "Review" tab
 * until you set its Decision to Approve or Reject. You get at most one email a
 * day, and only when something new is waiting.
 *
 * Setup: see backend/README.md.
 */

// ---------------- rules (edit freely) ----------------
const RULES = {
  maxPrice: 30,            // nothing at a VT dining venue costs more than this
  minPrice: 0.5,           // ...or less than this
  minEntree: 2,            // items with 400+ calories cost at least this
  minMedium: 1,            // items with 200-399 calories cost at least this
  vsApproved: [0.6, 1.6],  // a new price must be within 60%–160% of the approved one
  sameAsApproved: 0.05,    // within 5 cents of the approved price: counted as a confirmation, no review
  vsPending: [0.5, 2],     // ...and within 50%–200% of the median of other pending reports (when 2+)
  perDevicePerDay: 20,     // more than this from one phone in 24 hours is denied
  maxPending: 150,         // stop queueing when this many are waiting for you
};
const HALLS = { '01': "Ducky's", '06': 'Perry Place', '07': 'Xpress Lane', '09': 'Hokie Grill', '14': 'Turner Place',
  '16': 'West End', '18': 'Squires', '19': 'Viva Market', '71': 'DX', '72': "Deet's Place", '15': 'D2', '39': 'Owens Food Court' };
// D2 and Owens are all you care to eat: only their door prices are taken, never single items.
const AYCE = { '15': true, '39': true };
const DOOR = { min: 5, max: 40 };

// Decide what to do with one submission. Pure function, so it can be tested outside Google.
// ctx: { approved: number|null, pending: number[] (other people's pending prices for this item),
//        deviceToday: number, pendingTotal: number }
function judge(sub, ctx) {
  const p = Number(sub.price);
  if (!HALLS[sub.hall]) return { status: 'denied', reason: 'Unknown location' };
  if (!/^[A-Za-z0-9-]{1,16}$/.test(String(sub.id || ''))) return { status: 'denied', reason: 'Bad item id' };
  if (!/^[\w .,'&()\/+%-]{1,80}$/.test(String(sub.name || '')) || /https?:|www\.|\.com/i.test(sub.name))
    return { status: 'denied', reason: 'Bad item name' };
  if (!/^[0-9a-f-]{8,40}$/i.test(String(sub.device || ''))) return { status: 'denied', reason: 'No device id' };
  if (!isFinite(p) || Math.round(p * 100) !== Math.round(p * 1000) / 10) return { status: 'denied', reason: 'Not a price' };
  const door = /^door-(breakfast|lunch|dinner|brunch)$/.test(sub.id);
  if (AYCE[sub.hall] && !door) return { status: 'denied', reason: 'Item price at an all-you-care-to-eat hall' };
  if (!AYCE[sub.hall] && door) return { status: 'denied', reason: 'Door price for a hall without one' };
  if (door) {
    if (p < DOOR.min || p > DOOR.max) return { status: 'denied', reason: `Door price outside $${DOOR.min}–$${DOOR.max}` };
  } else {
    if (p > RULES.maxPrice) return { status: 'denied', reason: `Over $${RULES.maxPrice}` };
    const cal = Number(sub.cal) || 0;
    const floor = cal >= 400 ? RULES.minEntree : cal >= 200 ? RULES.minMedium : RULES.minPrice;
    if (p < floor) return { status: 'denied', reason: `Under $${floor.toFixed(2)} for a ${cal || '?'} cal item` };
  }
  if (ctx.deviceToday >= RULES.perDevicePerDay) return { status: 'denied', reason: 'Too many from one phone today' };
  if (ctx.approved) {
    if (Math.abs(p - ctx.approved) <= RULES.sameAsApproved) return { status: 'confirmed', reason: 'Matches approved price' };
    if (p < ctx.approved * RULES.vsApproved[0] || p > ctx.approved * RULES.vsApproved[1])
      return { status: 'denied', reason: `Far from approved $${ctx.approved.toFixed(2)}` };
  }
  if (ctx.pending.length >= 2) {
    const m = median(ctx.pending);
    if (p < m * RULES.vsPending[0] || p > m * RULES.vsPending[1]) return { status: 'denied', reason: `Far from other reports ($${m.toFixed(2)})` };
  }
  if (ctx.pendingTotal >= RULES.maxPending) return { status: 'denied', reason: 'Review queue full' };
  return { status: 'pending' };
}
function median(a) { const s = a.slice().sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; }

// ---------------- sheet plumbing ----------------
const REVIEW = 'Review', DENIED = 'Auto-denied', CONFIRMED = 'Confirmations';
// Review columns
const C = { time: 1, decision: 2, item: 3, where: 4, price: 5, current: 6, others: 7, key: 8, device: 9, cal: 10 };

function sheet_(name) { return SpreadsheetApp.getActive().getSheetByName(name); }
const key_ = s => `${s.hall}|${s.id}`;

function approvedPrices_() {
  const rows = sheet_(REVIEW).getDataRange().getValues().slice(1), out = {};
  for (const r of rows) {
    if (r[C.decision - 1] !== 'Approve') continue;
    const k = r[C.key - 1], t = new Date(r[C.time - 1]).getTime();
    if (!out[k] || t > out[k].t) out[k] = { p: Number(r[C.price - 1]), t, name: r[C.item - 1] };
  }
  return out;
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) return json_({ ok: false, error: 'busy' });
  try {
    let sub; try { sub = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'bad json' }); }
    sub.price = Math.round(Number(sub.price) * 100) / 100;
    const now = new Date(), key = key_(sub), review = sheet_(REVIEW);
    const rows = review.getDataRange().getValues().slice(1);
    const approved = approvedPrices_()[key];
    const pendingRows = rows.map((r, i) => ({ r, i })).filter(x => x.r[C.decision - 1] === 'Pending');
    const pending = pendingRows.filter(x => x.r[C.key - 1] === key && x.r[C.device - 1] !== sub.device).map(x => Number(x.r[C.price - 1]));
    const dayAgo = now.getTime() - 864e5;
    const deviceToday = [[review, C.device - 1], [sheet_(DENIED), 5], [sheet_(CONFIRMED), 5]].reduce((n, [sh, col]) =>
      n + sh.getDataRange().getValues().slice(1).filter(r => r[col] === sub.device && new Date(r[0]).getTime() > dayAgo).length, 0);
    const v = judge(sub, { approved: approved ? approved.p : null, pending, deviceToday, pendingTotal: pendingRows.length });
    const where = HALLS[sub.hall] || sub.hall;

    if (v.status === 'denied') {
      sheet_(DENIED).appendRow([now, v.reason, String(sub.name).slice(0, 80), where, sub.price, String(sub.device).slice(0, 40)]);
      return json_({ ok: true, status: 'denied' });
    }
    if (v.status === 'confirmed') {
      sheet_(CONFIRMED).appendRow([now, String(sub.name).slice(0, 80), where, sub.price, key, sub.device]);
      return json_({ ok: true, status: 'confirmed' });
    }
    // one pending report per phone per item: update it instead of adding another row
    const mine = pendingRows.find(x => x.r[C.key - 1] === key && x.r[C.device - 1] === sub.device);
    const others = pending.length ? `${pending.length} · median $${median(pending).toFixed(2)}` : '';
    const row = [now, 'Pending', String(sub.name).slice(0, 80), where, sub.price, approved ? approved.p : '', others, key, sub.device, Number(sub.cal) || ''];
    if (mine) review.getRange(mine.i + 2, 1, 1, row.length).setValues([row]);
    else review.appendRow(row);
    return json_({ ok: true, status: 'pending' });
  } finally { lock.releaseLock(); }
}

// ---------------- live gym occupancy (VT Rec Sports' public occupancy page) ----------------
const OCC_URL = 'https://connect.recsports.vt.edu/facilityoccupancy';
function fetchOccupancy_() {
  const html = UrlFetchApp.fetch(OCC_URL, { muteHttpExceptions: true, headers: { 'User-Agent': 'HokieMacros (free student app)' } }).getContentText();
  const out = [], re = /<h2><strong>([^<]+)<\/strong><\/h2>[\s\S]*?data-occupancy="(\d+)"\s+data-remaining="(\d+)"/g;
  let m; while ((m = re.exec(html))) out.push({ name: m[1].trim(), count: +m[2], max: +m[2] + +m[3] });
  return { ok: out.length > 0, at: new Date().toISOString(), facilities: out };
}
function occupancy_() {
  const cache = CacheService.getScriptCache(), hit = cache.get('occ');
  if (hit) return JSON.parse(hit);
  const o = fetchOccupancy_(); if (o.ok) cache.put('occ', JSON.stringify(o), 90);
  return o;
}
// Every 15 minutes: keep a log so the app can learn each gym's usual busy times.
function sampleOccupancy() {
  const o = fetchOccupancy_(); if (!o.ok) return;
  const sh = sheet_(OCC_LOG) || SpreadsheetApp.getActive().insertSheet(OCC_LOG);
  if (sh.getLastRow() === 0) sh.appendRow(['Time', 'Facility', 'Count', 'Max']);
  const now = new Date(); o.facilities.forEach(f => sh.appendRow([now, f.name, f.count, f.max]));
  CacheService.getScriptCache().put('occ', JSON.stringify(o), 90);
}
const OCC_LOG = 'Occupancy log';

// Approved prices (read by the app's daily data job), or live gym occupancy with ?occ=1.
function doGet(e) {
  if (e && e.parameter && e.parameter.occ) return json_(occupancy_());
  const a = approvedPrices_(), out = {};
  for (const k in a) out[k] = { p: a[k].p, d: Utilities.formatDate(new Date(a[k].t), 'America/New_York', 'yyyy-MM-dd') };
  return json_({ ok: true, updated: new Date().toISOString(), prices: out });
}

function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

// ---------------- daily digest: at most one email a day ----------------
function dailyDigest() {
  const props = PropertiesService.getScriptProperties();
  const since = Number(props.getProperty('lastDigest') || 0);
  const rows = sheet_(REVIEW).getDataRange().getValues().slice(1).filter(r => r[C.decision - 1] === 'Pending');
  const fresh = rows.filter(r => new Date(r[0]).getTime() > since);
  props.setProperty('lastDigest', String(Date.now()));
  if (!fresh.length) return;
  const denied = sheet_(DENIED).getDataRange().getValues().slice(1).filter(r => new Date(r[0]).getTime() > since).length;
  const list = fresh.slice(0, 15).map(r => `• ${r[C.item - 1]} at ${r[C.where - 1]}: $${Number(r[C.price - 1]).toFixed(2)}${r[C.current - 1] ? ` (now $${Number(r[C.current - 1]).toFixed(2)})` : ''}`).join('\n');
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(), `HokieMacros: ${fresh.length} new price${fresh.length > 1 ? 's' : ''} to review`,
    `${list}${fresh.length > 15 ? `\n…and ${fresh.length - 15} more` : ''}\n\n${rows.length} waiting in total. ${denied} junk submission${denied === 1 ? ' was' : 's were'} denied automatically.\n\nReview: ${SpreadsheetApp.getActive().getUrl()}`);
}

// ---------------- one-time setup: run this once from the editor ----------------
function setup() {
  const ss = SpreadsheetApp.getActive();
  const make = (name, head, widths) => {
    const sh = ss.getSheetByName(name) || ss.insertSheet(name);
    sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#2a1a20').setFontColor('#ffffff');
    sh.setFrozenRows(1); widths.forEach((w, i) => sh.setColumnWidth(i + 1, w)); return sh;
  };
  const r = make(REVIEW, ['Received', 'Decision', 'Item', 'Where', 'Price', 'Current price', 'Other reports', 'key', 'device', 'cal'], [130, 100, 220, 110, 70, 100, 140, 80, 80, 50]);
  r.getRange('B2:B').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['Pending', 'Approve', 'Reject'], true).build());
  r.getRange('E2:F').setNumberFormat('$0.00');
  const rule = (t, c) => SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(t).setBackground(c).setRanges([r.getRange('B2:B')]).build();
  r.setConditionalFormatRules([rule('Approve', '#d6f5e3'), rule('Reject', '#f8d7df'), rule('Pending', '#fff1db')]);
  r.hideColumns(8, 3);
  make(DENIED, ['Received', 'Reason', 'Item', 'Where', 'Price', 'device'], [130, 220, 220, 110, 70, 80]);
  make(CONFIRMED, ['Received', 'Item', 'Where', 'Price', 'key', 'device'], [130, 220, 110, 70, 80, 80]);
  const s1 = ss.getSheetByName('Sheet1'); if (s1 && ss.getSheets().length > 1 && s1.getLastRow() === 0) ss.deleteSheet(s1);
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dailyDigest').timeBased().everyDays(1).atHour(20).inTimezone('America/New_York').create();
  ScriptApp.newTrigger('sampleOccupancy').timeBased().everyMinutes(15).create();
  if (!ss.getSheetByName(OCC_LOG)) ss.insertSheet(OCC_LOG).appendRow(['Time', 'Facility', 'Count', 'Max']);
}

if (typeof module !== 'undefined') module.exports = { judge, median, RULES };
