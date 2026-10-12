# 极氪排班卡 内置排班快照兜底（Schedule Snapshot Fallback）设计

- 日期：2026-10-12
- 状态：已批准
- 背景：DMG 分发给其他电脑后，App 打开显示"各直播间暂无排班数据"空态。根因：App 每次启动实时 `fetch` GitHub raw 的 schedule.json，异机无代理/网络受限时拉取失败；设计中的 `userDataDir/cache.json` 从未真正落盘，App 包内也未内置任何数据，失败路径直接返回 `{}` 渲染空态。

## 目标

1. 异机安装后**首次启动即有数据**（内置最近一份排班快照兜底）。
2. 联网可用时**自动刷新为最新**，并把成功数据落盘为本地缓存，后续离线优先读缓存。
3. 重打包 DMG 时快照自动跟随最新代码进包，不依赖人工记忆。

## 数据读取优先级（main.js `fetchSchedule()` 改造）

```
联网成功 → 展示最新数据，并写入 userDataDir/cache.json（修复缓存从未落盘的旧缺陷）
联网失败 → 读 userDataDir/cache.json（异机使用一段时间后缓存会更新）
缓存缺失 → 读内置 Resources/app/schedule.snapshot.json（打包时注入）
全部缺失 → 维持空态（正常打包下不会发生，快照必在包内）
```

- 内置快照文件：`极氪排班卡.app/Contents/Resources/app/schedule.snapshot.json`（与 main.js 同目录，`__dirname` 相对读取，开发态/打包态路径一致；当前为手工改造官方包、Resources/app 为裸目录，无 asar 读取问题）。
- 缓存路径保持 `app.getPath('userData')/cache.json` 不变，仅修复"网络成功时未写入"的缺陷。

## 构建流程（新增脚本）

- 新增 `sync/build_snapshot.sh`：
  1. `cp sync/schedule.json → app/极氪排班卡.app/Contents/Resources/app/schedule.snapshot.json`
  2. 校验文件非空且为合法 JSON，失败即退出并提示。
- 重打包 DMG 流程固定为：跑 `build_snapshot.sh` → 重建 staging → `hdiutil create -format UDZO` → 挂载校验 `schedule.snapshot.json` 存在且内容为最新。

## 界面提示（小项）

- 展示快照/缓存数据（非实时拉取）时，主界面角落显示"数据更新于 <时间>"，时间取 schedule.json 内自带时间或拉取落盘时间，避免同事误以为看到的是实时数据。

## 验证

1. 本机模拟断网（临时将 SCHEDULE_URL 指向不可达地址）跑通三级回退：内置快照可显示。
2. 恢复联网，确认拉取成功且 `userDataDir/cache.json` 真正落盘；再断网，确认读缓存。
3. 重打包 DMG 后挂载，确认 `schedule.snapshot.json` 在包内且为最新内容。

## 分发

- 生成新 DMG（含本兜底 + 既有扫码修复/语音开关），覆盖桌面 `极氪排班卡.dmg` 并备份旧包为 `bak_vN`，再分发给同事重装。

## 改动清单

| 文件 | 改动 |
|---|---|
| `app/极氪排班卡.app/Contents/Resources/app/main.js` | `fetchSchedule()` 三级回退 + 网络成功写 cache.json |
| `app/极氪排班卡.app/Contents/Resources/app/renderer/`（可选） | 数据更新时显示"数据更新于 xx" |
| `sync/build_snapshot.sh`（新增） | 快照注入脚本 |
| 打包流程 | staging 重建前先跑快照脚本，挂载校验含快照 |
