---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 9d4a1ded685a81c80cf27c0c57895e9b_52e761219c4111f19046525400287e28
    ReservedCode1: SuGV06qrjSvTKUI4cTV9iIgYAQhESnizKVEBsvxn8MJ10aEoz3H2PXcm6/AtdE2ARJqMCb+AeIIdNo8GRVUcF7LznmpFzpOHSwOKaYFlIFu2BBpMMMjqXaPQSCjUjaJEVOdMkxMeCCA7RiBKUOQWVevh7vUca8ZCZS/n0hbXKsws3hS+w6sfndtKgr0=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 9d4a1ded685a81c80cf27c0c57895e9b_52e761219c4111f19046525400287e28
    ReservedCode2: SuGV06qrjSvTKUI4cTV9iIgYAQhESnizKVEBsvxn8MJ10aEoz3H2PXcm6/AtdE2ARJqMCb+AeIIdNo8GRVUcF7LznmpFzpOHSwOKaYFlIFu2BBpMMMjqXaPQSCjUjaJEVOdMkxMeCCA7RiBKUOQWVevh7vUca8ZCZS/n0hbXKsws3hS+w6sfndtKgr0=
---

# 排班页五项迭代设计（2026-08-20）

## 背景
极氪日播间排班站已上线（https://kayn-qy.github.io/-/），当前为毛玻璃 3D 版，含冻结列、实时提醒、内嵌编辑入口。本轮按用户需求做五项功能与视觉调整。

## 1. 提醒逻辑：提前一场
- 始终只显示「下一场」（未来最近一场**尚未开始**的场次，含当天与之后日期）
- 正在直播的场次不显示；当天无剩余场次时自动取之后最近一天首场
- 每 30 秒按北京时间重算
- 显示格式保持 `直播间 时间 主播开播`；无排班显示「暂无排班」

## 2. 冻结列：场次+角色贴合成组
- `场次`、`角色` 两列合并为固定列组，`sticky` 冻结（场次 left:0、角色 left:90px），横向滑动整组不动
- 固定列组与右侧日期表格区之间加明显视觉分界：独立底色 + 1px 分隔线 + 轻微阴影
- 表头与固定列组保持同一背景色，避免滑动穿帮

## 3. 删除技术/投流列（彻底删除）
- `render_web.py` 渲染模板、`editor.html` 编辑表单、`schedule.json` 同步移除 `tech` / `ad` 字段
- 历史数据字段清空

## 4. 表格等长等宽
- 所有直播间表格整体同宽（统一 max-width）
- 日期列等宽（table-layout: fixed + 统一列宽）
- 所有单元格行高等高（统一 min-height / padding），内容超长省略号截断
- 固定列组（场次/角色）列宽与行高统一

## 5. 在线编辑页新功能
### 5.1 清除按钮
- 弹日期选择（单选/范围），确认后清除**当前选中直播间**该日期范围内的全部场次数据，写回 GitHub

### 5.2 复制粘贴按钮
- 粘贴文本 → 自动解析：
  - 日期：从文字中识别（支持 `8.17` / `2026-08-17` / `8月17日` 等格式）
  - 场次：按文字中出现的时间区间顺序，依次写入第1场、第2场……
  - 直播间：忽略文字中的标识，写入当前选中直播间
  - 主播：取紧跟直播间后的第一个名字，其余忽略
- 解析结果先预览确认，再写入并保存到 GitHub
- 无法解析的行标红提示，不阻塞其他行

## 数据流
- 修改入口：`render_web.py`（PAGE_JS/CSS_TEMPLATE/渲染模板）、`editor.html`（CSS_VIEW/PAGE_JS/编辑逻辑）
- 数据：`schedule.json`（移除 tech/ad 字段）
- 生成：重新运行 `render_web.py` 生成 `index.html` / `output/schedule.html`
- 部署：git commit + push 到 GitHub Pages（推送走 Clash 代理 127.0.0.1:7897）

## 验收标准
- 提醒始终显示下一场，正在直播的不显示
- 横向滑动时场次/角色整组不动且有明显分隔
- 页面与编辑页均无技术/投流列，JSON 无残留字段
- 各直播间表格同宽、列等宽、行等高
- 编辑页可按日期范围清除当前直播间数据
- 粘贴文本可自动解析日期/时间/主播并预览后写入
*（内容由AI生成，仅供参考）*
