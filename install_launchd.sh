#!/bin/bash
# 安装提醒引擎为 macOS 开机自启服务 (launchd)
set -e
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
LABEL="com.marvis.schedule-reminder"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$PROJECT_DIR/reminder.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$PROJECT_DIR/temp/logs/reminder.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/temp/logs/reminder.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "已安装并启动: $LABEL"
