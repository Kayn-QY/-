#!/usr/bin/env python3
"""极氪排班卡同步看门狗

双校验判定同步链路是否异常:
  ① 心跳超时   : temp/heartbeat.json 的 last_success 距今超过 HEARTBEAT_TIMEOUT
  ② 远端一致性 : GitHub raw 上的 schedule.json 与本地内容 sha256 不一致
                 (首次不一致会等待 CDN_RECHECK_WAIT 秒复核, 排除 CDN 缓存滞后导致的误判)

异常处置:
  补跑一次 sync_wecom.py(单实例锁由同步脚本自身持有, 看门狗不抢锁以免与子进程互斥)
    - 补跑成功: 静默恢复, 清除告警标记
    - 返回码 3: 主任务正在跑(撞车), 本轮跳过, 下轮复查
    - 补跑失败: macOS 系统通知 + 写告警日志(同类告警 ALERT_COOLDOWN 内不重复打扰)

仅依赖标准库, 由系统 /usr/bin/python3 运行, 保证 venv 损坏时告警能力仍在。
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
HEARTBEAT_PATH = os.path.join(BASE_DIR, "temp", "heartbeat.json")
WATCH_LOG = os.path.join(BASE_DIR, "temp", "watch.log")
ALERT_STATE_PATH = os.path.join(BASE_DIR, "temp", "watch_alert_state.json")
VENV_PY = os.path.join(BASE_DIR, "venv", "bin", "python")
SYNC_SCRIPT = os.path.join(BASE_DIR, "sync_wecom.py")
RAW_URL = "https://raw.githubusercontent.com/Kayn-QY/-/main/schedule.json"

HEARTBEAT_TIMEOUT = 30 * 60   # 心跳超时阈值(秒)
ALERT_COOLDOWN = 2 * 3600     # 同类告警冷却(秒)
CDN_RECHECK_WAIT = 60         # 远端不一致时的二次确认等待(秒)
FETCH_TIMEOUT = 25            # 远端拉取超时(秒)
SYNC_TIMEOUT = 600            # 补跑超时(秒)
SKIP_ALERT_THRESHOLD = 3      # 连续撞车跳过多少次后判定主任务疑似卡死并告警


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(WATCH_LOG), exist_ok=True)
        with open(WATCH_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def rotate_log(path, max_bytes=1024 * 1024, keep_lines=500):
    """日志超过 1MB 时只保留尾部, 避免无限增长"""
    try:
        if os.path.getsize(path) > max_bytes:
            with open(path) as f:
                tail = f.readlines()[-keep_lines:]
            with open(path, "w") as f:
                f.writelines(tail)
    except Exception:
        pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch_remote_bytes():
    req = urllib.request.Request(
        RAW_URL, headers={"Cache-Control": "no-cache",
                          "User-Agent": "zeekr-sync-watch/1.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        return r.read()


def check_heartbeat():
    """返回 (是否异常, 描述)"""
    if not os.path.exists(HEARTBEAT_PATH):
        return True, "心跳文件不存在(同步从未记录成功)"
    try:
        with open(HEARTBEAT_PATH) as f:
            hb = json.load(f)
    except Exception as e:
        return True, f"心跳文件损坏: {e}"
    last = hb.get("last_success")
    if not last:
        return True, f"从未成功同步(streak={hb.get('failure_streak')}, detail={hb.get('detail')})"
    try:
        dt = datetime.fromisoformat(last)
    except Exception:
        return True, f"心跳时间格式异常: {last}"
    age = int((datetime.now() - dt).total_seconds())
    if age > HEARTBEAT_TIMEOUT:
        return True, f"心跳超时: 最后成功于 {last} ({age // 60} 分钟前)"
    return False, f"心跳正常(最后成功 {last})"


def check_consistency():
    """返回 (是否异常, 描述)"""
    if not os.path.exists(SCHEDULE_PATH):
        return True, "本地 schedule.json 不存在"
    with open(SCHEDULE_PATH, "rb") as f:
        local = sha256(f.read())
    try:
        remote = sha256(fetch_remote_bytes())
    except Exception as e:
        return True, f"远端拉取失败: {type(e).__name__}: {e}"
    if local == remote:
        return False, "远端与本地一致"
    log(f"首次比对不一致(local={local[:8]} remote={remote[:8]}), "
        f"等待 {CDN_RECHECK_WAIT}s 排除 CDN 缓存后复核")
    time.sleep(CDN_RECHECK_WAIT)
    try:
        remote2 = sha256(fetch_remote_bytes())
    except Exception as e:
        return True, f"复核时远端拉取失败: {type(e).__name__}: {e}"
    if local == remote2:
        return False, "远端与本地一致(首次为 CDN 缓存滞后)"
    return True, f"远端数据陈旧(local={local[:8]} remote={remote2[:8]})"


def run_sync():
    """补跑一次同步; 退出码 3 表示主任务正在跑(撞车跳过), 交由调用方区分"""
    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    try:
        r = subprocess.run([py, SYNC_SCRIPT, "--headless"], cwd=BASE_DIR,
                           capture_output=True, text=True, timeout=SYNC_TIMEOUT)
        out = (r.stdout or "").strip().splitlines()[-4:]
        err = (r.stderr or "").strip().splitlines()[-3:]
        return r.returncode, " / ".join(out + err)
    except subprocess.TimeoutExpired:
        return 124, f"补跑超时(>{SYNC_TIMEOUT}s)"
    except Exception as e:
        return 1, f"补跑异常: {type(e).__name__}: {e}"


def load_alert_state():
    try:
        with open(ALERT_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_alert_state(state):
    try:
        tmp = ALERT_STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ALERT_STATE_PATH)
    except Exception as e:
        log(f"[WARN] 告警状态写入失败: {e}")


def notify(title, message):
    """macOS 系统通知"""
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{esc(message)}" with title "{esc(title)}" sound name "Basso"'],
            capture_output=True, text=True, timeout=15)
        return True
    except Exception as e:
        log(f"[WARN] 系统通知发送失败: {e}")
        return False


def maybe_alert(state, reason, label="自动补跑仍失败"):
    """按冷却策略发送告警并落盘状态"""
    now = time.time()
    last_alert = float(state.get("last_alert") or 0)
    if now - last_alert >= ALERT_COOLDOWN:
        if notify("极氪排班卡同步异常", f"{label}: {reason[:80]}"):
            log("已发送 macOS 系统通知")
        state["last_alert"] = now
    else:
        remain = int((ALERT_COOLDOWN - (now - last_alert)) / 60)
        log(f"告警冷却中(剩余 {remain} 分钟), 仅记录日志")
    state["alerting"] = True
    state["last_fail"] = datetime.now().isoformat(timespec="seconds")
    state["last_reason"] = reason[:300]
    save_alert_state(state)


def main():
    rotate_log(WATCH_LOG)
    problems = []

    hb_bad, hb_msg = check_heartbeat()
    log(f"心跳校验: {hb_msg}")
    if hb_bad:
        problems.append(hb_msg)

    con_bad, con_msg = check_consistency()
    log(f"一致性校验: {con_msg}")
    if con_bad:
        problems.append(con_msg)

    state = load_alert_state()
    if not problems:
        changed = False
        if state.get("alerting"):
            log("状态已恢复正常, 清除告警标记")
            state["alerting"] = False
            changed = True
        if state.get("skip_streak"):
            state["skip_streak"] = 0
            changed = True
        if changed:
            save_alert_state(state)
        log("结论: 同步链路正常")
        return 0

    reason = "; ".join(problems)
    log(f"结论: 同步链路异常 -> {reason}")

    log("开始补跑同步...")
    code, tail = run_sync()
    tail_flat = tail.replace("\n", " / ")

    if code == 3:
        # 主任务持有锁: 通常它正在正常运行, 但若连续多轮都拿不到锁,
        # 说明主任务卡死且未释放锁, 此时必须告警而非无限等待
        streak = int(state.get("skip_streak") or 0) + 1
        state["skip_streak"] = streak
        save_alert_state(state)
        if streak >= SKIP_ALERT_THRESHOLD:
            log(f"连续 {streak} 轮撞车跳过且心跳仍异常, 判定主任务疑似卡死")
            maybe_alert(state, reason, label=f"主任务疑似卡死(连续 {streak} 轮未释放锁)")
            return 1
        log(f"主任务正在运行(撞车跳过 {streak}/{SKIP_ALERT_THRESHOLD}), 下轮复查")
        return 0

    if code == 0:
        log(f"补跑成功, 已自动恢复 | {tail_flat}")
        state["alerting"] = False
        state["skip_streak"] = 0
        save_alert_state(state)
        return 0

    log(f"补跑失败(exit={code}) | {tail_flat}")
    maybe_alert(state, reason)
    return 1


if __name__ == "__main__":
    sys.exit(main())
