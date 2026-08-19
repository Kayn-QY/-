"use strict";
/* 排班站 Excel 式 Sheet：左下角浮动电子表格，点击编辑、增删行列；保存复用 editor.html 的 GitHub API + Token 逻辑，
   写回 schedule.json / config.json，并用最新数据重新生成 index.html / output/schedule.html（含本组件）。 */
const SHEET_REPO_OWNER = "Kayn-QY";
const SHEET_REPO_NAME = "-";
const SHEET_API = `https://api.github.com/repos/${SHEET_REPO_OWNER}/${SHEET_REPO_NAME}/contents/`;
const SHEET_WEEKDAYS = ["周一","周二","周三","周四","周五","周六","周日"];
const SHEET_ROLES = [
  ["time", "直播时间"],
  ["car", "直播车型"],
  ["anchor", "主播"],
  ["tech", "技术"],
  ["ad", "投流"],
];
const SHEET_MARQUEE = ["Bilibili", "GitHub", "Vercel", "Figma", "Notion", "Slack"];

/* 与 render_web.py CSS_TEMPLATE / editor.html CSS_VIEW 保持一致（生成脚本注入） */
const SHEET_CSS = `
:root{
  --ink-deep: #0a1b33;
  --ink-2: #1e3a5f;
  --clay: #905831;
  --clay-2: #c07a4a;
  --peach: #ffd9b8;
  --text-main: #1f2c44;
  --text-muted: #4a5a72;
  --font-sans: "Inter", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-display: "Outfit", "PingFang SC", sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{color-scheme:light}
body{
  font-family:var(--font-sans);color:var(--text-main);overflow-x:hidden;
  -webkit-font-smoothing:antialiased;min-height:100vh;
  background:
    radial-gradient(1200px 700px at 15% -10%, rgba(144,88,49,.28), transparent 55%),
    radial-gradient(1000px 600px at 110% 30%, rgba(10,27,51,.35), transparent 55%),
    linear-gradient(160deg, #c9d3e2 0%, #aebbd0 40%, #d8dee8 100%);
  background-attachment:fixed;
}
/* 浮动胶囊导航 */
.pill-nav{
  position:fixed;left:50%;transform:translateX(-50%);top:20px;z-index:100;
  display:flex;gap:4px;padding:7px;border-radius:999px;
  background:linear-gradient(135deg, rgba(255,255,255,.62), rgba(255,255,255,.38));
  backdrop-filter:blur(26px) saturate(1.6);-webkit-backdrop-filter:blur(26px) saturate(1.6);
  border:1px solid rgba(255,255,255,.7);
  box-shadow:0 20px 44px rgba(20,30,50,.22), inset 0 1px 0 rgba(255,255,255,.85), 0 1px 0 rgba(20,30,50,.05);
  font-family:var(--font-sans);
}
.pill-nav a{
  padding:8px 18px;border-radius:999px;color:#334155;font-size:13px;font-weight:500;
  text-decoration:none;transition:all .25s ease;white-space:nowrap;
}
.pill-nav a:hover{background:rgba(255,255,255,.5)}
.pill-nav a.active{
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;font-weight:600;
  box-shadow:0 6px 16px rgba(10,27,51,.35);
}
/* 内容区 */
.content{position:relative;z-index:2;max-width:1320px;margin:0 auto;padding:120px 32px 64px}
/* Hero 毛玻璃 3D */
.hero{
  position:relative;border-radius:36px;overflow:hidden;min-height:320px;display:flex;align-items:center;
  border:1px solid rgba(255,255,255,.6);
  box-shadow:0 44px 90px rgba(20,30,50,.28), inset 0 1px 0 rgba(255,255,255,.8);
  background:linear-gradient(150deg, rgba(255,255,255,.5), rgba(255,255,255,.2));
  backdrop-filter:blur(20px) saturate(1.4);-webkit-backdrop-filter:blur(20px) saturate(1.4);
}
.hero::before{
  content:"";position:absolute;inset:0;
  background:linear-gradient(120deg, rgba(10,27,51,.9), rgba(10,27,51,.55) 50%, rgba(144,88,49,.55));
  mix-blend-mode:multiply;
}
.hero-inner{position:relative;padding:56px 48px;font-family:var(--font-display);color:#fff}
.hero-eyebrow{font-size:13px;color:var(--peach);font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px;text-shadow:0 1px 8px rgba(0,0,0,.2)}
.hero h1{font-size:clamp(30px,4.6vw,46px);font-weight:700;line-height:1.1;max-width:560px;text-shadow:0 2px 20px rgba(0,0,0,.25)}
.hero-sub{margin-top:14px;font-size:15px;font-family:var(--font-sans);color:rgba(255,255,255,.85);max-width:520px;text-shadow:0 1px 10px rgba(0,0,0,.2)}
.hero-actions{margin-top:28px;display:flex;gap:12px;flex-wrap:wrap;font-family:var(--font-sans)}
.btn-primary{
  display:inline-flex;align-items:center;background:linear-gradient(135deg, #fff, rgba(255,255,255,.85));
  color:#0a1b33;border-radius:999px;padding:12px 24px;font-size:13px;font-weight:600;text-decoration:none;
  box-shadow:0 14px 30px rgba(10,27,51,.35), inset 0 1px 0 #fff;transition:transform .15s;
}
.btn-primary:hover{transform:translateY(-2px)}
.btn-glass{
  display:inline-flex;align-items:center;border:1px solid rgba(255,255,255,.5);border-radius:999px;
  padding:12px 24px;font-size:13px;color:#fff;background:rgba(255,255,255,.16);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);text-decoration:none;transition:background .2s;
}
.btn-glass:hover{background:rgba(255,255,255,.28)}
/* 跑马灯 */
.marquee{
  margin-top:24px;overflow:hidden;position:relative;border-radius:18px;padding:14px 0;
  border:1px solid rgba(255,255,255,.5);
  background:linear-gradient(135deg, rgba(255,255,255,.5), rgba(255,255,255,.28));
  backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);
  box-shadow:0 20px 44px rgba(20,30,50,.16);
  -webkit-mask-image:linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
  mask-image:linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
}
.marquee-track{display:flex;gap:12px;white-space:nowrap;animation:slide 22s linear infinite;width:max-content}
.marquee-track span{
  border:1px solid rgba(255,255,255,.65);border-radius:999px;padding:9px 20px;background:rgba(255,255,255,.55);
  box-shadow:0 6px 16px rgba(20,30,50,.08), inset 0 1px 0 #fff;font-family:var(--font-sans);
  font-size:12px;color:#334155;white-space:nowrap;
}
@keyframes slide{from{transform:translateX(0)}to{transform:translateX(-50%)}}
/* 卡片网格：排班表 + 提醒 */
.cards-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:18px;margin-top:24px;align-items:start}
.glass-card{
  border-radius:28px;border:1px solid rgba(255,255,255,.6);
  background:linear-gradient(150deg, rgba(255,255,255,.56), rgba(255,255,255,.3));
  backdrop-filter:blur(22px) saturate(1.5);-webkit-backdrop-filter:blur(22px) saturate(1.5);
  box-shadow:0 30px 60px rgba(20,30,50,.2), inset 0 1px 0 rgba(255,255,255,.8);
  padding:24px;animation:rise .6s cubic-bezier(.16,1,.3,1) both;
}
.card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;flex-wrap:wrap;margin-bottom:16px}
.card-head h2{font-family:var(--font-display);font-size:18px;font-weight:600;color:#0f1e3d}
.card-head .sub{margin-top:6px;font-size:12px;color:var(--text-muted)}
.card-head .sub time{color:#0f1e3d;font-weight:500}
/* 统计 chips */
.stats{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.chip{
  font-size:12px;color:#3d4c66;background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.7);
  border-radius:999px;padding:6px 12px;box-shadow:inset 0 1px 0 #fff;transition:transform .2s;
}
.chip b{color:var(--clay);font-weight:600}
.chip:hover{transform:translateY(-1px)}
/* 表格 */
.table-scroll{overflow-x:auto;border-radius:16px}
/* 冻结列：场次/角色列固定不动，横向滚动仅数据区滑动 */
thead th.col-slot{position:sticky;left:0;z-index:6;background:linear-gradient(150deg, rgba(255,255,255,.97), rgba(255,255,255,.92))}
thead th.col-role{position:sticky;left:90px;z-index:6;background:linear-gradient(150deg, rgba(255,255,255,.97), rgba(255,255,255,.92))}
td.slot-col{position:sticky;left:0;z-index:4;background:linear-gradient(150deg, rgba(255,255,255,.97), rgba(255,255,255,.92))}
td.role-col{position:sticky;left:90px;z-index:4;background:linear-gradient(150deg, rgba(255,255,255,.97), rgba(255,255,255,.92))}
tbody tr:hover td.slot-col,
tbody tr:hover td.role-col{background:linear-gradient(150deg, rgba(255,255,255,.99), rgba(255,255,255,.94))}
table{width:100%;border-collapse:separate;border-spacing:6px;min-width:1120px;font-size:12.5px}
thead th{
  background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.7);border-radius:12px;
  box-shadow:inset 0 1px 0 #fff;color:#1f2c44;font-weight:600;padding:10px 8px;white-space:nowrap;text-align:center;
}
.date-col{min-width:96px;font-weight:600}
.date-col .wd{display:block;font-size:10px;color:var(--text-muted);font-weight:400;margin-top:2px}
.slot-col{width:84px;color:#334155;font-weight:500}
.role-col{width:80px;color:var(--text-muted);font-size:11.5px;font-weight:500}
td{
  border:1px solid rgba(255,255,255,.7);border-radius:12px;padding:9px 6px;text-align:center;
  color:#334155;vertical-align:middle;background:rgba(255,255,255,.55);box-shadow:inset 0 1px 0 #fff;
  transition:background .15s,transform .15s;
}
tbody tr:hover td{background:rgba(255,255,255,.72)}
.slot-badge{
  display:inline-flex;align-items:center;justify-content:center;min-width:46px;padding:4px 8px;border-radius:999px;
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;font-weight:600;font-size:11px;
  box-shadow:0 6px 14px rgba(10,27,51,.3);
}
.cell{min-height:26px}
.cell.anchor{
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;font-weight:600;border-color:transparent;
  box-shadow:0 8px 18px rgba(10,27,51,.3);
}
.cell.car{
  background:linear-gradient(135deg, #905831, #c07a4a);color:#fff;font-weight:600;border-color:transparent;
  box-shadow:0 8px 18px rgba(144,88,49,.3);
}
.cell.time{color:#0f1e3d;font-weight:500}
.cell.empty{background:rgba(255,255,255,.32);color:rgba(31,44,68,.25);border-color:rgba(255,255,255,.4)}
/* 提醒卡片 */
.remind-card{align-self:start}
.remind-item{
  margin-top:10px;background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.65);border-radius:16px;
  padding:12px 14px;font-size:13px;color:#334155;box-shadow:inset 0 1px 0 #fff;display:flex;align-items:center;gap:10px;
}
.remind-time{font-weight:600;color:#0a1b33;white-space:nowrap}
.remind-slot{color:var(--text-muted)}
.remind-name{color:var(--clay);font-weight:600}
.remind-empty{
  margin-top:12px;background:rgba(255,255,255,.4);border:1px dashed rgba(255,255,255,.7);border-radius:16px;
  padding:18px;font-size:13px;color:var(--text-muted);text-align:center;
}
/* 底部说明 */
.note{margin-top:20px;font-size:12px;color:var(--text-muted);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:0 4px}
.note .tag{letter-spacing:.06em;text-transform:uppercase;font-size:10.5px;color:rgba(74,90,114,.75)}
/* Excel 式 Sheet 面板（左下角浮动） */
.sheet-panel{
  position:fixed;left:16px;bottom:16px;z-index:120;width:min(560px,calc(100vw - 32px));
  border-radius:20px;border:1px solid rgba(255,255,255,.65);
  background:linear-gradient(150deg, rgba(255,255,255,.8), rgba(255,255,255,.56));
  backdrop-filter:blur(24px) saturate(1.5);-webkit-backdrop-filter:blur(24px) saturate(1.5);
  box-shadow:0 30px 70px rgba(20,30,50,.32), inset 0 1px 0 rgba(255,255,255,.9);
  overflow:hidden;font-family:var(--font-sans);
}
.sheet-panel.collapsed{width:auto}
.sheet-head{
  display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;
  background:linear-gradient(135deg, rgba(10,27,51,.93), rgba(30,58,95,.93));
}
.sheet-head .sheet-title{color:#fff;font-weight:600;font-size:13px;letter-spacing:.03em;white-space:nowrap}
.sheet-head .sheet-actions{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.sheet-head button{
  border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.14);color:#fff;
  border-radius:999px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:var(--font-sans);
  transition:background .2s;white-space:nowrap;
}
.sheet-head button:hover{background:rgba(255,255,255,.3)}
.sheet-head button.sheet-save{background:linear-gradient(135deg, #c07a4a, #905831);border-color:transparent;font-weight:600}
.sheet-head button.sheet-save:hover{background:linear-gradient(135deg, #d08a58, #a06838)}
.sheet-wrap{max-height:280px;overflow:auto;padding:10px 10px 4px}
.sheet-table{border-collapse:separate;border-spacing:3px;width:100%;min-width:420px;font-size:11.5px}
.sheet-table th,.sheet-table td{border-radius:8px;padding:4px 6px;text-align:center;font-weight:400}
.sheet-table thead th{
  background:rgba(255,255,255,.65);border:1px solid rgba(255,255,255,.8);color:#1f2c44;
  font-size:11px;white-space:nowrap;box-shadow:inset 0 1px 0 #fff;
}
.sheet-table thead th .sheet-del{display:inline-block;margin-left:4px;color:#c0392b;cursor:pointer;font-size:12px;font-weight:700;opacity:.75}
.sheet-table thead th .sheet-del:hover{opacity:1}
.sheet-table .sheet-corner{position:sticky;left:0;top:0;z-index:5;background:linear-gradient(135deg,#0a1b33,#1e3a5f);color:#fff;font-weight:600}
.sheet-table th.sheet-date{position:sticky;top:0;z-index:3}
.sheet-table td.sheet-cell{
  background:rgba(255,255,255,.6);border:1px solid rgba(255,255,255,.75);color:#334155;
  min-width:64px;outline:none;cursor:text;white-space:pre-wrap;word-break:break-word;
}
.sheet-table td.sheet-cell:hover{background:rgba(255,255,255,.8)}
.sheet-table td.sheet-cell:focus{background:rgba(255,255,255,.92);box-shadow:inset 0 0 0 1.5px var(--clay)}
.sheet-table td.sheet-cell.empty{color:rgba(31,44,68,.28);background:rgba(255,255,255,.4)}
.sheet-table td.sheet-label{
  background:rgba(255,255,255,.72);border:1px solid rgba(255,255,255,.85);color:#334155;
  white-space:nowrap;text-align:left;font-size:11px;
}
.sheet-table td.sheet-label .slot-badge{min-width:38px;padding:2px 6px;font-size:10px}
.sheet-table td.sheet-label .sheet-del{color:#c0392b;cursor:pointer;font-weight:700;margin-left:5px;opacity:.7;font-size:11px}
.sheet-table td.sheet-label .sheet-del:hover{opacity:1}
.sheet-status{min-height:20px;padding:2px 14px 8px;font-size:11.5px;color:var(--clay)}
.sheet-status.err{color:#c0392b}
.sheet-token{display:none;padding:8px 12px 10px;border-top:1px dashed rgba(255,255,255,.6)}
.sheet-token input{
  width:100%;padding:7px 12px;border:1px solid rgba(255,255,255,.75);border-radius:999px;font-size:12px;
  background:rgba(255,255,255,.6);color:var(--text-main);outline:none;box-shadow:inset 0 1px 0 #fff;
}
.sheet-token .sheet-token-actions{display:flex;gap:6px;margin-top:8px}
.sheet-token button{
  border:1px solid rgba(255,255,255,.7);background:rgba(255,255,255,.5);color:var(--text-main);
  border-radius:999px;padding:5px 12px;font-size:12px;cursor:pointer;font-family:var(--font-sans);
}
.sheet-token button.btn-primary{background:linear-gradient(135deg,#0a1b33,#1e3a5f);color:#fff;border-color:transparent}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:1024px){
  .cards-grid{grid-template-columns:1fr}
  .content{padding:120px 18px 48px}
}
@media (max-width:640px){
  .pill-nav{top:12px;max-width:calc(100vw - 24px);overflow-x:auto}
  .pill-nav a{padding:7px 12px;font-size:12px}
  .hero-inner{padding:40px 24px}
  .glass-card{padding:18px 14px;border-radius:20px}
}
`;

let sheetSchedule = {};
let sheetDates = [];
let sheetCfg = {};
let sheetSlots = ["第1场","第2场","第3场","第4场","第5场","第6场"];

function $sh(id){ return document.getElementById(id); }
function shEscape(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function shFmt(d){ return d.slice(5).replace("-", "/"); }
function shParse(s){
  let m = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
  if (m) return new Date(+m[1], +m[2]-1, +m[3]);
  m = s.match(/^(\d{1,2})[-/](\d{1,2})$/);
  if (m) return new Date(new Date().getFullYear(), +m[1]-1, +m[2]);
  return null;
}
function shISO(d){ return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
function shStatus(msg, err){
  const el = $sh("sheet-status");
  if (!el) return;
  el.textContent = msg;
  el.className = err ? "err" : "";
}
function shSortSlots(a, b){
  const ma = a.match(/\d+/), mb = b.match(/\d+/);
  if (ma && mb) return (+ma[0]) - (+mb[0]);
  return a < b ? -1 : 1;
}

async function shLoad(){
  try {
    const [sRes, cRes] = await Promise.all([
      fetch("schedule.json", {cache: "no-store"}),
      fetch("config.json", {cache: "no-store"}),
    ]);
    if (!sRes.ok) throw new Error("schedule.json 加载失败: " + sRes.status);
    sheetSchedule = await sRes.json();
    if (cRes.ok) sheetCfg = await cRes.json();
    sheetDates = (sheetCfg.display_dates && sheetCfg.display_dates.length) ? sheetCfg.display_dates.slice() : Object.keys(sheetSchedule).sort();
    Object.keys(sheetSchedule).forEach(d => { if (!sheetDates.includes(d)) sheetDates.push(d); });
    sheetDates.sort();
    const slots = new Set(sheetSlots);
    Object.values(sheetSchedule).forEach(sl => Object.keys(sl).forEach(s => slots.add(s)));
    sheetSlots = Array.from(slots).sort(shSortSlots);
    shRender();
  } catch (e) {
    shStatus("数据加载失败（请确认是通过 https://kayn-qy.github.io/-/ 访问）: " + e.message, true);
  }
}

function shRender(){
  const wrap = $sh("sheet-table");
  if (!wrap) return;
  let head = '<tr><th class="sheet-corner">日期 \\ 场次</th>';
  sheetDates.forEach((d, i) => {
    const dt = shParse(d);
    const wd = dt ? SHEET_WEEKDAYS[dt.getDay()] : "";
    head += `<th class="sheet-date">${shFmt(d)}<span class="wd" style="display:block;font-size:9px;color:#4a5a72;font-weight:400">${wd}</span><span class="sheet-del" data-sheet-del-col="${i}">×</span></th>`;
  });
  head += '</tr>';
  let body = "";
  sheetSlots.forEach(slot => {
    SHEET_ROLES.forEach(([rk, rn]) => {
      let cells = "";
      sheetDates.forEach(d => {
        const info = (sheetSchedule[d] && sheetSchedule[d][slot]) || {};
        const val = info[rk] !== undefined ? info[rk] : "";
        const empty = !String(val).trim();
        cells += `<td class="sheet-cell${empty ? " empty" : ""}" contenteditable="true" data-sd="${shEscape(d)}" data-ss="${shEscape(slot)}" data-sr="${rk}">${shEscape(val)}</td>`;
      });
      const label = rk === "time" ? `<span class="slot-badge">${shEscape(slot)}</span>` : `<span class="sheet-rolename">${rn}</span>`;
      const del = rk === "time" ? `<span class="sheet-del" data-sheet-del-row="${shEscape(slot)}">×</span>` : "";
      body += `<tr><td class="sheet-label">${label}${del}</td>${cells}</tr>`;
    });
  });
  wrap.innerHTML = head + body;
  shBind();
}

function shBind(){
  document.querySelectorAll("#sheet-table td.sheet-cell").forEach(td => {
    td.addEventListener("input", () => {
      const d = td.dataset.sd, s = td.dataset.ss, r = td.dataset.sr;
      if (!sheetSchedule[d]) sheetSchedule[d] = {};
      if (!sheetSchedule[d][s]) sheetSchedule[d][s] = {};
      sheetSchedule[d][s][r] = td.innerText.trim();
      td.classList.toggle("empty", !td.innerText.trim());
    });
  });
  document.querySelectorAll("#sheet-table .sheet-del[data-sheet-del-col]").forEach(el => {
    el.addEventListener("click", () => shDelCol(parseInt(el.dataset.sheetDelCol, 10)));
  });
  document.querySelectorAll("#sheet-table .sheet-del[data-sheet-del-row]").forEach(el => {
    el.addEventListener("click", () => shDelRow(el.dataset.sheetDelRow));
  });
}

function shAddCol(){
  const input = prompt("输入新日期列（格式 2026-08-20，或 08-20）：");
  if (!input) return;
  const dt = shParse(input.trim());
  if (!dt) { shStatus("日期格式不正确", true); return; }
  const iso = shISO(dt);
  if (sheetDates.includes(iso)) { shStatus("该日期已存在", true); return; }
  sheetDates.push(iso);
  sheetDates.sort();
  if (!sheetSchedule[iso]) sheetSchedule[iso] = {};
  shRender();
  shStatus(`已添加日期列 ${iso}（点击「保存」发布）`);
}
function shDelCol(i){
  const d = sheetDates[i];
  if (!confirm(`确定删除日期列 ${d} 及其全部排班数据？`)) return;
  sheetDates.splice(i, 1);
  delete sheetSchedule[d];
  shRender();
  shStatus(`已删除 ${d}（点击「保存」发布）`);
}
function shAddRow(){
  const input = prompt("输入新场次行（如：第7场）：");
  if (!input) return;
  const s = input.trim();
  if (!s) return;
  if (sheetSlots.includes(s)) { shStatus("该场次已存在", true); return; }
  sheetSlots.push(s);
  sheetSlots.sort(shSortSlots);
  shRender();
  shStatus(`已添加场次 ${s}（点击「保存」发布）`);
}
function shDelRow(slot){
  if (!confirm(`确定删除场次 ${slot} 及其全部排班数据？`)) return;
  sheetSlots = sheetSlots.filter(s => s !== slot);
  Object.keys(sheetSchedule).forEach(d => { delete sheetSchedule[d][slot]; });
  shRender();
  shStatus(`已删除场次 ${slot}（点击「保存」发布）`);
}

/* ---------- GitHub API + Token（复用 editor.html 逻辑） ---------- */
function shToken(){ return (localStorage.getItem("gh_token") || "").trim(); }
async function shGetSha(path){
  const r = await fetch(SHEET_API + path, { headers: { Authorization: `Bearer ${shToken()}` } });
  if (!r.ok) { if (r.status === 404) return null; throw new Error(`获取 ${path} 失败: HTTP ${r.status}`); }
  const j = await r.json();
  return j.sha || null;
}
async function shPut(path, content){
  const sha = await shGetSha(path);
  const body = { message: "Sheet 在线编辑排班表", content: btoa(unescape(encodeURIComponent(content))) };
  if (sha) body.sha = sha;
  const r = await fetch(SHEET_API + path, {
    method: "PUT",
    headers: { Authorization: `Bearer ${shToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try { const j = await r.json(); msg = (j.message || "") + (j.errors ? " " + JSON.stringify(j.errors) : ""); } catch(e){}
    throw new Error(`更新 ${path} 失败: ${msg}`);
  }
  return true;
}

/* ---------- 生成完整页面（与 render_web.py render_html 一致） ---------- */
function shLatestReminders(){
  const dates = Object.keys(sheetSchedule).sort();
  if (!dates.length) return [null, []];
  const d = dates[dates.length - 1];
  const items = [];
  sheetSlots.forEach(slot => {
    const info = (sheetSchedule[d] && sheetSchedule[d][slot]) || {};
    const t = (info.time || "").trim();
    const a = (info.anchor || "").trim();
    if (t && a) items.push([t, a, slot]);
  });
  return [d, items];
}
function shChips(){
  const counter = {};
  Object.values(sheetSchedule).forEach(slots => Object.values(slots).forEach(info => {
    const n = (info.anchor || "").trim();
    if (n) counter[n] = (counter[n] || 0) + 1;
  }));
  return Object.entries(counter).map(([n, c]) => `<span class="chip">主播 <b>${shEscape(n)}</b> × ${c} 场</span>`).join("") || '<span class="chip">暂无数据</span>';
}
function shPage(updatedAt){
  const dateHeader = sheetDates.map(d => {
    const dt = shParse(d);
    const wd = dt ? SHEET_WEEKDAYS[dt.getDay()] : "";
    return `<th class="date-col">${shFmt(d)}<span class="wd">${wd}</span></th>`;
  }).join("");
  const rows = [];
  sheetSlots.forEach(slot => {
    SHEET_ROLES.forEach(([rk, rn]) => {
      let cells = "";
      sheetDates.forEach(d => {
        const info = (sheetSchedule[d] && sheetSchedule[d][slot]) || {};
        const val = info[rk] !== undefined ? info[rk] : "";
        if (String(val).trim()) {
          let cls = "cell";
          if (rk === "anchor") cls = "cell anchor";
          else if (rk === "car") cls = "cell car";
          else if (rk === "time") cls = "cell time";
          cells += `<td class="${cls}">${shEscape(val)}</td>`;
        } else {
          cells += '<td class="cell empty">·</td>';
        }
      });
      const rowLabel = rk === "time" ? `<span class="slot-badge">${shEscape(slot)}</span>` : "";
      const trCls = rk === "time" ? ' class="row-slot"' : "";
      rows.push(`<tr${trCls}><td class="slot-col">${rowLabel}</td><td class="role-col">${rn}</td>${cells}</tr>`);
    });
  });
  const marqueeItems = SHEET_MARQUEE.map(it => `<span>${it}</span>`).join("");
  const marquee = `<div class="marquee"><div class="marquee-track">${marqueeItems}${marqueeItems}</div></div>`;
  const [remindDate, remindItems] = shLatestReminders();
  let remindTitle, remindSub, remindList;
  if (remindItems.length) {
    const today = new Date();
    const pad = n => String(n).padStart(2, "0");
    const todayStr = `${today.getFullYear()}-${pad(today.getMonth()+1)}-${pad(today.getDate())}`;
    remindTitle = remindDate === todayStr ? "今日提醒" : "最近排班提醒";
    remindSub = `<span class="sub">${shEscape(remindDate)} · 到点自动提醒</span>`;
    remindList = remindItems.map(([t, a, s]) =>
      `<div class="remind-item"><span class="remind-time">${shEscape(t)}</span><span><span class="remind-slot">${shEscape(s)}</span> · <span class="remind-name">${shEscape(a)}</span></span></div>`
    ).join("");
  } else {
    remindTitle = "今日提醒";
    remindSub = '<span class="sub">暂无排班数据</span>';
    remindList = '<div class="remind-empty">今日暂无排班，添加数据后自动生成提醒</div>';
  }
  const sheetHtml = `<div class="sheet-panel" id="sheet-panel">
  <div class="sheet-head">
    <span class="sheet-title">Excel Sheet · 排班编辑</span>
    <div class="sheet-actions">
      <button id="sheet-add-col">＋列</button>
      <button id="sheet-add-row">＋行</button>
      <button class="sheet-save" id="sheet-save">保存</button>
      <button id="sheet-collapse">收起</button>
    </div>
  </div>
  <div class="sheet-wrap"><table class="sheet-table" id="sheet-table"></table></div>
  <div class="sheet-status" id="sheet-status">加载中…</div>
  <div class="sheet-token" id="sheet-token">
    <input type="password" id="sheet-token-input" placeholder="GitHub Token（ghp_ 或 github_pat_ 开头）">
    <div class="sheet-token-actions">
      <button class="btn-primary" id="sheet-token-save">保存 Token</button>
      <button id="sheet-token-clear">清除</button>
    </div>
  </div>
</div>
<script src="sheet.js"><\/script>`;
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>【7X官方直播间】直播排班表</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>${SHEET_CSS}</style>
</head>
<body>

<nav class="pill-nav">
  <a class="active" href="#schedule">排班表</a>
  <a href="#reminder">提醒</a>
  <a href="#help">说明</a>
  <a href="editor.html" target="_blank">在线编辑</a>
</nav>

<main class="content">
  <section class="hero" id="top">
    <div class="hero-inner">
      <div class="hero-eyebrow">Schedule Reminder · 7X Official Live</div>
      <h1>排班一眼看清，提醒准时到达</h1>
      <p class="hero-sub">直播排班 · 角色分工 · 每日提醒，一站掌握 7X 官方直播间全流程。</p>
      <div class="hero-actions">
        <a class="btn-primary" href="#schedule">查看排班</a>
        <a class="btn-glass" href="#help">如何设置</a>
      </div>
    </div>
  </section>

  ${marquee}

  <div class="cards-grid">
    <section class="glass-card" id="schedule">
      <header class="card-head">
        <div>
          <h2>排班表</h2>
          <p class="sub">数据更新 <time>${updatedAt}</time></p>
        </div>
        <div class="stats" id="stats">${shChips()}</div>
      </header>
      <div class="table-scroll">
        <table>
          <thead>
            <tr><th class="col-slot">场次</th><th class="col-role">角色</th>${dateHeader}</tr>
          </thead>
          <tbody>${rows.join("")}</tbody>
        </table>
      </div>
    </section>

    <aside class="glass-card remind-card" id="reminder">
      <header class="card-head">
        <div>
          <h2>${remindTitle}</h2>
          ${remindSub}
        </div>
      </header>
      ${remindList}
    </aside>
  </div>

  <div class="note" id="help">
    <span>深蓝为主播 · 赤陶为车型 · 圆点为未排班（周末/节假日/未填写）</span>
    <span class="tag">Frosted 3D Style · Marvis Schedule</span>
  </div>
</main>
${sheetHtml}
</body>
</html>`;
}

/* ---------- 保存 ---------- */
async function shSave(){
  document.querySelectorAll("#sheet-table td.sheet-cell").forEach(td => {
    const d = td.dataset.sd, s = td.dataset.ss, r = td.dataset.sr;
    if (!sheetSchedule[d]) sheetSchedule[d] = {};
    if (!sheetSchedule[d][s]) sheetSchedule[d][s] = {};
    sheetSchedule[d][s][r] = td.innerText.trim();
  });
  const clean = {};
  Object.keys(sheetSchedule).sort().forEach(d => {
    const slots = {};
    Object.keys(sheetSchedule[d]).forEach(s => {
      const info = {};
      let has = false;
      SHEET_ROLES.forEach(([rk]) => {
        const v = (sheetSchedule[d][s][rk] || "").trim();
        info[rk] = v;
        if (v) has = true;
      });
      if (has) slots[s] = info;
    });
    if (Object.keys(slots).length) clean[d] = slots;
  });
  sheetSchedule = clean;
  sheetCfg.display_dates = sheetDates.slice();

  if (!shToken()) {
    $sh("sheet-token").style.display = "block";
    shStatus("请先输入 GitHub Token 后保存", true);
    $sh("sheet-token-input").focus();
    return;
  }

  const now = new Date();
  const pad = n => String(n).padStart(2, "0");
  const updatedAt = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
  const html = shPage(updatedAt);

  shStatus("正在保存并发布…");
  const btn = $sh("sheet-save");
  if (btn) btn.disabled = true;
  try {
    await shPut("schedule.json", JSON.stringify(sheetSchedule, null, 2) + "\n");
    await shPut("config.json", JSON.stringify(sheetCfg, null, 2) + "\n");
    await shPut("index.html", html);
    await shPut("output/schedule.html", html);
    shStatus("保存成功！GitHub Pages 约 1~2 分钟后自动更新。");
  } catch (e) {
    shStatus(e.message, true);
    if (/Bad credentials|401/.test(e.message)) $sh("sheet-token").style.display = "block";
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* ---------- 初始化 ---------- */
function shInit(){
  const p = $sh("sheet-panel");
  const addCol = $sh("sheet-add-col");
  const addRow = $sh("sheet-add-row");
  const save = $sh("sheet-save");
  const collapse = $sh("sheet-collapse");
  if (!p || !addCol || !addRow || !save || !collapse) return;
  addCol.addEventListener("click", shAddCol);
  addRow.addEventListener("click", shAddRow);
  save.addEventListener("click", shSave);
  collapse.addEventListener("click", () => {
    const collapsed = p.classList.toggle("collapsed");
    const w = $sh("sheet-wrap"), st = $sh("sheet-status"), tk = $sh("sheet-token");
    if (w) w.style.display = collapsed ? "none" : "";
    if (st) st.style.display = collapsed ? "none" : "";
    if (tk) tk.style.display = collapsed ? "none" : "";
    collapse.textContent = collapsed ? "展开" : "收起";
  });
  const tkSave = $sh("sheet-token-save");
  const tkClear = $sh("sheet-token-clear");
  if (tkSave) tkSave.addEventListener("click", () => {
    const t = ($sh("sheet-token-input").value || "").trim();
    if (!t) { shStatus("Token 不能为空", true); return; }
    localStorage.setItem("gh_token", t);
    $sh("sheet-token").style.display = "none";
    $sh("sheet-token-input").value = "";
    shStatus("Token 已保存（仅本浏览器有效）");
  });
  if (tkClear) tkClear.addEventListener("click", () => {
    localStorage.removeItem("gh_token");
    $sh("sheet-token-input").value = "";
    shStatus("Token 已清除");
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => { shInit(); shLoad(); });
} else {
  shInit();
  shLoad();
}
