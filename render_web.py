#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页排班表渲染：模仿原 Excel 表格结构（日期横向、场次纵向、角色行）
设计风格：毛玻璃 3D 版（Frosted Glass + 3D Depth）—— 磨砂玻璃背景 + 圆角毛玻璃框 + 外投影/内高光立体感
参考视觉稿：design-direction-v2.html（整体背景磨砂朦胧、内容框 backdrop-filter blur + 半透明渐变 + 1px 半透明白描边、3D 外投影 + inset 高光）
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

MARQUEE_ITEMS = ["Bilibili", "GitHub", "Vercel", "Figma", "Notion", "Slack"]

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
table{width:100%;border-collapse:separate;border-spacing:6px;table-layout:fixed;min-width:1120px;font-size:12.5px}
thead th{
  background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.7);border-radius:12px;
  box-shadow:inset 0 1px 0 #fff;color:#1f2c44;font-weight:600;padding:10px 8px;white-space:nowrap;text-align:center;
}
.date-col{width:96px;min-width:96px;font-weight:600}
.date-col .wd{display:block;font-size:10px;color:var(--text-muted);font-weight:400;margin-top:2px}
.slot-col{width:84px;color:#334155;font-weight:500}
.role-col{width:80px;color:var(--text-muted);font-size:11.5px;font-weight:500}
td{
  border:1px solid rgba(255,255,255,.7);border-radius:12px;padding:0 6px;text-align:center;
  color:#334155;vertical-align:middle;background:rgba(255,255,255,.55);box-shadow:inset 0 1px 0 #fff;
  transition:background .15s,transform .15s;
}
tbody tr:hover td{background:rgba(255,255,255,.72)}
.slot-badge{
  display:inline-flex;align-items:center;justify-content:center;min-width:46px;padding:4px 8px;border-radius:999px;
  background:linear-gradient(135deg, #0a1b33, #1e3a5f);color:#fff;font-weight:600;font-size:11px;
  box-shadow:0 6px 14px rgba(10,27,51,.3);
}
.cell{width:96px;min-width:96px;height:46px;min-height:46px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cell.time{
  background:linear-gradient(135deg,#4f8df7,#2f6fe0);color:#fff;font-weight:600;border-color:transparent;
  box-shadow:0 8px 18px rgba(47,111,224,.32), inset 0 1px 0 rgba(255,255,255,.38);
}
.cell.car{
  background:linear-gradient(135deg,#f0a25e,#c9793d);color:#fff;font-weight:600;border-color:transparent;
  box-shadow:0 8px 18px rgba(201,121,61,.32), inset 0 1px 0 rgba(255,255,255,.38);
}
.cell.anchor{
  background:linear-gradient(135deg,#2ec4a6,#0f9c8b);color:#fff;font-weight:600;border-color:transparent;
  box-shadow:0 8px 18px rgba(15,156,139,.32), inset 0 1px 0 rgba(255,255,255,.38);
}
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


def latest_reminders(schedule):
    """取最近一天的排班作为提醒列表，返回 (日期, [(时间, 主播, 场次), ...])"""
    dates = sorted(schedule.keys())
    if not dates:
        return None, []
    d = dates[-1]
    items = []
    for slot in SLOT_ORDER:
        info = schedule[d].get(slot, {})
        t = info.get("time", "").strip()
        a = info.get("anchor", "").strip()
        if t and a:
            items.append((t, a, slot))
    return d, items


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

    # 跑马灯：内容复制一份实现无缝循环
    marquee_items_html = "".join(
        f"<span>{item}</span>" for item in MARQUEE_ITEMS
    )
    marquee_html = (
        f'<div class="marquee"><div class="marquee-track">{marquee_items_html}{marquee_items_html}</div></div>'
    )

    # 提醒卡片
    remind_date, remind_items = latest_reminders(schedule)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if remind_items:
        if remind_date == today_str:
            remind_title = "今日提醒"
            remind_sub = f'<span class="sub">按今天排班 · 到点自动提醒</span>'
        else:
            remind_title = "最近排班提醒"
            remind_sub = f'<span class="sub">{remind_date} · 到点自动提醒</span>'
        remind_list = "".join(
            f'<div class="remind-item"><span class="remind-time">{t}</span><span><span class="remind-slot">{slot}</span> · <span class="remind-name">{a}</span></span></div>'
            for t, a, slot in remind_items
        )
    else:
        remind_title = "今日提醒"
        remind_sub = '<span class="sub">暂无排班数据</span>'
        remind_list = '<div class="remind-empty">今日暂无排班，添加数据后自动生成提醒</div>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>【7X官方直播间】直播排班表</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS_TEMPLATE}</style>
</head>
<body>

<nav class="pill-nav">
  <a class="active" href="#schedule">排班表</a>
  <a href="#reminder">提醒</a>
  <a href="#help">说明</a>
  <a href="editor.html" target="_blank">在线编辑</a>
</nav>

<main class="content">
  <!-- Hero -->
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
    </section>

    <aside class="glass-card remind-card" id="reminder">
      <header class="card-head">
        <div>
          <h2>{remind_title}</h2>
          {remind_sub}
        </div>
      </header>
      {remind_list}
    </aside>
  </div>

  <div class="note" id="help">
    <span>深蓝为主播 · 赤陶为车型 · 圆点为未排班（周末/节假日/未填写）</span>
    <span class="tag">Frosted 3D Style · Marvis Schedule</span>
  </div>
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
