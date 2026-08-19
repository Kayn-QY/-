#!/bin/bash
# 一键部署：渲染 HTML → 推送到 git 仓库（公开静态托管）
set -e
cd "$(dirname "$0")"

# 1. 渲染网页
echo "==> 渲染排班网页..."
python3 render_web.py
cp output/schedule.html index.html

# 2. 检查 git 配置
REMOTE=$(python3 -c "import json;print(json.load(open('config.json'))['git']['remote'])")
BRANCH=$(python3 -c "import json;print(json.load(open('config.json'))['git']['branch'])")
USER_NAME=$(python3 -c "import json;print(json.load(open('config.json'))['git']['user_name'])")
USER_EMAIL=$(python3 -c "import json;print(json.load(open('config.json'))['git']['user_email'])")

if [ -z "$REMOTE" ]; then
  echo "错误: config.json 中未配置 git.remote"
  exit 1
fi

# 3. 初始化仓库（如需要）
if [ ! -d ".git" ]; then
  echo "==> 初始化 git 仓库..."
  git init -b "$BRANCH"
  git remote add origin "$REMOTE"
fi

git config user.name "$USER_NAME"
if [ -n "$USER_EMAIL" ]; then
  git config user.email "$USER_EMAIL"
fi

# 4. 提交并推送
echo "==> 提交并推送..."
git add output/schedule.html index.html schedule.json editor.html
git commit -m "更新排班表 $(date '+%Y-%m-%d %H:%M')" || echo "无变更可提交"
git push -u origin "$BRANCH" 2>&1 || echo "推送失败，请检查仓库权限/地址"

echo "==> 完成"
