# 2026-08-21 排班站三模块迭代设计

## 背景

排班站（editor.html 编辑页 + render_web.py / index.html 展示页）本轮迭代三个需求，经头脑风暴逐项确认后进入实现。用户已授权"开始，后续不用我确认了，改完直接部署"。

## 需求清单

### 模块 1：粘贴/OCR 预览日期列可编辑

- 预览表（renderEditablePreview）日期列由纯文本改为可编辑输入框，允许任意日期。
- 输入格式兼容：`08/17`、`08-17`、`2026-08-17`、`8月17日`、`8.17`、`0817`。
- 无效日期输入标红，确认写入前整体校验，任一无效则中止并提示。
- 目标日期已有同名场次（同一日期同一场次已有数据）时，弹确认提示"覆盖"；确认后覆盖写入，取消则不写入。

改动点（editor.html）：
1. 新增 `parseFlexDate(s)`：解析上述 6 种格式 → Date；失败返回 null。
2. `renderEditablePreview` 日期单元格改为 `<input class="cell-edit date-cell" ...>`，input 事件中经 parseFlexDate 转标准 `YYYY-MM-DD` 存入 `col.date`，无效加 `.invalid` 标红。
3. `confirmPaste` 写入前：校验全部列日期有效（无效中止）；统计冲突场次（日期+场次已存在），有冲突弹 confirm 覆盖确认；确认后覆盖写入（不再保留旧值）。

### 模块 2：编辑页删除直播间

- 方案 A：每个直播间 Tab 右上角小 ×，悬停显示，点击弹确认。
- 只剩 1 个直播间时禁用删除（不显示 ×）。
- 删除后：删除 schedule[room] 数据、config.rooms 移除、切换到剩余第一个直播间，发布四文件（schedule.json / config.json / index.html / output/schedule.html）。

改动点（editor.html）：
1. CSS：新增 `.room-tab-del`（右上角 ×，悬停显示）。
2. `renderRoomSwitch`：Tab 内嵌删除按钮（rooms.length > 1 时显示）。
3. 新增 `deleteRoomEditor(room)`：confirm → 删数据 → 切房间 → 重渲染 → 调 `save()` 发布。
4. document click 监听：优先命中 `.room-tab-del`，stopPropagation 后进入删除流程。

### 模块 3：主播场次统计改为当天（北京时间）共计

- 展示页与编辑页的 buildStats 由"遍历全部日期每周共计"改为"只统计当天（北京时间）"。
- 当天无排班时显示"今日暂无"（原"暂无数据"）。
- 同步改动 3 处逻辑：编辑页 `buildStatsHtml`、展示页模板 `buildStats`（editor.html PAGE_JS_TEMPLATE + render_web.py PAGE_JS 同一份 JS）、render_web.py Python 预渲染 `build_stats_html`。

改动点：
- editor.html `buildStatsHtml`：只统计 `data[todayISO()]`。
- editor.html PAGE_JS_TEMPLATE `buildStats`：只统计 `data[todayISO()]`，空态文案改"今日暂无"。
- render_web.py `PAGE_JS` 内 `buildStats`：同上。
- render_web.py `build_stats_html`：Python 侧以北京时间当天为准，空态文案改"今日暂无"。

## 实现与验证

- 用 python 脚本对 editor.html / render_web.py 做精确字符串替换（断言 count==1），避免并行工具互相覆盖。
- 重新生成 index.html（python render_web.py）。
- 本地 http.server 8899 起服务，派 browser-agent 桌面 + 375px 实测三模块。
- 验证通过后 git push 部署到 GitHub Pages。

## 风险

- 编辑页与展示页两处 JS 模板需保持一致，脚本替换后 grep 复核。
- 删除直播间为破坏性操作，仅编辑器内 confirm 确认；不涉及文件系统删除。
