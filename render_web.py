#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页排班表渲染：模仿原 Excel 表格结构（日期横向、场次纵向、角色行）
设计风格：Wandor（全屏视频 + 毛玻璃卡片）—— Geist/Special Elite 字体 + 赤陶强调
"""
import json
import os
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
    ("tech", "技术"),
    ("ad", "投流"),
]
SLOT_ORDER = ["第1场", "第2场", "第3场", "第4场", "第5场", "第6场"]

VIDEO_SRC = "https://pollen-batch-41236914.figma.site/_components/v2/f0ee2dae7671c170c34f12e31c4cb41418976c98/769c564298c132f7919405cd9f17c1b1231f341d.769c5642.mp4"

CSS_TEMPLATE = """
:root{
  --wandor-dark: #0a0a0a;
  --wandor-text: #1a1a1a;
  --wandor-muted: #767676;
  --wandor-prompt: #905831;
  --font-sans: "Geist", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-display: "Special Elite", "PingFang SC", serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{color-scheme:light}
body{font-family:var(--font-sans);background:#fff;color:var(--wandor-text);overflow-x:hidden;-webkit-font-smoothing:antialiased;min-height:100vh}
/* 背景视频：固定视口铺满，滚动时背景保持 */
.hero-video{position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;pointer-events:none}
/* 顶部白色渐变 overlay：保证导航与标题可读 */
.top-overlay{position:fixed;inset-x:0;top:0;height:687px;background:linear-gradient(180deg,rgba(255,255,255,1) 0%,rgba(255,255,255,0) 100%);pointer-events:none;z-index:1}
/* 导航 */
nav{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;padding:28px 80px 16px}
.wordmark{font-family:var(--font-display);font-size:40px;line-height:1;color:var(--wandor-text);user-select:none;letter-spacing:.02em}
.nav-links{position:absolute;left:50%;transform:translateX(-50%);display:flex;gap:32px}
.nav-link{background:transparent;border:none;cursor:pointer;font-family:var(--font-sans);font-size:15px;font-weight:500;text-transform:uppercase;color:var(--wandor-text);letter-spacing:.04em;text-decoration:none;transition:opacity .2s}
.nav-link:hover{opacity:.55}
.nav-actions{display:flex;align-items:center;gap:32px}
.btn-dark{display:inline-flex;align-items:center;background:var(--wandor-dark);color:#fafafa;border:none;cursor:pointer;font-family:var(--font-sans);font-size:15px;font-weight:500;text-transform:uppercase;letter-spacing:.04em;padding:14px 20px;border-radius:999px;text-decoration:none;transition:background-color .2s,transform .15s;white-space:nowrap}
.btn-dark:hover{background:#333}
.btn-dark:active{transform:scale(.95)}
.btn-ghost{background:transparent;border:none;cursor:pointer;font-family:var(--font-sans);font-size:15px;font-weight:600;text-transform:uppercase;color:#292929;letter-spacing:.04em;text-decoration:none;transition:opacity .2s}
.btn-ghost:hover{opacity:.55}
/* 内容区 */
.content{position:relative;z-index:2;max-width:1360px;margin:0 auto;padding:40px 80px 80px}
/* 毛玻璃卡片 */
.glass-card{background:rgba(255,255,255,.72);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);border:1px solid rgba(255,255,255,.65);border-radius:24px;box-shadow:0 24px 80px rgba(0,0,0,.18);padding:36px 40px;animation:rise .6s cubic-bezier(.16,1,.3,1) both}
.card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;flex-wrap:wrap;margin-bottom:28px}
.card-head h1{font-size:clamp(22px,2.8vw,30px);font-weight:700;letter-spacing:-.01em;line-height:1.15}
.card-head .sub{margin-top:8px;font-size:14px;color:var(--wandor-muted)}
.card-head .sub time{color:var(--wandor-text);font-weight:500}
/* 统计 chips */
.stats{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.chip{font-size:13px;color:var(--wandor-muted);background:rgba(255,255,255,.6);border:1px solid rgba(26,26,26,.08);border-radius:999px;padding:7px 14px;transition:border-color .2s,transform .2s}
.chip b{color:var(--wandor-prompt);font-weight:600}
.chip:hover{border-color:rgba(144,88,49,.4);transform:translateY(-1px)}
/* 表格 */
.table-scroll{overflow-x:auto;border-radius:14px}
table{width:100%;border-collapse:collapse;min-width:1260px;font-size:13px}
thead th{background:rgba(255,255,255,.55);color:var(--wandor-text);font-weight:600;padding:13px 10px;border-bottom:1px solid rgba(26,26,26,.10);white-space:nowrap;text-align:center}
.date-col{min-width:98px;font-weight:600}
.date-col .wd{display:block;font-size:11px;color:var(--wandor-muted);font-weight:400;margin-top:3px}
td{border-bottom:1px solid rgba(26,26,26,.07);padding:10px 10px;text-align:center;color:var(--wandor-text);vertical-align:middle;transition:background .15s}
tbody tr:hover td{background:rgba(0,0,0,.028)}
.row-slot td{border-top:1px solid rgba(26,26,26,.12)}
.slot-col{width:72px;color:var(--wandor-muted);font-weight:500}
.slot-badge{display:inline-flex;align-items:center;justify-content:center;min-width:48px;padding:4px 9px;border-radius:999px;background:rgba(144,88,49,.12);color:var(--wandor-prompt);font-weight:600;font-size:12px;letter-spacing:.02em}
.role-col{width:86px;color:var(--wandor-muted);font-size:12px;font-weight:500}
.cell{min-height:26px}
.cell.anchor{color:var(--wandor-prompt);font-weight:600}
.cell.empty{color:rgba(26,26,26,.22)}
/* 卡片底部说明 */
.note{margin-top:18px;font-size:12px;color:var(--wandor-muted);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.note .tag{letter-spacing:.06em;text-transform:uppercase;font-size:11px;color:rgba(118,118,118,.8)}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:900px){
  nav{padding:20px 24px 14px}
  .wordmark{font-size:32px}
  .nav-links{display:none}
  .content{padding:24px 16px 48px}
  .glass-card{padding:20px 16px;border-radius:18px}
}
@media (max-width:640px){
  .nav-actions{gap:12px}
  .btn-dark{padding:11px 16px;font-size:13px}
  .btn-ghost{display:none}
}
"""


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schedule():
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def display_dates(cfg, schedule):
    """确定展示的日期列：优先用配置，否则用数据范围"""
    if cfg.get("display_dates"):
        return cfg["display_dates"]
    dates = sorted(schedule.keys())
    if not dates:
        return []
    start, end = datetime.strptime(dates[0], "%Y-%m-%d"), datetime.strptime(dates[-1], "%Y-%m-%d")
    result = []
    cur = start
    while cur <= end:
        result.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return result


def anchor_stats(schedule):
    counter = Counter()
    for d, slots in schedule.items():
        for slot, info in slots.items():
            name = info.get("anchor", "").strip()
            if name:
                counter[name] += 1
    return counter.most_common()


def render_html(schedule, cfg):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dates = display_dates(cfg, schedule)
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    date_header = "".join(
        f'<th class="date-col">{d[5:].replace("-", "/")}<span class="wd">{WEEKDAYS[datetime.strptime(d, "%Y-%m-%d").weekday()]}</span></th>'
        for d in dates
    )

    # 场次行：每场次渲染 5 个角色行
    rows = []
    for slot in SLOT_ORDER:
        for role_key, role_name in ROLES:
            cells = []
            for d in dates:
                info = schedule.get(d, {}).get(slot, {})
                val = info.get(role_key, "")
                if val:
                    cls = "cell anchor" if role_key == "anchor" else "cell"
                    cells.append(f'<td class="{cls}">{val}</td>')
                else:
                    cells.append('<td class="cell empty">·</td>')
            if role_key == "time":
                row_label = f'<span class="slot-badge">{slot}</span>'
                tr_cls = ' class="row-slot"'
            else:
                row_label = ""
                tr_cls = ""
            rows.append(
                f'<tr{tr_cls}><td class="slot-col">{row_label}</td><td class="role-col">{role_name}</td>{"".join(cells)}</tr>'
            )

    counter = anchor_stats(schedule)
    if counter:
        stat_html = "".join(
            f'<span class="chip">主播 <b>{name}</b> × {cnt} 场</span>' for name, cnt in counter
        )
    else:
        stat_html = '<span class="chip">暂无数据</span>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>【7X官方直播间】直播排班表</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&family=Geist:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS_TEMPLATE}</style>
</head>
<body>
<video class="hero-video" src="{VIDEO_SRC}" autoplay muted loop playsinline></video>
<div class="top-overlay"></div>

<nav>
  <span class="wordmark">7X OPS</span>
  <div class="nav-links">
    <a class="nav-link" href="#stats">Stats</a>
    <a class="nav-link" href="#schedule">Schedule</a>
    <a class="nav-link" href="#help">Help</a>
  </div>
  <div class="nav-actions">
    <a class="btn-dark" href="editor.html" target="_blank">在线编辑</a>
  </div>
</nav>

<main class="content">
  <section class="glass-card" id="schedule">
    <header class="card-head">
      <div>
        <h1>【7X官方直播间】直播排班表</h1>
        <p class="sub">数据更新 <time>{updated_at}</time></p>
      </div>
      <div class="stats" id="stats">{stat_html}</div>
    </header>
    <div class="table-scroll">
      <table>
        <thead>
          <tr><th class="col-slot">场次</th><th class="col-role">角色</th>{date_header}</tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    <div class="note" id="help">
      <span>赤陶色为主播 · 圆点为未排班（周末/节假日/未填写）</span>
      <span class="tag">Wandor Style · Marvis Schedule</span>
    </div>
  </section>
</main>
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
