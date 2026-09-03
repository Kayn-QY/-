#!/usr/bin/env python3
"""企业微信微文档 → 极氪排班站 schedule.json 自动同步

用法:
  python3 sync_wecom.py --cookie <cookie_file> [--no-push] [--rooms 7X,8X,9X,猎装]

流程:
  1. Playwright 打开微文档链接, 提取 9 个 Sheet 单元格数据
  2. 解析每个 Sheet → {直播间: {日期: {场次: {time,car,anchor}}}}
  3. 与现有 schedule.json diff, 无变化直接退出
  4. 有变化 → 写新 schedule.json → git commit & push
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
COOKIE_DEFAULT = os.path.join(BASE_DIR, "temp", "wecom_cookie.txt")
URL = "https://doc.weixin.qq.com/sheet/e3_AcQAxwZyAHkCN70BsWMPOStuFgj8i?scode=AHYAvAeeAAYSYD01NRAaYA_QYzAP8&tab=BB08J2"

# sheet id -> 直播间名（与表格 sheet 标题一致, 用于展示）
SHEET_NAMES = {
    "BB08J2": "9X官方直播间", "bu5vfc": "极氪8X官方直播间", "068ykn": "极氪7X官方直播间",
    "exsnhu": "猎装官方直播间", "jerhr6": "增量项目-极氪情报官", "16goet": "极氪尊享服务",
    "q4t6ok": "极氪x", "cvg6j4": "TK-澳洲", "rayvs6": "极氪情报局",
}
SHEET_ROOM = {
    "9X官方直播间": "9X", "极氪8X官方直播间": "8X", "极氪7X官方直播间": "7X",
    "猎装官方直播间": "猎装", "增量项目-极氪情报官": "情报官",
    "极氪尊享服务": "售后", "极氪x": "极氪x", "TK-澳洲": "TK", "极氪情报局": "情报局",
}
MONTH_DAY_RE = re.compile(r"^(\d{1,2})月(\d{1,2})日$")
FULL_DATE_RE = re.compile(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$")
SESSION_RE = re.compile(r"^第\s*([一二三四五六七八九十\d]+)\s*场$")
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
REST_WORDS = ("休息", "休", "不播", "停播", "放假", "无排班", "OFF", "off")
YEAR = 2026

# 标准场次时间槽: (开始小时, 场次序号)。第N场 = [开始小时, 开始小时+2)
SLOTS = [(10, 1), (12, 2), (14, 3), (16, 4), (18, 5), (20, 6)]


def slot_of_time(text):
    """按开播开始时间归位到标准场次键(如 '第3场').

    例如 14:30->第3场, 13:00->第2场; 不在任何槽内就就近归位;
    无法解析时间时返回 None(由调用方兜底保留原标签).
    """
    m = re.match(r"\s*(\d{1,2}):(\d{2})", text or "")
    if not m:
        return None
    m_min = int(m.group(1)) * 60 + int(m.group(2))
    for start_h, idx in SLOTS:
        if start_h * 60 <= m_min < (start_h + 2) * 60:
            return f"第{idx}场"
    best = min(SLOTS, key=lambda x: abs(m_min - x[0] * 60))
    return f"第{best[1]}场"

JS_EXTRACT = """() => {
  const sheets = window.SpreadsheetApp.workbook.worksheetManager.sheetList;
  const out = {};
  for (let si = 0; si < sheets.length; si++) {
    const s = sheets[si];
    if (!s || !s.cellDataGrid) continue;
    const blocks = s.cellDataGrid._kK || [];
    const cells = [];
    for (let b1 = 0; b1 < blocks.length; b1++) {
      const subs = blocks[b1];
      for (let b2 = 0; b2 < (subs ? subs.length : 0); b2++) {
        const sub = subs ? subs[b2] : null;
        if (!sub || !sub._Ao) continue;
        for (let r = 0; r < sub._Ao.length; r++) {
          const rowCells = sub._Ao[r];
          if (!rowCells) continue;
          for (let c = 0; c < rowCells.length; c++) {
            const cell = rowCells[c];
            if (!cell) continue;
            let txt = null;
            try { if (cell.formattedValue && cell.formattedValue.value !== undefined) txt = cell.formattedValue.value; } catch(e) {}
            if (txt === null || txt === undefined || txt === '') continue;
            cells.push({row: b1*64+r, col: b2*32+c, text: String(txt)});
          }
        }
      }
    }
    out[si] = {name: ((s.name || (s.sheetProperties && s.sheetProperties.codeName)) || ''), cells: cells};
  }
  return out;
}
"""


def norm_session_name(label):
    m = SESSION_RE.match(label.strip())
    if not m:
        return None
    s = m.group(1)
    if s.isdigit():
        return f"第{s}场"
    total = 0
    for ch in s:
        total = total * 10 + CN_NUM.get(ch, 0)
    return f"第{total}场" if total else None


def parse_date(text):
    text = text.strip()
    m = FULL_DATE_RE.match(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = MONTH_DAY_RE.match(text)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        return f"{YEAR:04d}-{mo:02d}-{d:02d}"
    return None


def is_rest(text):
    if text is None:
        return True
    t = text.strip()
    if not t:
        return True
    return any(t == w or t.startswith(w) for w in REST_WORDS)


def build_grid(cells):
    return {(c["row"], c["col"]): c["text"] for c in cells}


def parse_sheet(sheet):
    """sheet: {name, cells} -> ({room: {date: {session: {...}}}}, err)"""
    cells = sheet.get("cells") or []
    if not cells:
        return None, "空表"
    grid = build_grid(cells)
    rows = sorted({k[0] for k in grid})
    date_row = None
    for r in rows:
        if grid.get((r, 1), "").strip() == "日期" and parse_date(grid.get((r, 2), "")):
            date_row = r
            break
    if date_row is None:
        return None, "无日期行"
    date_cols = {}
    for c in sorted({k[1] for k in grid if k[0] == date_row}):
        d = parse_date(grid.get((date_row, c), ""))
        if d:
            date_cols[c] = d
    if not date_cols:
        return None, "日期列为空"
    sessions = []
    for r in sorted(rows):
        if r <= date_row:
            continue
        sn = norm_session_name(grid.get((r, 0), "").strip())
        if sn:
            sessions.append((sn, r))
    if not sessions:
        return None, "无场次块"
    result = {}
    for idx, (sn, sr) in enumerate(sessions):
        er = sessions[idx + 1][1] if idx + 1 < len(sessions) else max(rows) + 1
        time_row = car_row = anchor_row = None
        for r in range(sr, min(sr + 8, er)):
            c1 = grid.get((r, 1), "").strip()
            if c1 in ("直播时间", "AUS Time", "Time"):
                time_row = r
            elif c1 in ("直播车型", "Model"):
                car_row = r
            elif c1 in ("主播", "Host"):
                anchor_row = r
        for c, d in date_cols.items():
            t = grid.get((time_row, c), "") if time_row is not None else ""
            if is_rest(t):
                continue
            car = grid.get((car_row, c), "").strip() if car_row is not None else ""
            anchor = grid.get((anchor_row, c), "").strip() if anchor_row is not None else ""
            if not anchor and not car:
                continue
            entry = {"time": t.strip()}
            if car:
                entry["car"] = car
            if anchor:
                entry["anchor"] = anchor
            # 归位: 按开播开始时间映射到标准场次键(原表格标签仅作解析顺序参考)
            slot_key = slot_of_time(entry["time"]) or sn
            result.setdefault(d, {})[slot_key] = entry
    if not result:
        return None, "无有效场次数据"
    return result, None


def load_cookies(path):
    cookie_str = open(path).read().strip()
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies.append({"name": k.strip(), "value": v.strip(), "domain": ".doc.weixin.qq.com", "path": "/"})
    return cookies


TAB_NAMES = ["9X官方直播间", "极氪8X官方直播间", "极氪7X官方直播间", "猎装官方直播间",
             "增量项目-极氪情报官", "极氪尊享服务", "极氪x", "TK-澳洲", "极氪情报局"]


def extract_all(cookie_path, headless=False):
    """Playwright 提取全部 sheet 单元格, 返回 {sheet_index: {name, cells}}

    策略: 逐个点击 Sheet tab 触发懒加载, Ctrl+End 触发滚动加载剩余块,
    初始 + 滚动后两次提取合并去重。
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=headless)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900})
        ctx.add_cookies(load_cookies(cookie_path))
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        # 等待 sheetList 对象出现
        ok = False
        for i in range(60):
            try:
                ok = page.evaluate("() => { const s = window.SpreadsheetApp && window.SpreadsheetApp.workbook && window.SpreadsheetApp.workbook.worksheetManager; return !!(s && s.sheetList && s.sheetList.length >= 8); }")
                if ok:
                    break
            except Exception:
                pass
            time.sleep(2)
        if not ok:
            browser.close()
            raise RuntimeError("等待工作表对象超时")
        # 先切走首个 tab(默认激活), 否则回头点击它时无法触发数据加载
        try:
            page.locator(".tab-bar-item-title:has-text('极氪8X官方直播间')").first.click(timeout=5000)
        except Exception:
            pass
        time.sleep(2)
        # 逐个点击 Sheet tab 触发数据加载
        # 修复: click 失败时记录并整轮重试核心 tab, 防止静默吞错导致空表
        # 末尾空表 tab(极氪x/TK-澳洲/极氪情报局)可能不在 DOM 中, 点击失败不重试
        CORE_TABS = TAB_NAMES[:6]
        for attempt in range(2):
            missing = []
            for nm in TAB_NAMES:
                clicked = False
                for _ in range(2):
                    try:
                        page.locator(f".tab-bar-item-title:has-text('{nm}')").first.click(timeout=8000)
                        clicked = True
                        break
                    except Exception:
                        time.sleep(1)
                if not clicked and nm in CORE_TABS:
                    missing.append(nm)
                    continue
                for _ in range(25):
                    loaded = False
                    try:
                        loaded = page.evaluate(f"""() => {{
                          const gn = (sh) => (sh && (sh.name || (sh.sheetProperties && sh.sheetProperties.codeName))) || '';
                          const s = window.SpreadsheetApp.workbook.worksheetManager.sheetList;
                          for (const sh of s) {{ if (gn(sh) === '{nm}' && sh.cellDataGrid && (sh.cellDataGrid._kK || []).length > 0) return true; }}
                          return false;
                        }}""")
                    except Exception:
                        pass
                    if loaded:
                        break
                    time.sleep(2)
            if not missing:
                break
            if attempt == 0:
                time.sleep(3)
        if missing:
            print(f"[WARN] 以下核心 Sheet 未能加载数据: {missing}", file=sys.stderr)
        # Ctrl+End 触发滚动加载剩余块
        first = None
        second = None
        try:
            page.keyboard.press("Control+End")
            time.sleep(6)
            first = page.evaluate(JS_EXTRACT)
        except Exception:
            pass
        if first is not None:
            try:
                page.keyboard.press("Control+End")
                time.sleep(4)
                second = page.evaluate(JS_EXTRACT)
            except Exception:
                pass
        try:
            browser.close()
        except Exception:
            pass
        if first is None:
            raise RuntimeError("页面在滚动提取前已关闭, 提取失败")
    # 合并两次结果（按单元格坐标去重）
    merged = {}
    for src in (first, second):
        if src is None:
            continue
        for si, sheet in src.items():
            m = merged.setdefault(si, {"name": sheet["name"], "cells": {}})
            if not m["name"]:
                m["name"] = sheet["name"]
            for c in sheet["cells"]:
                m["cells"][(c["row"], c["col"])] = c["text"]
    # 按真实名字映射（不再按 sheetList 索引用 TAB_NAMES 猜名回填）
    # 名字来源: JS_EXTRACT 已优先从 sheetProperties.codeName 取真名(逐个点击激活后补齐)
    unnamed = [si for si, v in merged.items() if not v["name"]]
    if unnamed:
        print(f"[WARN] 以下 Sheet 未取到名字(可能未成功激活): {unnamed}", file=sys.stderr)
    result = {si: {"name": v["name"], "cells": [{"row": r, "col": c, "text": t} for (r, c), t in v["cells"].items()]} for si, v in merged.items()}
    # 修复: 名字完整性校验——核心 6 个 Sheet 必须按真名识别, 否则中止,
    # 防止 tab 顺序变化时静默错位(8X/9X 数据对调)
    name_rooms = {v["name"] for v in result.values() if v["name"] in SHEET_ROOM}
    if len(name_rooms) < 6:
        raise RuntimeError(f"按名字映射异常: 仅识别到 {sorted(name_rooms)}, 无法可靠对齐直播间, 中止同步")
    # 修复: 提取质量校验——非空 Sheet 过少说明懒加载失败, 中止避免用陈旧数据覆盖
    nonempty = sum(1 for v in result.values() if v["name"] and v["cells"])
    if nonempty < 6:
        raise RuntimeError(f"提取质量异常: 仅 {nonempty} 个 Sheet 有数据, 疑似懒加载失败, 中止同步")
    return result


def git(cmd, cwd=BASE_DIR):
    return subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cookie", default=COOKIE_DEFAULT)
    ap.add_argument("--no-push", action="store_true", help="只更新本地 schedule.json, 不 git push")
    ap.add_argument("--rooms", default="", help="逗号分隔, 默认取 config.json rooms")
    ap.add_argument("--headless", action="store_true", help="无头模式(定时任务使用, 不弹浏览器窗口)")
    args = ap.parse_args()

    if not os.path.exists(args.cookie):
        print(f"[FAIL] Cookie 文件不存在: {args.cookie}")
        sys.exit(1)

    cfg = json.load(open(CONFIG_PATH)) if os.path.exists(CONFIG_PATH) else {}
    rooms = [r.strip() for r in args.rooms.split(",") if r.strip()] or cfg.get("rooms", ["7X", "8X", "9X", "猎装"])

    # 1. 提取
    print("[1/4] 提取微文档数据...")
    sheets = extract_all(args.cookie, headless=args.headless)
    print(f"      提取到 {len(sheets)} 个 Sheet")

    # 2. 解析
    print("[2/4] 解析排班数据...")
    parsed = {}
    skipped = []
    for si in sorted(sheets, key=int):
        sheet = sheets[si]
        room = SHEET_ROOM.get(sheet["name"], sheet["name"])
        res, err = parse_sheet(sheet)
        if res:
            parsed[room] = res
            if room == "售后":
                # 售后场次车型强制填「售后」
                for _dates in res.values():
                    for _entry in _dates.values():
                        _entry["car"] = "售后"
            print(f"      [OK] {sheet['name']} -> {room}: {len(res)} 天")
        else:
            skipped.append(f"{sheet['name']}({err})")
    if skipped:
        print("      跳过: " + "; ".join(skipped))

    # 3. diff
    print("[3/4] 对比 schedule.json ...")
    cur = {}
    if os.path.exists(SCHEDULE_PATH):
        cur = json.load(open(SCHEDULE_PATH))
    changed_rooms = []
    new_schedule = {}
    for room in rooms:
        if room not in parsed:
            print(f"      [{room}] 表格中无数据, 保留原值")
            if room in cur:
                new_schedule[room] = cur[room]
            continue
        if cur.get(room) != parsed[room]:
            changed_rooms.append(room)
            print(f"      [{room}] 有变化 ({len(cur.get(room, {}))} -> {len(parsed[room])} 天)")
        else:
            print(f"      [{room}] 无变化")
        new_schedule[room] = parsed[room]
    # 保留 config.rooms 之外的旧 key（如售后手动编辑数据）
    for k, v in cur.items():
        if k not in rooms and k not in new_schedule:
            new_schedule[k] = v

    if not changed_rooms:
        print("[4/4] 无需更新")
        return

    # 4. 写盘 + git
    print("[4/4] 写入 schedule.json 并提交...")
    with open(SCHEDULE_PATH, "w") as f:
        json.dump(new_schedule, f, ensure_ascii=False, indent=2)
    print(f"      更新直播间: {', '.join(changed_rooms)}")

    # 4.1 联动渲染网页 index.html（失败不阻断数据推送）
    render_ok = False
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "render_web.py")],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=180)
        sched_html = os.path.join(BASE_DIR, "output", "schedule.html")
        if r.returncode == 0 and os.path.exists(sched_html):
            shutil.copyfile(sched_html, os.path.join(BASE_DIR, "index.html"))
            render_ok = True
            print("      网页已重新渲染 index.html")
        else:
            print(f"[WARN] 网页渲染失败(returncode={r.returncode}), 本轮仅推送数据")
    except Exception as e:
        print(f"[WARN] 网页渲染异常: {e}, 本轮仅推送数据")

    if args.no_push:
        print("      (--no-push, 未提交 git)")
        return
    files = ["schedule.json"]
    if render_ok:
        files += ["index.html", "output/schedule.html"]
    r = git(["add"] + files)
    if r.returncode != 0:
        print(f"[FAIL] git add: {r.stderr}")
        sys.exit(1)
    r = git(["commit", "-m", f"sync: 微文档排班同步 {datetime.now().strftime('%m-%d %H:%M')} ({', '.join(changed_rooms)})"])
    if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
        print(f"[FAIL] git commit: {r.stderr}")
        sys.exit(1)
    r = git(["push", "origin", cfg.get("git", {}).get("branch", "main")])
    if r.returncode != 0:
        print(f"[FAIL] git push: {r.stderr}")
        sys.exit(1)
    print("      已推送 GitHub")


if __name__ == "__main__":
    main()
