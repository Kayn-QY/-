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


def check_once(now=None):
    """检查当前时间点是否有需要触发的提醒（只提醒主播开播）。返回触发数量。"""
    cfg = load_config()
    schedule = load_schedule()
    state = load_state()
    remind_minutes = int(cfg.get("remind_minutes", 10))
    triggered = 0

    now = now or datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_schedule = schedule.get(today_str, {})

    # 清理非当天的已提醒状态（跨天自动切换）
    state = {k: v for k, v in state.items() if k.startswith(today_str)}

    for slot, info in today_schedule.items():
        slot_time = info.get("time", "")
        anchor = (info.get("anchor", "") or "").strip()
        if not slot_time or not anchor:
            continue
        try:
            start_time = slot_start_time(slot_time)
        except Exception:
            continue
        slot_start = datetime.combine(now.date(), start_time)
        remind_at = slot_start - timedelta(minutes=remind_minutes)

        # 只在提醒时间点前后 30 秒内触发
        if not (remind_at - timedelta(seconds=30) <= now <= remind_at + timedelta(seconds=30)):
            continue
        # 若已过时段开始时间，跳过
        if now > slot_start + timedelta(minutes=1):
            continue

        key = f"{today_str}|{slot}|{anchor}"
        if key in state:
            continue

        message = f"到点了：{anchor} {slot_time} 要开播了（提前{remind_minutes}分钟提醒）"
        notify("开播提醒", message)
        log(f"提醒触发: {message}")
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
