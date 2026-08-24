# 极氪排班站桌面小组件设计（Übersicht 悬浮卡片）

日期：2026-08-24
状态：已确认，待实现

## 背景

用户是极氪直播团队排班负责人，现有排班站（schedule-reminder 项目）已部署到 GitHub Pages，排班数据在 `schedule.json`，支持多直播间（7X/8X/9X/猎装）动态排班。

用户需求：在 macOS 桌面上常驻一个"下一场倒计时"小组件，并在开播前 20 分钟 / 5 分钟各发一次系统通知。要求**可复制**——能快速部署到其他苹果电脑。小爱音箱播报为后续阶段（保留接口）。

## 技术选型

- **框架**：Übersicht（macOS 开源桌面小组件框架，HTML/CSS/JSX 渲染，brew 可装）
- **数据源**：GitHub 在线 `https://raw.githubusercontent.com/Kayn-QY/-/main/schedule.json`（已验证 HTTP 200），跨机器零数据迁移
- **语言**：widget 主体 JSX + Python 辅助脚本（解析排班、计算下一场、通知判定）

## 架构

```
schedule-widget.widget/
├── index.jsx          # Übersicht widget 入口（command 取数 + render 渲染）
└── schedule_helper.py # 辅助脚本：拉取 schedule.json、算下一场、判定通知时机
```

数据流：
1. widget 每 60 秒执行一次 command（refreshFrequency: 60000）
2. command 调用 schedule_helper.py：curl 拉 GitHub 在线 schedule.json → 解析 → 计算下一场（合并同时开播直播间）→ 判定是否命中通知窗口 → 输出 JSON
3. render 函数将 JSON 渲染为毛玻璃卡片
4. 命中通知窗口且未通知过 → osascript 发系统通知（提前 20 分钟 / 5 分钟）

## 卡片内容（下一场倒计时）

- 显示最近一场：直播间（多个同时开播则合并列出）、时间段、主播名、剩余分钟倒计时
- 开播后自动滚动到下一场
- 当天无排班显示"今日无排班"
- 毛玻璃深蓝卡片，延续排班站视觉；默认桌面右上角，可拖拽

## 提醒机制

- 提前 20 分钟、提前 5 分钟各一次 macOS 系统通知（osascript display notification + 声音）
- 状态文件去重（记录 日期|直播间|场次 键，同场次不重复通知；跨天自动重置）
- 只提醒"下一场"，避免刷屏

## 可复制性

新 Mac 三步启用：
1. 安装 Übersicht（brew install --cask ubersicht，或使用已下载的 DMG）
2. 拷贝 `schedule-widget.widget/` 到 `~/Library/Application Support/Übersicht/widgets/`
3. 打开 Übersicht 自动加载

排班数据全部走 GitHub 在线，新电脑零配置零迁移。

## 后续阶段（不纳入本次实现）

- A 方案：macOS 快捷指令（Shortcuts）原生小组件（.shortcut 导出导入）
- 小爱音箱播报：通知触发点已隔离，后续接小爱音箱只需在触发处加一路调用

## 验证方式

- 本地起 http.server 提供模拟数据，浏览器 1280px 视口渲染验证
- 真实 Übersicht 环境加载 widget 截图确认
- 用临时排班数据验证 20/5 分钟通知触发与去重
