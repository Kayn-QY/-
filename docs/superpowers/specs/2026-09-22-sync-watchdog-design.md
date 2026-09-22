# 同步可靠性加固（看门狗兜底）设计

日期：2026-09-22
状态：已实施

## 背景

排班数据同步链路存在两类静默失败，都会导致 App 显示旧数据而不被察觉：

1. **抓取层**：Playwright 等待工作表超时（历史 18 次）、页面加载超时（4 次）、核心 Sheet 未加载（4 次）。
2. **推送层**：`git push` 报 HTTP2 framing layer 失败（2 次），疑似亿格云安全终端干扰 HTTP/2 大包。

脚本对失败的处理是打印 `[FAIL]` 后退出，既无重试也不告警，远端因此停更，且没有任何人知道。

## 目标

让同步链路的失败**可自愈、可感知**：

- 失败能被独立于主任务的进程发现；
- 发现后先自动补跑一次；
- 补跑仍失败才通知人，且不重复打扰。

非目标：不做云端同步、不改数据源、不动已加固的 push 逻辑、不做多机协同。Mac 关机期間不同步仍为已知边界。

## 架构

```
主任务 com.marvis.zeekr.sync（每 10 分钟）
   ├─ 全链路成功 → 写心跳 temp/heartbeat.json
   └─ 持有单实例锁 temp/sync.lock

看门狗 com.marvis.zeekr.sync-watch（每 30 分钟）
   ├─ 校验① 心跳：last_success 距今 > 30 分钟？
   ├─ 校验② 一致性：远端 raw schedule.json 的 sha256 == 本地？
   ├─ 一切正常 → 静默退出（不打扰）
   └─ 判定异常 → 补跑一次 sync_wecom.py
         ├─ 成功     → 写日志恢复，清除告警标记
         ├─ 退出码 3 → 主任务正在跑，本轮跳过，下轮复查
         └─ 失败     → macOS 系统通知 + 告警日志
```

## 判定方式为什么是双校验

最初设想是"远端数据超过阈值未更新即异常"，但**该判据会误报**：排班长时间无变化时，同步成功也不会产生新提交，远端时间戳自然陈旧。

改为两条互补判据，任一条异常即判定故障：

| 判据 | 覆盖的故障 | 不误报的原因 |
|---|---|---|
| 心跳超时 | 主任务被卡死、被杀、脚本崩溃 | 脚本只要完整跑完一轮就刷新心跳，与数据有无变化无关 |
| 远端一致性 | 抓取成功但 push 静默失败 | 无变化时本地与远端字节一致，hash 天然相等 |

两条判据分别覆盖"没在跑"与"跑了但没生效"，缺一不可。

## 关键实现细节

### 单实例锁归属

锁由 `sync_wecom.py` 自身持有（`fcntl.flock` 非阻塞）。看门狗**不抢锁**，而是通过子进程退出码区分：

- 退出码 3 = 撞车跳过，既非成功也非失败，不写心跳，看门狗视为"下轮复查"。

早期版本让看门狗先抢锁再启动子进程，结果子进程因锁被父进程占用而永远跳过并被误判为"补跑成功"，此处为实测发现并修正的缺陷。

### 卡死兜底（两层）

只靠"下轮复查"会留一个死锁：若主任务卡死并一直持有锁，看门狗会永远撞车跳过、永不告警。因此补两层防御：

1. **主脚本自解**：`sync_wecom.py` 用 `signal.alarm(RUN_TIMEOUT = 900)` 限制单轮时长，超时抛错退出并释放锁。
2. **看门狗判定**：连续 `SKIP_ALERT_THRESHOLD = 3` 轮（默认约 90 分钟）撞车跳过、且心跳仍异常，判定主任务卡死并告警，不再无限等待。

### CDN 缓存误判

GitHub raw 存在约 5 分钟缓存。刚 push 完拉取可能拿到旧内容，造成"远端陈旧"误判。处理：首次比对不一致时等待 60 秒复核，仍不一致才判定异常。

### 告警节流

同类告警 2 小时冷却，冷却期内只写日志不弹通知，避免故障持续时每 30 分钟打扰一次。

### 关机行为

Mac 关机期间看门狗不运行，恢复开机后 `RunAtLoad` 立即跑一次。此时心跳必然超时，看门狗直接补跑；补跑成功即静默恢复，不触发告警。

### 运行环境解耦

看门狗仅依赖标准库，由 `/usr/bin/python3` 运行；补跑时才调用 `venv/bin/python`。这样即使 venv 损坏（playwright 环境异常），告警能力仍然保留。

## 参数

| 参数 | 值 | 位置 |
|---|---|---|
| 看门狗检查间隔 | 1800 秒 | `com.marvis.zeekr.sync-watch.plist` StartInterval |
| 心跳超时判定 | 1800 秒 | `watch_sync.py` HEARTBEAT_TIMEOUT |
| 告警冷却 | 7200 秒 | `watch_sync.py` ALERT_COOLDOWN |
| CDN 复核等待 | 60 秒 | `watch_sync.py` CDN_RECHECK_WAIT |
| 补跑超时 | 600 秒 | `watch_sync.py` SYNC_TIMEOUT |
| 单轮同步超时 | 900 秒 | `sync_wecom.py` RUN_TIMEOUT |
| 撞车告警阈值 | 连续 3 轮 | `watch_sync.py` SKIP_ALERT_THRESHOLD |

## 相关文件

| 文件 | 作用 |
|---|---|
| `sync/sync_wecom.py` | 新增 `acquire_single_lock()`、`write_heartbeat()`，入口包裹成败记录 |
| `sync/watch_sync.py` | 看门狗主体（双校验 + 补跑 + 告警） |
| `~/Library/LaunchAgents/com.marvis.zeekr.sync-watch.plist` | 看门狗定时任务 |
| `sync/temp/heartbeat.json` | 心跳（last_success / failure_streak） |
| `sync/temp/watch.log` | 看门狗日志（超 1MB 自动保留尾部 500 行） |
| `sync/temp/watch_alert_state.json` | 告警冷却状态 |

## 验证记录

| 场景 | 构造方式 | 结果 |
|---|---|---|
| 心跳缺失 | 删除心跳文件 | 判定异常 → 补跑成功 → 心跳写入 ✓ |
| 正常态 | 心跳与远端均正常 | 2 秒内静默退出，不补跑 ✓ |
| 撞车 | 持有锁时运行同步 | 退出码 3，不写心跳；看门狗识别并跳过 ✓ |
| 主任务卡死 | 桩函数令补跑持续返回撞车 | 前 2 轮静默跳过，第 3 轮判定卡死并告警；恢复后计数归零 ✓ |
| 主任务落盘 | launchd 真机触发一轮 | 退出码 0，心跳刷新至 09:34:28 ✓ |
| 补跑失败 | 桩函数返回失败 | 弹系统通知，退出码 1 ✓ |
| 告警冷却 | 连续两次失败 | 第二次仅记日志，不重复弹窗 ✓ |
| 端到端 | launchd 加载后 RunAtLoad | 静默通过，任务状态 0 ✓ |

## 手动运维

```bash
cd "/Users/xiaozhongbo/Library/Application Support/zeekr-schedule-card/sync"

# 查看心跳
cat temp/heartbeat.json

# 查看看门狗近期判断
tail -20 temp/watch.log

# 手动跑一次看门狗（不会销毁状态）
/usr/bin/python3 watch_sync.py

# 暂停/恢复看门狗
launchctl unload ~/Library/LaunchAgents/com.marvis.zeekr.sync-watch.plist
launchctl load   ~/Library/LaunchAgents/com.marvis.zeekr.sync-watch.plist
```

告警状态在 `temp/watch_alert_state.json`；如需立即重发告警，将其内容重置为 `{}` 即可解除冷却。
