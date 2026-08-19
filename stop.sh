#!/bin/bash
# 停止提醒引擎（launchd 服务或后台进程）
cd "$(dirname "$0")"
LABEL="com.marvis.schedule-reminder"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  echo "已停止 launchd 服务 $LABEL"
else
  pkill -f "reminder.py" 2>/dev/null && echo "已停止后台进程" || echo "未发现运行中的进程"
fi
