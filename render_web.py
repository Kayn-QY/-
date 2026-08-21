#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页排班表渲染：极氪日播间排班 · 多直播间版
支持 7X / 8X / 9X / 猎装 四个直播间（后续可增加），左下角 Excel 式 Sheet 标签切换。
设计风格：毛玻璃 3D 版（Frosted Glass + 3D Depth）
数据层：schedule.json = {room: {date: {slot: {role: value}}}}
注意：CSS_TEMPLATE 与 editor.html 中 CSS_VIEW、PAGE_JS 需保持一致。
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
ROLES = [
    ("time", "直播时间"),
    ("car", "直播车型"),
    ("anchor", "主播"),
]
SLOT_ORDER = ["第1场", "第2场", "第3场", "第4场", "第5场", "第6场"]
MARQUEE_ITEMS = ["Bilibili", "GitHub", "Vercel", "Figma", "Notion", "Slack"]
SITE_TITLE = "极氪日播间排班"
DEFAULT_ROOMS = ["7X", "8X", "9X", "猎装"]

CSS_TEMPLATE = """
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
.hero-body{position:relative;width:100%;display:flex;align-items:center;gap:32px;padding:44px 48px}
.hero-inner{flex:0 0 auto;font-family:var(--font-display);color:#fff;min-width:0}
.hero-eyebrow{font-size:13px;color:var(--peach);font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px;text-shadow:0 1px 8px rgba(0,0,0,.2)}
.hero h1{font-size:clamp(30px,4.6vw,46px);font-weight:700;line-height:1.1;max-width:560px;text-shadow:0 2px 20px rgba(0,0,0,.25)}
.hero-sub{margin-top:14px;font-size:15px;font-family:var(--font-sans);color:rgba(255,255,255,.85);max-width:520px;text-shadow:0 1px 10px rgba(0,0,0,.2)}
.hero-actions{margin-top:28px;display:flex;gap:12px;flex-wrap:wrap;font-family:var(--font-sans)}
/* 紧凑提醒卡片 - 全直播间 */
.hero-remind{
  flex:1 1 440px;min-width:320px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.4);
  border-radius:24px;padding:16px 18px;backdrop-filter:blur(16px) saturate(1.3);-webkit-backdrop-filter:blur(16px) saturate(1.3);
  box-shadow:0 20px 50px rgba(10,27,51,.25), inset 0 1px 0 rgba(255,255,255,.5);
}
.hero-remind-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.hero-remind-title{font-size:13px;font-weight:700;color:#fff;letter-spacing:.02em}
.hero-remind-badge{font-size:10.5px;color:var(--peach);border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:2px 9px;background:rgba(255,255,255,.12)}
.hero-remind-list{display:flex;flex-direction:column;gap:5px}
.hero-remind-item{
  display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.9);border-radius:10px;padding:6px 10px;
  box-shadow:inset 0 1px 0 #fff, 0 2px 8px rgba(10,27,51,.08);
}
.hero-remind-room{font-weight:700;color:#fff;background:linear-gradient(135deg,#0a1b33,#1e3a5f);border-radius:7px;padding:2px 8px;font-size:11px;flex-shrink:0}
.hero-remind-info{flex:1;min-width:0;display:flex;align-items:center;gap:8px}
.hero-remind-slot{font-size:12px;font-weight:600;color:#0a1b33;white-space:nowrap}
.hero-remind-name{font-size:11.5px;color:var(--clay);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hero-remind-name.off{color:var(--text-muted);font-weight:500}
.hero-remind-time{font-size:11px;color:var(--text-muted);white-space:nowrap;margin-left:auto}
.remind-empty{
  margin-top:12px;background:rgba(255,255,255,.4);border:1px dashed rgba(255,255,255,.7);border-radius:16px;
  padding:18px;font-size:13px;color:var(--text-muted);text-align:center;
}
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
.cards-grid{display:grid;grid-template-columns:1fr;gap:18px;margin-top:24px;align-items:start}
.glass-card{
  border-radius:28px;border:1px solid rgba(255,255,255,.6);
  background:linear-gradient(150deg, rgba(255,255,255,.56), rgba(255,255,255,.3));
  backdrop-filter:blur(22px) saturate(1.5);-webkit-backdrop-filter:blur(22px) saturate(1.5);
  box-shadow:0 30px 60px rgba(20,30,50,.2), inset 0 1px 0 rgba(255,255,255,.8);
  padding:24px;animation:rise .6s cubic-bezier(.16,1,.3,1) both;
}
.card-head{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.card-head h2{font-family:var(--font-display);font-size:18px;font-weight:600;color:#0f1e3d}
.card-head .sub{margin-top:6px;font-size:12px;color:var(--text-muted)}
.card-head .sub time{color:#0f1e3d;font-weight:500}
.head-right{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:flex-end}
/* 统计 chips */
.stats{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.chip{
  font-size:12px;color:#3d4c66;background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.7);
  border-radius:999px;padding:6px 12px;box-shadow:inset 0 1px 0 #fff;transition:transform .2s;
}
.chip b{color:var(--clay);font-weight:600}
.chip:hover{transform:translateY(-1px)}
/* 表格：左右双容器方案A —— 左面板固定承载场次/角色，右侧独立横向滚动日期表 */
.room-table{overflow:hidden;border-radius:16px}
.schedule-wrap{
  display:flex;align-items:flex-start;gap:10px;
  border-radius:16px;background:rgba(240,246,255,.45);
}
/* 左面板：场次+角色固定，不随横向滚动移动，纵向与右侧一起滚动 */
.left-panel{
  flex:0 0 auto;width:194px;position:sticky;left:0;z-index:5;align-self:stretch;
  background:rgba(255,255,255,.35);
  backdrop-filter:blur(20px) saturate(1.4);-webkit-backdrop-filter:blur(20px) saturate(1.4);
  border-radius:16px;border:1px solid rgba(255,255,255,.65);
  box-shadow:0 4px 14px rgba(15,30,61,.06), inset 0 1px 0 rgba(255,255,255,.6);
}
.left-panel .left-table{width:100%;border-collapse:separate;border-spacing:6px;font-size:12.5px;table-layout:fixed}
/* 右侧：日期表横向滚动容器 */
.right-scroll{
  flex:1 1 auto;min-width:0;overflow-x:auto;
  border-radius:16px;background:rgba(255,255,255,.32);
}
.right-scroll .right-table{
  width:100%;margin:0 auto;
  border-collapse:separate;border-spacing:6px;font-size:12.5px;table-layout:fixed;
}
/* 表头：左右统一固定高度，保证左侧场次/角色面板与右侧日期表逐行对齐 */
thead th{
  background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.7);border-radius:12px;
  box-shadow:inset 0 1px 0 #fff;color:#1f2c44;font-weight:600;padding:10px 8px;white-space:nowrap;text-align:center;
  height:56px;vertical-align:middle;
}
.left-panel thead th{background:rgba(255,255,255,.55)}
.date-col{width:96px;font-weight:600}
.date-col .wd{display:block;font-size:10px;color:var(--text-muted);font-weight:400;margin-top:2px}
.date-col.today{background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;border-color:transparent}
.date-col.today .wd{color:rgba(255,255,255,.92)}
/* 周导航 */
.week-nav{display:flex;align-items:center;gap:8px;flex:0 0 auto}
.week-btn{
  border:1px solid rgba(255,255,255,.7);background:rgba(255,255,255,.5);color:#334155;
  border-radius:999px;padding:7px 14px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:var(--font-sans);
  box-shadow:inset 0 1px 0 #fff;transition:all .2s;white-space:nowrap;
}
.week-btn:hover{background:rgba(255,255,255,.78)}
.week-label{font-size:12.5px;font-weight:600;color:var(--text-main);white-space:nowrap;letter-spacing:.02em}
.slot-col{width:92px;color:#334155;font-weight:500}
.role-col{width:96px;color:var(--text-muted);font-size:11.5px;font-weight:500}
td{
  border:1px solid rgba(255,255,255,.7);border-radius:12px;padding:9px 6px;text-align:center;
  color:#334155;vertical-align:middle;background:rgba(255,255,255,.55);box-shadow:inset 0 1px 0 #fff;
  transition:background .15s,transform .15s;
  height:44px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
tbody tr:hover td{background:rgba(255,255,255,.72)}
.slot-badge{
  display:inline-flex;align-items:center;justify-content:center;min-width:46px;padding:4px 8px;border-radius:999px;
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;font-weight:600;font-size:11px;
  box-shadow:0 6px 14px rgba(10,27,51,.3);
}
.cell{min-height:26px}
.cell.anchor{color:#334155;font-weight:500}
.cell.car{color:#334155;font-weight:500}
.cell.time{background:#eaf3ff;color:#0f1e3d;font-weight:500}
.cell.empty{background:rgba(255,255,255,.32);color:rgba(31,44,68,.25);border-color:rgba(255,255,255,.4)}
/* 提醒卡片（hero 区紧凑版，样式见 .hero-remind*） */
.remind-empty{
  margin-top:12px;background:rgba(255,255,255,.4);border:1px dashed rgba(255,255,255,.7);border-radius:16px;
  padding:18px;font-size:13px;color:var(--text-muted);text-align:center;
}
/* 底部说明 */
.note{margin-top:20px;font-size:12px;color:var(--text-muted);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:0 4px}
.note .tag{letter-spacing:.06em;text-transform:uppercase;font-size:10.5px;color:rgba(74,90,114,.75)}
/* 排班表标题栏内嵌 Excel 式 Sheet 标签栏 */
.sheet-bar{
  display:flex;align-items:center;gap:6px;
  padding:6px 8px;border-radius:16px;max-width:100%;overflow-x:auto;
  background:linear-gradient(135deg, rgba(255,255,255,.66), rgba(255,255,255,.42));
  backdrop-filter:blur(24px) saturate(1.6);-webkit-backdrop-filter:blur(24px) saturate(1.6);
  border:1px solid rgba(255,255,255,.75);
  box-shadow:0 18px 40px rgba(20,30,50,.24), inset 0 1px 0 rgba(255,255,255,.9);
  font-family:var(--font-sans);
}
.sheet-tab{
  border:1px solid rgba(255,255,255,.7);background:rgba(255,255,255,.5);color:#334155;
  border-radius:12px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;
  box-shadow:inset 0 1px 0 #fff;transition:all .2s ease;font-family:var(--font-sans);
}
.sheet-tab:hover{background:rgba(255,255,255,.75)}
.sheet-tab.active{
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;border-color:transparent;
  box-shadow:0 8px 18px rgba(10,27,51,.35);
}
/* 直播间独立表格 */
.room-table{display:none}
.room-table.active{display:block;animation:rise .4s cubic-bezier(.16,1,.3,1) both}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:1024px){
  .cards-grid{grid-template-columns:1fr}
  .content{padding:72px 18px 48px}
  .hero-body{flex-direction:column;align-items:stretch}
  .hero-remind{width:100%}
}
@media (max-width:640px){
  .hero-body{padding:28px 14px}
  .hero-inner{padding:0;width:100%}
  .hero h1{font-size:clamp(46px,18.4vw,69px)}
  .hero-remind{padding:14px 14px}
  .hero-remind-item{padding:5px 8px}
  .glass-card{padding:18px 14px;border-radius:20px;width:100%}
  .head-right{flex-direction:column;align-items:stretch;justify-content:flex-start;width:100%;gap:10px}
  .week-nav{display:none}
  .sheet-bar{max-width:100%;flex-wrap:wrap}
  .schedule-wrap{display:flex;gap:10px}
  .left-panel{flex:0 0 calc(50% - 5px);width:calc(50% - 5px);min-width:0}
  .right-scroll{flex:0 0 calc(50% - 5px);width:calc(50% - 5px);min-width:0}
  .left-panel th.col-slot,.slot-col{width:58px!important}
  .left-panel th.col-role,.role-col{width:84px!important;font-size:11.5px;padding:4px 2px;white-space:nowrap;overflow:hidden}
  .date-col{width:100%!important}
  .date-col .d-top{font-size:11px;white-space:nowrap}
  .date-col .d-sub{font-size:9px;white-space:nowrap}
  .right-scroll .right-table{min-width:0;width:100%}
  .right-scroll td.time-cell{font-size:10px;padding:2px 1px;white-space:nowrap;overflow:hidden}
  .hidden-d{display:none!important}
}
"""

# 页面内嵌 JS：切换直播间 + 新增直播间 + 重新渲染（与 editor.html 中 PAGE_JS 保持一致，禁止使用反引号/模板字符串）
PAGE_JS = r"""
"use strict";
var WEEKDAYS_JS = ["周日","周一","周二","周三","周四","周五","周六"];
var ROLES_JS = [["time","直播时间"],["car","直播车型"],["anchor","主播"]];
var SLOT_ORDER_JS = ["第1场","第2场","第3场","第4场","第5场","第6场"];
var MARQUEE_JS = ["Bilibili","GitHub","Vercel","Figma","Notion","Slack"];

var SCHEDULE = __SCHEDULE_JSON__;
var CFG = __CFG_JSON__;
var ROOMS = (CFG.rooms && CFG.rooms.length) ? CFG.rooms.slice() : Object.keys(SCHEDULE);
var CSS_TEMPLATE_JS = __CSS_TEMPLATE_JSON__;
var PAGE_JS_SRC = __PAGE_JS_JSON__;

function esc(s){ return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function fmtD(d){ return d.slice(5).replace("-", "/"); }
function parseD(s){ var m = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/); if (m) return new Date(+m[1], +m[2]-1, +m[3]); return null; }
function weekOf(d){ var dt = parseD(d); return dt ? WEEKDAYS_JS[dt.getDay()] : ""; }

function displayDatesFor(){
  return weekDates();
}
/* ---- 7天周窗口：默认本周（周一~周日），上周/下周翻页 ---- */
function toISO(d){ return d.getFullYear() + "-" + pad2(d.getMonth()+1) + "-" + pad2(d.getDate()); }
function mondayOf(d){ var x = new Date(d.getFullYear(), d.getMonth(), d.getDate()); var day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); return x; }
var weekStart = mondayOf(bjNow());
function weekDates(){
  var out = [];
  for (var i = 0; i < 7; i++){ var x = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + i); out.push(toISO(x)); }
  return out;
}
function todayISO(){ return toISO(bjNow()); }
function fmtShort(d){ return d.slice(5).replace("-", "/"); }
function weekLabel(){ var ws = weekDates(); return fmtShort(ws[0]) + " ~ " + fmtShort(ws[6]); }
function shiftWeek(n){ weekStart.setDate(weekStart.getDate() + n * 7); renderAllTables(); }
function renderAllTables(){
  var active = "";
  document.querySelectorAll(".sheet-tab").forEach(function(t){ if (t.classList.contains("active")) active = t.dataset.room; });
  var wrap = document.querySelector(".room-tables");
  if (wrap) wrap.innerHTML = ROOMS.map(buildRoomTable).join("");
  if (active) switchRoom(active);
  var lbl = document.getElementById("week-label");
  if (lbl) lbl.textContent = weekLabel();
  applyMobileView();
}

function buildRoomTable(room){
  var dates = displayDatesFor();
  var data = SCHEDULE[room] || {};
  var today = todayISO();
  var dateHeader = dates.map(function(d){ return '<th class="date-col' + (d === today ? " today" : "") + '" data-d="' + d + '">' + fmtD(d) + '<span class="wd">' + weekOf(d) + '</span></th>'; }).join("");
  var leftRows = [];
  var rightRows = [];
  SLOT_ORDER_JS.forEach(function(slot){
    ROLES_JS.forEach(function(pair){
      var rk = pair[0], rn = pair[1];
      var cells = "";
      dates.forEach(function(d){
        var val = "";
        if (data[d] && data[d][slot] && data[d][slot][rk] !== undefined) val = data[d][slot][rk];
        if (val){
          var cls = "cell";
          if (rk === "anchor") cls = "cell anchor";
          else if (rk === "car") cls = "cell car";
          else if (rk === "time") cls = "cell time";
          cells += '<td class="' + cls + '" data-d="' + d + '">' + esc(val) + '</td>';
        } else {
          cells += '<td class="cell empty" data-d="' + d + '">·</td>';
        }
      });
      var rowLabel = rk === "time" ? '<span class="slot-badge">' + slot + '</span>' : "";
      var trCls = rk === "time" ? ' class="row-slot"' : "";
      leftRows.push('<tr' + trCls + '><td class="slot-col">' + rowLabel + '</td><td class="role-col">' + rn + '</td></tr>');
      rightRows.push('<tr' + trCls + '>' + cells + '</tr>');
    });
  });
  return '<div class="room-table" data-room="' + esc(room) + '"><div class="schedule-wrap"><div class="left-panel"><table class="left-table"><thead><tr><th class="col-slot">场次</th><th class="col-role">角色</th></tr></thead><tbody>' + leftRows.join("") + '</tbody></table></div><div class="right-scroll"><table class="right-table"><thead><tr>' + dateHeader + '</tr></thead><tbody>' + rightRows.join("") + '</tbody></table></div></div></div>';
}

function buildTabs(){
  return ROOMS.map(function(r, i){
    return '<button class="sheet-tab' + (i === 0 ? " active" : "") + '" data-room="' + esc(r) + '">' + esc(r) + '</button>';
  }).join("");
}

function buildStats(room){
  var data = SCHEDULE[room] || {};
  var counter = {};
  var today = todayISO();
  var day = data[today];
  if (day && typeof day === "object") {
    Object.keys(day).forEach(function(s){
      var n = (day[s].anchor || "").trim();
      if (n) counter[n] = (counter[n] || 0) + 1;
    });
  }
  var arr = Object.keys(counter).map(function(n){ return '<span class="chip">主播 <b>' + esc(n) + '</b> × ' + counter[n] + ' 场</span>'; });
  if (arr.length) return arr.join("");
  return room === "问我我"
    ? '<a class="chip chip-edit" href="editor.html" target="_blank">在线编辑</a>'
    : '<span class="chip">今日暂无</span>';
}

function pad2(n){ return n < 10 ? "0" + n : String(n); }
function bjNow(){
  var n = new Date();
  return new Date(n.getTime() + (n.getTimezoneOffset() + 480) * 60000);
}
function clockMin(t){
  var m = String(t).match(/^(\d{1,2}):(\d{2})/);
  return m ? (+m[1]) * 60 + (+m[2]) : -1;
}
/* 未来最近一场：当天无剩余场次自动取之后最近一天首场 */
function nextRemind(room){
  var data = SCHEDULE[room] || {};
  var now = bjNow();
  var best = null;
  var dates = Object.keys(data).sort();
  for (var i = 0; i < dates.length; i++){
    var d = dates[i];
    var day = data[d];
    if (!day || typeof day !== "object") continue;
    for (var j = 0; j < SLOT_ORDER_JS.length; j++){
      var slot = SLOT_ORDER_JS[j];
      var info = day[slot] || {};
      var mm = clockMin(info.time);
      if (mm < 0) continue;
      var start = new Date(+d.slice(0,4), +d.slice(5,7) - 1, +d.slice(8,10), Math.floor(mm / 60), mm % 60);
      if (start <= now) continue;
      if (!best || start < best.start) best = { start: start, slot: slot, anchor: (info.anchor || "").trim() };
    }
  }
  return best;
}
function countdownText(start){
  var diffMin = Math.round((start - bjNow()) / 60000);
  if (diffMin < 1) return "即将开播";
  if (diffMin < 60) return diffMin + "分钟后";
  var h = diffMin / 60;
  if (h < 24) return (Math.round(h * 10) / 10) + "小时后";
  var d = Math.floor(h / 24);
  return d + "天后";
}
function buildRemind(){
  var items = [];
  ROOMS.forEach(function(room){
    var b = nextRemind(room);
    if (!b){
      items.push('<div class="hero-remind-item"><span class="hero-remind-room">' + esc(room) + '</span><div class="hero-remind-info"><span class="hero-remind-slot">暂无排班</span><span class="hero-remind-name off">暂无数据</span></div><span class="hero-remind-time">—</span></div>');
      return;
    }
    var st = b.slot + " " + pad2(b.start.getHours()) + ":" + pad2(b.start.getMinutes());
    var cd = countdownText(b.start);
    if (b.anchor){
      items.push('<div class="hero-remind-item"><span class="hero-remind-room">' + esc(room) + '</span><div class="hero-remind-info"><span class="hero-remind-slot">' + st + '</span><span class="hero-remind-name">' + esc(b.anchor) + '</span></div><span class="hero-remind-time">' + cd + '</span></div>');
    } else {
      items.push('<div class="hero-remind-item"><span class="hero-remind-room">' + esc(room) + '</span><div class="hero-remind-info"><span class="hero-remind-slot">' + st + '</span><span class="hero-remind-name off">无人播</span></div><span class="hero-remind-time">' + cd + '</span></div>');
    }
  });
  if (!items.length) return '<div class="remind-empty">各直播间暂无排班数据，添加后自动生成提醒</div>';
  return '<div class="hero-remind-list">' + items.join("") + '</div>';
}
function updateRemind(){
  var el = document.getElementById("reminder");
  if (!el) return;
  var list = el.querySelector(".hero-remind-list");
  var html = buildRemind();
  if (list) list.outerHTML = html;
  else el.insertAdjacentHTML("beforeend", html);
}

function renderHtml(updatedAt){
  var roomTables = ROOMS.map(buildRoomTable).join("");
  var tabs = buildTabs();
  var statsAll = ROOMS.map(function(r, i){
    return '<div class="stats" data-stats-for="' + esc(r) + '"' + (i === 0 ? "" : ' style="display:none"') + '>' + buildStats(r) + '</div>';
  }).join("");
  var marqueeItems = MARQUEE_JS.map(function(it){ return '<span>' + it + '</span>'; }).join("");
  var marquee = '<div class="marquee"><div class="marquee-track">' + marqueeItems + marqueeItems + '</div></div>';
  var remindList = buildRemind();
  var h = "";
  h += '<!DOCTYPE html>\n';
  h += '<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">\n';
  h += '<title>极氪日播间排班 · 多直播间</title>\n';
  h += '<link rel="preconnect" href="https://fonts.googleapis.com">\n';
  h += '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n';
  h += '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">\n';
  h += '<style>__CSS_TEMPLATE__</style>\n</head>\n<body>\n';
  h += '<main class="content">\n';
  h += '  <section class="hero" id="top">\n    <div class="hero-body">\n      <div class="hero-inner">\n';
  h += '      <div class="hero-eyebrow">Schedule Reminder · ZEEKR Daily Live</div>\n';
  h += '      <h1>极氪日播间排班</h1>\n';
  h += '      <p class="hero-sub">' + ROOMS.join(" · ") + ' · 多直播间独立排班</p>\n';
  h += '      <div class="hero-actions">\n        <a class="btn-primary" href="#schedule">查看排班</a>\n        <a class="btn-glass" href="editor.html" target="_blank">在线编辑</a>\n      </div>\n      </div>\n';
  h += '      <aside class="hero-remind" id="reminder">\n        <div class="hero-remind-head">\n          <span class="hero-remind-title">最近排班提醒</span>\n          <span class="hero-remind-badge">全部直播间</span>\n        </div>\n        ' + remindList + '\n      </aside>\n    </div>\n  </section>\n';
  h += '  ' + marquee + '\n';
  h += '  <div class="cards-grid">\n';
  h += '    <section class="glass-card" id="schedule">\n      <header class="card-head">\n';
  h += '        <div>\n          <h2>排班表</h2>\n          <p class="sub">数据更新 <time>' + esc(updatedAt) + '</time></p>\n        </div>\n';
  h += '        <div class="head-right">\n          <div class="week-nav">\n            <button class="week-btn" id="btn-prev-week">‹ 上周</button>\n            <span class="week-label" id="week-label">' + weekLabel() + '</span>\n            <button class="week-btn" id="btn-next-week">下周 ›</button>\n          </div>\n          <div class="sheet-bar" id="sheet-bar">' + tabs + '</div>\n          <div class="stats-wrap">' + statsAll + '</div>\n        </div>\n      </header>\n';
  h += '      <div class="room-tables">' + roomTables + '</div>\n    </section>\n  </div>\n';
  h += '  <div class="note" id="help">\n';
  h += '    <span>深蓝为主播 · 赤陶为车型 · 圆点为未排班（周末/节假日/未填写）</span>\n';
  h += '    <span class="tag">Frosted 3D Style · Marvis Schedule</span>\n  </div>\n';
  h += '</main>\n';
  h += '<script>__PAGE_JS__</' + 'script>\n';
  h += '</body>\n</html>';
  return h;
}

function switchRoom(room){
  document.querySelectorAll(".sheet-tab").forEach(function(t){ t.classList.toggle("active", t.dataset.room === room); });
  document.querySelectorAll(".room-table").forEach(function(t){ t.classList.toggle("active", t.dataset.room === room); });
  document.querySelectorAll("[data-stats-for]").forEach(function(s){ s.style.display = (s.dataset.statsFor === room) ? "" : "none"; });
}

function ghGetSha(path){
  var token = (localStorage.getItem("gh_token") || "").trim();
  return fetch("https://api.github.com/repos/Kayn-QY/-/contents/" + path, { headers: { Authorization: "Bearer " + token } })
    .then(function(r){ if (!r.ok) { if (r.status === 404) return null; throw new Error("获取 " + path + " 失败: HTTP " + r.status); } return r.json(); })
    .then(function(j){ return j ? j.sha : null; });
}
function ghPut(path, content){
  return ghGetSha(path).then(function(sha){
    var body = { message: "在线编辑排班表", content: btoa(unescape(encodeURIComponent(content))) };
    if (sha) body.sha = sha;
    return fetch("https://api.github.com/repos/Kayn-QY/-/contents/" + path, {
      method: "PUT",
      headers: { Authorization: "Bearer " + (localStorage.getItem("gh_token") || "").trim(), "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function(r){
      if (!r.ok) { throw new Error("更新 " + path + " 失败: HTTP " + r.status); }
    });
  });
}

function addRoom(){
  var name = prompt("输入新直播间名称：");
  if (!name) return;
  var room = name.trim();
  if (!room) { alert("直播间名称不能为空"); return; }
  if (ROOMS.indexOf(room) >= 0) { alert("直播间「" + room + "」已存在"); return; }
  var token = (localStorage.getItem("gh_token") || "").trim();
  if (!token) { alert("新增直播间需要 GitHub Token（请先在在线编辑器保存 Token 后重试）。"); window.open("editor.html", "_blank"); return; }
  SCHEDULE[room] = {};
  CFG.rooms = ROOMS.concat([room]);
  ROOMS = CFG.rooms.slice();
  var now = new Date();
  var pad = function(n){ return String(n).padStart(2, "0"); };
  var updatedAt = now.getFullYear() + "-" + pad(now.getMonth()+1) + "-" + pad(now.getDate()) + " " + pad(now.getHours()) + ":" + pad(now.getMinutes());
  var html = renderHtml(updatedAt).replace("__CSS_TEMPLATE__", CSS_TEMPLATE_JS).replace("__PAGE_JS__", PAGE_JS_SRC);
  ghPut("schedule.json", JSON.stringify(SCHEDULE, null, 2) + "\n")
    .then(function(){ return ghPut("config.json", JSON.stringify(CFG, null, 2) + "\n"); })
    .then(function(){ return ghPut("index.html", html); })
    .then(function(){ return ghPut("output/schedule.html", html); })
    .then(function(){ alert("已新增直播间「" + room + "」，刷新后生效"); location.reload(); })
    .catch(function(e){ alert("新增失败: " + e.message); });
}

function applyMobileView(){
  var mobile = window.matchMedia && window.matchMedia("(max-width:640px)").matches;
  document.querySelectorAll(".room-table").forEach(function(rt){
    var todayIdx = -1;
    rt.querySelectorAll(".right-table thead th.date-col").forEach(function(t, i){
      if (t.classList.contains("today")) todayIdx = i;
    });
    rt.querySelectorAll(".right-table thead th.date-col").forEach(function(t, i){
      t.classList.toggle("hidden-d", mobile && i !== todayIdx);
    });
    rt.querySelectorAll(".right-table tbody tr").forEach(function(tr){
      Array.prototype.forEach.call(tr.children, function(td, i){
        td.classList.toggle("hidden-d", mobile && i !== todayIdx);
      });
    });
  });
}

function initRoomPage(){
  document.addEventListener("click", function(e){
    var tab = e.target.closest(".sheet-tab");
    if (tab) { switchRoom(tab.dataset.room); return; }
  });
  var pw = document.getElementById("btn-prev-week");
  if (pw) pw.addEventListener("click", function(){ shiftWeek(-1); });
  var nw = document.getElementById("btn-next-week");
  if (nw) nw.addEventListener("click", function(){ shiftWeek(1); });
  applyMobileView();
  if (!window.__mvBound) { window.__mvBound = true; window.addEventListener("resize", applyMobileView); }
  updateRemind();
  setInterval(updateRemind, 30000);
}
initRoomPage();
"""


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schedule():
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_schedule(schedule):
    """旧结构 {date: {...}} → {"7X": {...}}，并补齐默认直播间"""
    if not isinstance(schedule, dict):
        return {r: {} for r in DEFAULT_ROOMS}
    keys = list(schedule.keys())
    is_old = bool(keys) and any("-" in k for k in keys) and not any(k in DEFAULT_ROOMS for k in keys)
    if is_old:
        return {"7X": schedule, "8X": {}, "9X": {}, "猎装": {}}
    result = dict(schedule)
    for r in DEFAULT_ROOMS:
        result.setdefault(r, {})
    return result


def rooms_of(cfg, schedule):
    rooms = cfg.get("rooms") or []
    if not rooms:
        rooms = [r for r in DEFAULT_ROOMS if r in schedule] or DEFAULT_ROOMS
    return rooms


def current_week_dates():
    """本周（周一~周日）7 天，按北京时间。展示/编辑均按自然周窗口显示。"""
    now_bj = datetime.utcnow() + timedelta(hours=8)
    monday = now_bj - timedelta(days=now_bj.weekday())
    return [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]


def build_room_table_html(room, data, dates, active=False):
    today = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d")
    date_header = "".join(
        f'<th class="date-col{" today" if d == today else ""}">{d[5:].replace("-", "/")}<span class="wd">{WEEKDAYS[datetime.strptime(d, "%Y-%m-%d").weekday()]}</span></th>'
        for d in dates
    )
    left_rows = []
    right_rows = []
    for slot in SLOT_ORDER:
        for role_key, role_name in ROLES:
            cells = []
            for d in dates:
                info = data.get(d, {}).get(slot, {})
                val = info.get(role_key, "")
                if val:
                    cls = "cell"
                    if role_key == "anchor":
                        cls = "cell anchor"
                    elif role_key == "car":
                        cls = "cell car"
                    elif role_key == "time":
                        cls = "cell time"
                    cells.append(f'<td class="{cls}">{val}</td>')
                else:
                    cells.append('<td class="cell empty">·</td>')
            row_label = f'<span class="slot-badge">{slot}</span>' if role_key == "time" else ""
            tr_cls = ' class="row-slot"' if role_key == "time" else ""
            left_rows.append(
                f'<tr{tr_cls}><td class="slot-col">{row_label}</td><td class="role-col">{role_name}</td></tr>'
            )
            right_rows.append(
                f'<tr{tr_cls}>{"".join(cells)}</tr>'
            )
    return (
        f'<div class="room-table{" active" if active else ""}" data-room="{room}">'
        f'<div class="schedule-wrap">'
        f'<div class="left-panel"><table class="left-table">'
        f'<thead><tr><th class="col-slot">场次</th><th class="col-role">角色</th></tr></thead>'
        f'<tbody>{"".join(left_rows)}</tbody></table></div>'
        f'<div class="right-scroll"><table class="right-table">'
        f'<thead><tr>{date_header}</tr></thead>'
        f'<tbody>{"".join(right_rows)}</tbody></table></div>'
        f'</div></div>'
    )


def build_stats_html(data, room):
    counter = Counter()
    today = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d")
    day = data.get(today)
    if isinstance(day, dict):
        for slot, info in day.items():
            name = (info.get("anchor", "") or "").strip()
            if name:
                counter[name] += 1
    if counter:
        return "".join(
            f'<span class="chip">主播 <b>{name}</b> × {cnt} 场</span>' for name, cnt in counter.most_common()
        )
    if room == "问我我":
        return '<a class="chip chip-edit" href="editor.html" target="_blank">在线编辑</a>'
    return '<span class="chip">今日暂无</span>'


def build_remind_html(schedule, rooms):
    """服务端预渲染：逐直播间输出未来最近一场（北京时间），与 PAGE_JS buildRemind 语义一致"""
    now_bj = datetime.utcnow() + timedelta(hours=8)

    def clock_min(t):
        m = re.match(r"^(\d{1,2}):(\d{2})", str(t or "").strip())
        return int(m.group(1)) * 60 + int(m.group(2)) if m else -1

    def countdown_text(start):
        diff_min = int(round((start - now_bj).total_seconds() / 60))
        if diff_min < 1:
            return "即将开播"
        if diff_min < 60:
            return f"{diff_min}分钟后"
        h = diff_min / 60
        if h < 24:
            h = round(h * 10) / 10
            return f"{h:g}小时后"
        d = int(h // 24)
        return f"{d}天后"

    items = []
    for room in rooms:
        data = schedule.get(room, {})
        best = None
        for d in sorted(data.keys()):
            day = data.get(d)
            if not isinstance(day, dict):
                continue
            try:
                day0 = datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                continue
            for slot in SLOT_ORDER:
                info = day.get(slot) or {}
                mm = clock_min(info.get("time", ""))
                if mm < 0:
                    continue
                start = day0.replace(hour=mm // 60, minute=mm % 60)
                if start <= now_bj:
                    continue
                if best is None or start < best["start"]:
                    best = {"start": start, "slot": slot, "anchor": (info.get("anchor") or "").strip()}
        if best is None:
            items.append(
                f'<div class="hero-remind-item"><span class="hero-remind-room">{room}</span>'
                f'<div class="hero-remind-info"><span class="hero-remind-slot">暂无排班</span>'
                f'<span class="hero-remind-name off">暂无数据</span></div>'
                f'<span class="hero-remind-time">—</span></div>'
            )
            continue
        st = best["slot"] + " " + best["start"].strftime("%H:%M")
        cd = countdown_text(best["start"])
        if best["anchor"]:
            items.append(
                f'<div class="hero-remind-item"><span class="hero-remind-room">{room}</span>'
                f'<div class="hero-remind-info"><span class="hero-remind-slot">{st}</span>'
                f'<span class="hero-remind-name">{best["anchor"]}</span></div>'
                f'<span class="hero-remind-time">{cd}</span></div>'
            )
        else:
            items.append(
                f'<div class="hero-remind-item"><span class="hero-remind-room">{room}</span>'
                f'<div class="hero-remind-info"><span class="hero-remind-slot">{st}</span>'
                f'<span class="hero-remind-name off">无人播</span></div>'
                f'<span class="hero-remind-time">{cd}</span></div>'
            )
    if not items:
        return '<div class="remind-empty">各直播间暂无排班数据，添加后自动生成提醒</div>'
    return '<div class="hero-remind-list">' + "".join(items) + "</div>"


def render_html(schedule, cfg):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    schedule = migrate_schedule(schedule)
    rooms = rooms_of(cfg, schedule)
    dates = current_week_dates()
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    room_tables = "".join(
        build_room_table_html(room, schedule.get(room, {}), dates, active=(i == 0)) for i, room in enumerate(rooms)
    )
    tabs = "".join(
        f'<button class="sheet-tab{" active" if i == 0 else ""}" data-room="{room}">{room}</button>'
        for i, room in enumerate(rooms)
    )
    _stats_parts = []
    for _i, room in enumerate(rooms):
        _hide = " style=\"display:none\"" if _i != 0 else ""
        _stats_parts.append(f'<div class="stats" data-stats-for="{room}"{_hide}>{build_stats_html(schedule.get(room, {}), room)}</div>')
    stats_all = "".join(_stats_parts)
    remind_list = build_remind_html(schedule, rooms)

    marquee_items_html = "".join(f"<span>{item}</span>" for item in MARQUEE_ITEMS)
    marquee_html = (
        f'<div class="marquee"><div class="marquee-track">{marquee_items_html}{marquee_items_html}</div></div>'
    )

    def _js_json(obj):
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    week_start_short = dates[0][5:].replace("-", "/")
    week_end_short = dates[6][5:].replace("-", "/")

    page_js = PAGE_JS.replace("__SCHEDULE_JSON__", _js_json(schedule))
    page_js = page_js.replace("__CFG_JSON__", _js_json(cfg))
    page_js = page_js.replace("__CSS_TEMPLATE_JSON__", _js_json(CSS_TEMPLATE))
    page_js = page_js.replace("__PAGE_JS_JSON__", _js_json(PAGE_JS))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>极氪日播间排班 · 多直播间</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS_TEMPLATE}</style>
</head>
<body>

<main class="content">
  <!-- Hero -->
  <section class="hero" id="top">
    <div class="hero-body">
      <div class="hero-inner">
        <div class="hero-eyebrow">Schedule Reminder · ZEEKR Daily Live</div>
        <h1>极氪日播间排班</h1>
        <p class="hero-sub">{" · ".join(rooms)} · 多直播间独立排班</p>
        <div class="hero-actions">
          <a class="btn-primary" href="#schedule">查看排班</a>
          <a class="btn-glass" href="editor.html" target="_blank">在线编辑</a>
        </div>
      </div>
      <aside class="hero-remind" id="reminder">
        <div class="hero-remind-head">
          <span class="hero-remind-title">最近排班提醒</span>
          <span class="hero-remind-badge">全部直播间</span>
        </div>
        {remind_list}
      </aside>
    </div>
  </section>

  <!-- 跑马灯 -->
  {marquee_html}

  <!-- 排班表 + 提醒 -->
  <div class="cards-grid">
    <section class="glass-card" id="schedule">
      <header class="card-head">
        <div>
          <h2>排班表</h2>
          <p class="sub">数据更新 <time>{updated_at}</time></p>
        </div>
        <div class="head-right">
          <div class="week-nav">
            <button class="week-btn" id="btn-prev-week">‹ 上周</button>
            <span class="week-label" id="week-label">{week_start_short} ~ {week_end_short}</span>
            <button class="week-btn" id="btn-next-week">下周 ›</button>
          </div>
          <div class="sheet-bar" id="sheet-bar">{tabs}</div>
          <div class="stats-wrap">{stats_all}</div>
        </div>
      </header>
      <div class="room-tables">{room_tables}</div>
    </section>
  </div>

  <div class="note" id="help">
    <span>深蓝为主播 · 赤陶为车型 · 圆点为未排班（周末/节假日/未填写）</span>
    <span class="tag">Frosted 3D Style · Marvis Schedule</span>
  </div>
</main>

<script>
{page_js}
</script>
</body>
</html>"""
    html_path = os.path.join(OUTPUT_DIR, "schedule.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {html_path}")
    return html_path


if __name__ == "__main__":
    cfg = load_config()
    schedule = load_schedule()
    render_html(schedule, cfg)
