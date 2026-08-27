#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直播开播提醒引擎：后台常驻，读取 schedule.json（场次结构），主播开播前 N 分钟触发 macOS 通知

用法：
  python3 reminder.py          # 前台运行
  python3 reminder.py --once   # 只检查一次（供 launchd 定时调用）
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
LOG_PATH = os.path.join(BASE_DIR, "temp", "logs", "reminder.log")
STATE_PATH = os.path.join(BASE_DIR, "temp", "reminder_state.json")


def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    print(msg)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schedule():
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def notify(title, message):
    """调用 osascript 发送 macOS 通知"""
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)


def slot_start_time(slot_time):
    """'10:00-12:00' → datetime.time 开始时间"""
    start_s = slot_time.split("-")[0].strip()
    return datetime.strptime(start_s, "%H:%M").time()


def slot_end_time(slot_time):
    """'10:00-12:00' → datetime.time 结束时间"""
    end_s = slot_time.split("-")[1].strip()
    return datetime.strptime(end_s, "%H:%M").time()


def normalize_schedule(schedule, cfg):
    """兼容旧结构（顶层为日期键）→ 迁移为 {room: {date: ...}} 多直播间结构"""
    if not schedule or not isinstance(schedule, dict):
        return {}
    rooms = cfg.get("rooms") or ["7X", "8X", "9X", "猎装", "售后"]
    # 顶层 key 与直播间名有交集 → 已是多直播间结构
    if any(r in schedule for r in rooms):
        return schedule
    # 顶层为日期键（旧结构）→ 归入 7X
    return {"7X": schedule}


def check_once(now=None):
    """检查当前时间点是否有需要触发的提醒（开播/换播/下播，提前 10/5 分钟各一次）。返回触发数量。"""
    cfg = load_config()
    schedule = normalize_schedule(load_schedule(), cfg)
    state = load_state()
    rooms = cfg.get("rooms") or list(schedule.keys()) or ["7X"]
    SLOT_ORDER = ["第1场", "第2场", "第3场", "第4场", "第5场", "第6场"]
    LEADS = [10, 5]
    triggered = 0

    now = now or datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # 清理非当天的已提醒状态（跨天自动切换）
    state = {k: v for k, v in state.items() if k.startswith(today_str)}

    for room in rooms:
        room_data = schedule.get(room, {})
        if not isinstance(room_data, dict):
            continue
        day = room_data.get(today_str, {})
        if not isinstance(day, dict):
            continue
        # 收集当天有序场次（含开始/结束/主播）
        slots = []
        for slot in SLOT_ORDER:
            info = day.get(slot) or {}
            if not isinstance(info, dict):
                continue
            slot_time = info.get("time", "")
            if not slot_time:
                continue
            try:
                s_t = slot_start_time(slot_time)
                e_t = slot_end_time(slot_time)
            except Exception:
                continue
            slots.append({
                "slot": slot,
                "start": datetime.combine(now.date(), s_t),
                "end": datetime.combine(now.date(), e_t),
                "anchor": (info.get("anchor", "") or "").strip(),
                "time": slot_time,
            })
        # 生成事件：开播 + 切换（换播/下播）
        events = []
        for i, s in enumerate(slots):
            prev = slots[i - 1] if i > 0 else None
            if s["anchor"]:
                # 前一场有主播且无缝衔接 → 场上切换由「换播」覆盖，不再单独发开播
                if not (prev and prev["anchor"] and prev["end"] == s["start"]):
                    events.append({"kind": "开播", "slot": s["slot"], "time": s["time"], "anchor": s["anchor"], "at": s["start"]})
            nx = slots[i + 1] if i + 1 < len(slots) else None
            if s["anchor"]:
                kind = "换播" if (nx and nx["anchor"]) else "下播"
                events.append({
                    "kind": kind,
                    "slot": nx["slot"] if nx else s["slot"],
                    "time": nx["time"] if nx else "",
                    "anchor": nx["anchor"] if (nx and nx["anchor"]) else "无场次",
                    "at": s["end"],
                })
        for lead in LEADS:
            for ev in events:
                remind_at = ev["at"] - timedelta(minutes=lead)
                # 只在提醒时间点前后 30 秒内触发
                if not (remind_at - timedelta(seconds=30) <= now <= remind_at + timedelta(seconds=30)):
                    continue
                # 若已过事件时刻，跳过
                if now > ev["at"] + timedelta(minutes=1):
                    continue
                key = f"{today_str}|{room}|{lead}|{ev['kind']}|{ev['slot']}|{ev['at'].strftime('%H:%M')}"
                if key in state:
                    continue
                message = f"{ev['slot']} {ev['time']} {ev['anchor']}，{lead}分钟后{ev['kind']}"
                notify(f"{ev['kind']}提醒 · {room}", message)
                log(f"提醒触发: [{room}] {message}")
                state[key] = now.strftime("%Y-%m-%d %H:%M:%S")
                triggered += 1

    save_state(state)
    return triggered


def run_forever():
    log("提醒引擎启动（场次结构/主播提醒），等待开播触发...")
    while True:
        try:
            check_once()
        except Exception as e:
            log(f"检查异常: {e}")
        time.sleep(30)


if __name__ == "__main__":
    if "--once" in sys.argv:
        n = check_once()
        print(f"本轮触发 {n} 条提醒")
    else:
        run_forever()
