#!/bin/bash
# 查看提醒引擎状态
cd "$(dirname "$0")"
LABEL="com.marvis.schedule-reminder"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "==> launchd 服务:"
if [ -f "$PLIST" ]; then
  launchctl list | grep "$LABEL" || echo "未加载"
else
  echo "未安装 launchd 服务（可运行 install_launchd.sh 安装）"
fi

echo ""
echo "==> 最近日志:"
if [ -f "temp/logs/reminder.log" ]; then
  tail -20 temp/logs/reminder.log
else
  echo "暂无日志"
fi
