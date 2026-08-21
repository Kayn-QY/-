# 2026-08-21 编辑页工具栏与今日列样式调整设计

## 背景

编辑页工具栏与今日列样式需调整：删除两个按钮入口、简化「清除全部」样式、统一今日列配色。经头脑风暴逐项确认后进入实现。用户已确认设计方案，授权改完直接部署。

## 需求清单

### 1. 删除「清除选定日期」按钮

- 工具栏按钮（btn-clear-date）HTML 与事件绑定移除。
- 保留 `clearSelectedDate` 函数定义、点击日期表头选中列高亮逻辑（功能代码不删，仅无入口）。

### 2. 删除「粘贴截图」按钮

- 工具栏按钮（btn-paste-ocr）HTML 与事件绑定移除。
- 保留 OCR 相关函数定义与弹窗代码；「复制粘贴」文本解析功能完全不受影响。

### 3. 「清除全部」去除红色填色

- class 由 `btn-danger` 改为 `btn-outline`：无红色渐变填充，改为普通描边按钮（白色半透明底 + 白边框），与「复制粘贴」等按钮一致。

### 4. 当日日期红色填充改为「保存并发布」填充色

- 编辑页主界面 CSS、编辑页内嵌展示页模板（PAGE_JS_TEMPLATE）、render_web.py CSS_TEMPLATE 三处 `date-col.today` 统一改为深蓝渐变 `#0a1b33 → #1e3a5f`，文字白色。
- 展示页（index.html / output/schedule.html）与编辑页风格保持一致。

### 5. 底部说明文案

- board-note 移除「清除选定日期」相关描述，保留「点击日期表头可选中该列（高亮）」「清除全部清空当前直播间全部数据」。

## 改动位置

| 文件 | 位置 | 改动 |
|---|---|---|
| editor.html | 工具栏 HTML（~250-252 行） | 删除 btn-clear-date、btn-paste-ocr 两按钮；btn-clear-all 改 btn-outline |
| editor.html | init 事件绑定（~1747/1750 行） | 移除 btn-clear-date、btn-paste-ocr 的 addEventListener |
| editor.html | 主界面 CSS（~133 行） | date-col.today 改深蓝渐变 |
| editor.html | PAGE_JS_TEMPLATE CSS（~956 行） | date-col.today 改深蓝渐变 |
| editor.html | board-note（~274 行） | 文案更新 |
| render_web.py | CSS_TEMPLATE（~182 行） | date-col.today 改深蓝渐变 |

## 实现与验证

- 用 python 脚本对 editor.html / render_web.py 做精确字符串替换（断言 count==1）。
- 重新生成 index.html（python render_web.py + cp）。
- 本地 http.server 8899 起服务，browser-agent 桌面 + 375px 实测：两按钮消失、清除全部为描边按钮、今日列为深蓝渐变。
- 验证通过后 git push 部署到 GitHub Pages。

## 风险

- 删除按钮 HTML 后若事件绑定残留会导致 `$("btn-paste-ocr")` 为 null 报错，必须同步移除绑定（本方案已覆盖）。
- 展示页与编辑页三处 CSS 需保持同步，脚本替换后 grep 复核。
