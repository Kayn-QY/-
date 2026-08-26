# 自动同步联动网页部署设计（2026-08-26）

## 问题

- 企业微信排班文档 → 桌面卡片 App 能自动同步；网页（GitHub Pages 静态站 index.html）不更新。
- 根因：两条链路断裂。`sync_wecom.py`（launchd 每 10 分钟）只 `git add schedule.json` 并推送；
  网页 `index.html` 是 `render_web.py` 静态预渲染文件，由 `deploy.sh` 手动渲染 + 推送。
  桌面卡片直接拉取远端 `schedule.json`，所以数据一推送卡片即更新；网页停留在旧版 08-26 15:04。

## 目标

- 企业微信排班一有变化，10 分钟内 `schedule.json` 与网页 `index.html` 同时更新，与桌面卡片一致。

## 方案（用户选定：方案 1——同步脚本内闭环）

- 改动仅 `sync_wecom.py` 一处。
- 数据流：
  1. 提取微文档 → 解析 → diff
  2. 有变化 → 写入 `schedule.json`
  3. `subprocess` 运行 `python3 render_web.py`（cwd=BASE_DIR）生成 `output/schedule.html`
  4. 渲染成功 → 复制 `output/schedule.html` → `index.html`
  5. 三个文件一起 `git add` → `commit` → `push`（原子一致）
  6. 渲染失败 → 打印告警，仍只推 `schedule.json`（数据优先）

## 失败兜底

- 渲染失败：不阻断数据推送，日志记录，下次有变化自动重试。
- push 被远端拒绝（在线编辑页 ghPut 冲突）：不自动 reset，打印提示保留本地数据，交人工处理。

## 其它说明

- 当前工作区 `render_web.py` 有未提交改动（网页侧「换播」文案构建逻辑），本次联动部署会一并上线，兑现此前待办。

## 验证

1. `sync_wecom.py --no-push`：真实提取 + 渲染，不推送，确认 `index.html` 已更新。
2. 检查 `index.html` 生成时间戳晚于 `schedule.json`。
3. 正式同步推送后，抓取远端 raw 确认数据与网页同版本。
