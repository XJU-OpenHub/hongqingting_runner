/* ============================================================
 * 红蜻蜓接口实验台 · 浏览器端实现
 * 仅用于教学。所有目标地址由用户在 UI 中填写。
 * ============================================================ */

'use strict';

/* ----------------------------- 常量 ----------------------------- */

const STORAGE_KEY = 'hqt-runner-config-v1';

const DEFAULT_CONFIG = {
  authUrl: '',
  summaryUrl: '',
  uploadUrl: '',
  schoolNo: '',
  passwordPrefix: 'Stu',
  queryUid: '',
  uidList: '',
};

// 距离预设。复刻 hongqingting.py 里 PostRunData_* 各自的随机参数。
// distMin/distMax 是相对 distBase 的偏移；durJitter 是叠加在 durBase 上的随机秒数。
const PRESETS = {
  '1.6km': {
    distBase: 1600,
    distMin: -100,
    distMax: 100,
    durBase: 320,
    durJitterMin: 1,
    durJitterMax: 100,
    beginJitterMax: 360,
    trackFile: 'location_1_6km',
  },
  '1.16km': {
    distBase: 1160,
    distMin: -50,
    distMax: 50,
    durBase: 320,
    durJitterMin: 1,
    durJitterMax: 900,
    beginJitterMax: 0, // 原 Python 该分支无 begintime 抖动
    trackFile: 'location_1_6km', // 原 Python 同样复用 1_6km 轨迹
  },
  '12km': {
    distBase: 12000,
    distMin: 1,
    distMax: 500,
    durBase: 5800,
    durJitterMin: 1,
    durJitterMax: 600,
    beginJitterMax: 3600,
    trackFile: 'location_12km',
  },
  '1km': {
    distBase: 1000,
    distMin: -50,
    distMax: 50,
    durBase: 320,
    durJitterMin: 1,
    durJitterMax: 100,
    beginJitterMax: 360,
    trackFile: 'location_1km',
  },
};

/* ----------------------------- 工具函数 ----------------------------- */

const $ = (id) => document.getElementById(id);

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randFloat(min, max) {
  return Math.random() * (max - min) + min;
}

function nowSec() {
  return Math.floor(Date.now() / 1000);
}

function fmtTime(sec) {
  const d = new Date(sec * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/* ----------------------------- 日志 ----------------------------- */

const logEl = () => $('log');

function log(level, ...parts) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const line = `[${ts}] [${level}] ${parts.map((p) => (typeof p === 'string' ? p : JSON.stringify(p))).join(' ')}\n`;
  const el = logEl();
  el.textContent += line;
  el.scrollTop = el.scrollHeight;
}

const info = (...a) => log('INFO', ...a);
const warn = (...a) => log('WARN', ...a);
const errr = (...a) => log('ERR ', ...a);

/* ----------------------------- 配置 ----------------------------- */

// 配置只在内存里，UI 不展示。导入/清除时同步到 localStorage 持久化。
let currentConfig = { ...DEFAULT_CONFIG };

function readConfig() {
  return { ...currentConfig };
}

function applyConfig(c) {
  const src = c || {};
  currentConfig = {
    authUrl: (src.authUrl || '').trim(),
    summaryUrl: (src.summaryUrl || '').trim(),
    uploadUrl: (src.uploadUrl || '').trim(),
    schoolNo: (src.schoolNo || '').trim(),
    passwordPrefix: src.passwordPrefix || 'Stu',
    queryUid: (src.queryUid || '').trim(),
    uidList: src.uidList || '',
  };
}

function flashButton(btn, text, ms = 1500) {
  if (!btn) return;
  if (btn._flashTimer) {
    clearTimeout(btn._flashTimer);
    btn.textContent = btn._flashOrig;
  }
  btn._flashOrig = btn.textContent;
  btn.textContent = text;
  btn.classList.add('flash-ok');
  btn._flashTimer = setTimeout(() => {
    btn.textContent = btn._flashOrig;
    btn.classList.remove('flash-ok');
    btn._flashTimer = null;
  }, ms);
}

function isConfigLoaded() {
  const c = readConfig();
  // 至少 3 个核心 URL 全有才算"已加载"
  return Boolean(c.authUrl && c.summaryUrl && c.uploadUrl);
}

function refreshConfigStatus() {
  const badge = $('config-status');
  if (!badge) return;
  if (isConfigLoaded()) {
    badge.textContent = '✓ 已加载';
    badge.classList.remove('status-empty');
    badge.classList.add('status-loaded');
  } else {
    badge.textContent = '🔒 待导入密钥';
    badge.classList.remove('status-loaded');
    badge.classList.add('status-empty');
  }
}

function persistConfigToLocalStorage() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(readConfig()));
}

function loadConfig({ silent = false } = {}) {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    applyConfig(DEFAULT_CONFIG);
    if (!silent) info('未找到浏览器配置，请导入 JSON 密钥');
    refreshConfigStatus();
    return false;
  }
  try {
    applyConfig({ ...DEFAULT_CONFIG, ...JSON.parse(raw) });
    if (!silent) info('已从浏览器 localStorage 自动恢复配置');
    refreshConfigStatus();
    return true;
  } catch (e) {
    errr('localStorage 配置解析失败：', e.message);
    applyConfig(DEFAULT_CONFIG);
    refreshConfigStatus();
    return false;
  }
}

function clearConfig() {
  if (!confirm('确认清除浏览器中保存的配置？清除后需要重新导入 JSON 密钥才能继续使用。')) return;
  localStorage.removeItem(STORAGE_KEY);
  applyConfig(DEFAULT_CONFIG);
  info('已清除浏览器配置');
  flashButton($('btn-clear-config'), '✓ 已清除');
  refreshConfigStatus();
}

function triggerImport() {
  $('cfg-file-input').click();
}

async function handleImportFile(ev) {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const obj = JSON.parse(text);
    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
      throw new Error('JSON 顶层必须是一个对象');
    }
    applyConfig({ ...DEFAULT_CONFIG, ...obj });
    // 同时写入 localStorage，方便下次自动加载
    persistConfigToLocalStorage();
    info(`已从 ${file.name} 导入配置（已同步写入浏览器 localStorage）`);
    flashButton($('btn-import-config'), '✓ 已导入');
    refreshConfigStatus();
  } catch (e) {
    errr(`导入失败：${e.message}`);
    alert(`导入失败：${e.message}`);
  } finally {
    // 清空 input.value 以便下次能重选同一个文件
    ev.target.value = '';
  }
}

function getUidList() {
  return readConfig()
    .uidList.split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function pickUid(idx) {
  const list = getUidList();
  if (list.length === 0) throw new Error('UID 列表为空，请先在配置区填写至少一行 UID');
  if (idx < 0 || idx >= list.length) throw new Error(`UID 索引 ${idx} 越界（共 ${list.length} 行）`);
  return list[idx];
}

/* ----------------------------- gzip ----------------------------- */

async function gzipString(str) {
  if (typeof CompressionStream === 'undefined') {
    throw new Error('浏览器不支持 CompressionStream，请用现代 Chromium / Firefox / Safari');
  }
  const bytes = new TextEncoder().encode(str);
  const cs = new CompressionStream('gzip');
  const writer = cs.writable.getWriter();
  writer.write(bytes);
  writer.close();
  const reader = cs.readable.getReader();
  const chunks = [];
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const merged = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    merged.set(c, off);
    off += c.length;
  }
  return merged;
}

/* ----------------------------- 轨迹改写 ----------------------------- */

let trackCache = {};

async function loadTrack(name) {
  if (trackCache[name]) return trackCache[name];
  const resp = await fetch(`assets/${name}`, { cache: 'force-cache' });
  if (!resp.ok) throw new Error(`无法读取轨迹文件 assets/${name}：HTTP ${resp.status}`);
  const text = await resp.text();
  trackCache[name] = text;
  return text;
}

// 与 hongqingting.py 中正则逻辑等价：
// 1) 按 '@' 切分每个轨迹点
// 2) 取每个点 ';' 之前的第一段（lat,lng）作为坐标
// 3) 把 'lat,lng;OLDTS;null;null;' 改写为 'lat,lng;NEWTS;null;null;'
// 4) 时间戳沿等分时间步推进
// 5) 拼接后去掉末尾的 '@'
function rewriteTrajectory(text, beginTime, useTime) {
  const points = text.match(/.*?@/gs) || [];
  if (points.length === 0) return '';
  const delta = useTime / points.length;
  let runtime = beginTime;
  let out = '';
  for (const item of points) {
    const m = item.match(/^(.*?);.*?;null;null;/);
    if (!m) {
      out += item;
      continue;
    }
    const loc = m[1];
    out += item.replace(/^.*?;.*?;null;null;/, `${loc};${Math.floor(runtime)};null;null;`);
    runtime += delta;
  }
  // 去掉最后那个 '@'
  return out.endsWith('@') ? out.slice(0, -1) : out;
}

/* ----------------------------- 请求构造 ----------------------------- */

// 登录：name=['bangding','<schoolNo>','student','<no>','<md5(prefix+no)>']  整个数组按字面字符 URL 编码
function buildAuthBody(no, schoolNo, passwordPrefix) {
  if (typeof window.md5 !== 'function') throw new Error('md5 库未加载，请检查 CDN 引用');
  const md5pwd = window.md5(passwordPrefix + no);
  // %5B = [   %27 = '   %2C = ,   %5D = ]
  const body = `name=%5B%27bangding%27%2C%27${schoolNo}%27%2C%27student%27%2C%27${no}%27%2C%27${md5pwd}%27%5D`;
  return { body, md5pwd };
}

// 查询里程 body（Python-dict 风格字符串，studentno 不带引号，其它字段带引号）
function buildSummaryBody(no, queryUid, schoolNo) {
  return `{'studentno':${no},'uid':'${queryUid}','schoolno':'${schoolNo}'}`;
}

// 上传 body（同 Python 拼接顺序）
function buildUploadBody(p) {
  return (
    `{'begintime':'${p.beginTime}','endtime':'${p.endTime}','uid':'${p.uid}',` +
    `'schoolno':'${p.schoolNo}','distance':'${p.distance.toFixed(1)}','speed':'${p.speed}',` +
    `'studentno':'${p.no}','atttype':'3','eventno':'803','location':'${p.location}',` +
    `'pointstatus':'1','usetime':'${p.useTime}','path':'null'}`
  );
}

/* ----------------------------- 跑步数据生成 ----------------------------- */

function generateTimes(day, preset) {
  let beginTime, endTime;
  if (day !== 0) {
    const beginJitter = preset.beginJitterMax > 0 ? randInt(1, preset.beginJitterMax) : 0;
    beginTime = Math.floor(nowSec() - 86400 * day + beginJitter);
    endTime = beginTime + preset.durBase + randInt(preset.durJitterMin, preset.durJitterMax);
  } else {
    endTime = nowSec() - randInt(1, 3600);
    beginTime = endTime - preset.durBase - randInt(preset.durJitterMin, preset.durJitterMax);
  }
  return { beginTime, endTime };
}

async function generateRunData({ no, day, uidIdx, presetName }) {
  const cfg = readConfig();
  if (!cfg.schoolNo) throw new Error('未填写 schoolno');
  const preset = PRESETS[presetName];
  if (!preset) throw new Error(`未知预设：${presetName}`);
  const uid = pickUid(uidIdx);

  const { beginTime, endTime } = generateTimes(day, preset);
  const distance = preset.distBase + randFloat(preset.distMin, preset.distMax);
  const useTime = endTime - beginTime - randInt(1, 10);
  const speed = useTime / 60 / (distance / 1000); // 分钟 / 千米

  const trackText = await loadTrack(preset.trackFile);
  const location = rewriteTrajectory(trackText, beginTime, useTime);

  const body = buildUploadBody({
    beginTime,
    endTime,
    uid,
    schoolNo: cfg.schoolNo,
    distance,
    speed,
    no,
    location,
    useTime,
  });

  return {
    body,
    meta: {
      preset: presetName,
      trackFile: preset.trackFile,
      beginTime,
      endTime,
      beginTimeText: fmtTime(beginTime),
      endTimeText: fmtTime(endTime),
      useTime,
      distance: Number(distance.toFixed(1)),
      speedMinPerKm: Number(speed.toFixed(4)),
      locationLength: location.length,
      pointCount: (trackText.match(/.*?@/gs) || []).length,
      uidIdx,
      uid,
    },
  };
}

/* ----------------------------- 网络发送 ----------------------------- */

async function postForm(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
}

async function postBytes(url, bytes) {
  // 与原 Python 一致：body 是 gzip 字节，但不显式声明 Content-Encoding，由服务器自检
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: bytes,
  });
}

async function readResponse(resp) {
  const text = await resp.text();
  return { status: resp.status, ok: resp.ok, text };
}

/* ----------------------------- UI 处理：登录 ----------------------------- */

function handleBuildAuth() {
  try {
    const cfg = readConfig();
    if (!cfg.authUrl) throw new Error('未填写登录接口 URL');
    if (!cfg.schoolNo) throw new Error('未填写 schoolno');
    const no = $('stu-no').value.trim();
    if (!no) throw new Error('未填写学号');

    const { body, md5pwd } = buildAuthBody(no, cfg.schoolNo, cfg.passwordPrefix);
    $('preview-auth').textContent =
      `URL:    POST ${cfg.authUrl}\n` +
      `Header: Content-Type: application/x-www-form-urlencoded\n` +
      `Salt:   ${cfg.passwordPrefix}${no}\n` +
      `MD5:    ${md5pwd}\n` +
      `Body:   ${body}\n`;
    info('已构造登录请求');
    return body;
  } catch (e) {
    errr('构造登录请求失败：', e.message);
    return null;
  }
}

async function handleSendAuth() {
  const body = handleBuildAuth();
  if (!body) return;
  const cfg = readConfig();
  info('发送登录请求 →', cfg.authUrl);
  try {
    const resp = await postForm(cfg.authUrl, body);
    const r = await readResponse(resp);
    info(`← HTTP ${r.status}`);
    $('preview-auth').textContent += `\nResponse: HTTP ${r.status}\n${r.text}\n`;
  } catch (e) {
    errr('登录请求失败：', e.message);
    $('preview-auth').textContent += `\nResponse: 失败：${e.message}\n（多半是 CORS、HTTPS 混合内容、或目标服务器不可达）\n`;
  }
}

/* ----------------------------- UI 处理：查询里程 ----------------------------- */

function buildQueryPreview() {
  const cfg = readConfig();
  if (!cfg.summaryUrl) throw new Error('未填写查询接口 URL');
  if (!cfg.schoolNo) throw new Error('未填写 schoolno');
  const no = $('stu-no').value.trim();
  if (!no) throw new Error('未填写学号（在 ② 区填写）');
  const queryUid = cfg.queryUid || (() => {
    const idx = parseInt($('up-uid-idx').value, 10) || 0;
    return pickUid(idx);
  })();
  const body = buildSummaryBody(no, queryUid, cfg.schoolNo);
  return { url: cfg.summaryUrl, body, queryUid };
}

async function handleBuildQuery() {
  try {
    const { url, body, queryUid } = buildQueryPreview();
    $('preview-query').textContent =
      `URL:        POST ${url}\n` +
      `Body(明文): ${body}\n` +
      `Body 长度:  ${body.length} 字节\n` +
      `UID:        ${queryUid}\n` +
      `（实际发送时会先 gzip 压缩）\n`;
    info('已构造查询请求');
  } catch (e) {
    errr('构造查询请求失败：', e.message);
  }
}

async function handleSendQuery() {
  let url, body;
  try {
    ({ url, body } = buildQueryPreview());
  } catch (e) {
    errr('构造查询请求失败：', e.message);
    return;
  }
  info('发送查询请求 →', url);
  try {
    const gz = await gzipString(body);
    const resp = await postBytes(url, gz);
    const r = await readResponse(resp);
    info(`← HTTP ${r.status} (gzip ${gz.length} 字节)`);
    let parsed = '';
    try {
      const j = JSON.parse(r.text);
      if (j && typeof j.lasttime === 'number') {
        parsed = `\n解析: 跑步里程 m=${j.m}, 最后上报时间=${fmtTime(j.lasttime)}`;
      }
    } catch {
      /* not JSON */
    }
    $('preview-query').textContent += `\nResponse: HTTP ${r.status}\n${r.text}${parsed}\n`;
  } catch (e) {
    errr('查询请求失败：', e.message);
    $('preview-query').textContent += `\nResponse: 失败：${e.message}\n`;
  }
}

/* ----------------------------- UI 处理：上传跑步数据 ----------------------------- */

let uploadAbortFlag = false;

async function handleBuildUpload() {
  try {
    const cfg = readConfig();
    if (!cfg.uploadUrl) throw new Error('未填写上传接口 URL');
    const no = $('stu-no').value.trim();
    if (!no) throw new Error('未填写学号（在 ② 区填写）');
    const day = parseFloat($('up-day').value);
    const uidIdx = parseInt($('up-uid-idx').value, 10) || 0;
    const presetName = $('up-preset').value;

    const { body, meta } = await generateRunData({ no, day, uidIdx, presetName });
    const gz = await gzipString(body);

    $('preview-upload').textContent =
      `URL:           POST ${cfg.uploadUrl}\n` +
      `预设:          ${meta.preset}（轨迹文件 assets/${meta.trackFile}，${meta.pointCount} 个点）\n` +
      `开始时间:      ${meta.beginTimeText} (${meta.beginTime})\n` +
      `结束时间:      ${meta.endTimeText} (${meta.endTime})\n` +
      `usetime:       ${meta.useTime} 秒\n` +
      `distance:      ${meta.distance} 米\n` +
      `speed:         ${meta.speedMinPerKm} 分钟/千米\n` +
      `UID[${meta.uidIdx}]:        ${meta.uid}\n` +
      `body 明文长度: ${body.length} 字节\n` +
      `gzip 后:       ${gz.length} 字节\n\n` +
      `--- body 明文 (前 800 字符) ---\n${body.slice(0, 800)}${body.length > 800 ? '\n...(已截断)' : ''}\n`;
    info(`已构造上传请求，明文 ${body.length} B → gzip ${gz.length} B`);
  } catch (e) {
    errr('构造上传请求失败：', e.message);
  }
}

async function handleSendUpload() {
  const cfg = readConfig();
  if (!cfg.uploadUrl) {
    errr('未填写上传接口 URL');
    return;
  }
  const no = $('stu-no').value.trim();
  if (!no) {
    errr('未填写学号（在 ② 区填写）');
    return;
  }
  const dayStart = parseFloat($('up-day').value);
  const step = parseFloat($('up-step').value) || 1;
  const count = Math.max(1, parseInt($('up-count').value, 10) || 1);
  const uidIdx = parseInt($('up-uid-idx').value, 10) || 0;
  const presetName = $('up-preset').value;

  uploadAbortFlag = false;
  $('btn-stop-upload').disabled = false;
  $('btn-send-upload').disabled = true;
  $('btn-build-upload').disabled = true;

  let outText = '';
  for (let i = 0; i < count; i++) {
    if (uploadAbortFlag) {
      info(`用户中止：第 ${i}/${count} 轮停止`);
      break;
    }
    const day = dayStart + i * step;
    info(`[${i + 1}/${count}] 生成 day=${day}`);
    try {
      const { body, meta } = await generateRunData({ no, day, uidIdx, presetName });
      const gz = await gzipString(body);
      info(`[${i + 1}/${count}] 发送：${meta.beginTimeText} → ${meta.endTimeText}, ${meta.distance}m`);
      const resp = await postBytes(cfg.uploadUrl, gz);
      const r = await readResponse(resp);
      info(`[${i + 1}/${count}] ← HTTP ${r.status}: ${r.text.slice(0, 200)}`);
      outText += `[${i + 1}/${count}] day=${day} ${meta.beginTimeText} → ${meta.endTimeText} dist=${meta.distance}m HTTP ${r.status}\n${r.text}\n\n`;
    } catch (e) {
      errr(`[${i + 1}/${count}] 失败：${e.message}`);
      outText += `[${i + 1}/${count}] day=${day} 失败：${e.message}\n\n`;
    }
  }

  $('preview-upload').textContent = outText || $('preview-upload').textContent;
  $('btn-stop-upload').disabled = true;
  $('btn-send-upload').disabled = false;
  $('btn-build-upload').disabled = false;
}

function handleStopUpload() {
  uploadAbortFlag = true;
  warn('已请求停止后续轮次');
}

/* ----------------------------- 启动 ----------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  loadConfig({ silent: true });

  $('btn-import-config').addEventListener('click', triggerImport);
  $('cfg-file-input').addEventListener('change', handleImportFile);
  $('btn-clear-config').addEventListener('click', clearConfig);

  $('btn-build-auth').addEventListener('click', handleBuildAuth);
  $('btn-send-auth').addEventListener('click', handleSendAuth);

  $('btn-build-query').addEventListener('click', handleBuildQuery);
  $('btn-send-query').addEventListener('click', handleSendQuery);

  $('btn-build-upload').addEventListener('click', handleBuildUpload);
  $('btn-send-upload').addEventListener('click', handleSendUpload);
  $('btn-stop-upload').addEventListener('click', handleStopUpload);

  $('btn-clear-log').addEventListener('click', () => {
    logEl().textContent = '';
  });

  info('页面就绪。请先在 ① 配置区填写自己服务器的接口 URL。');
});
