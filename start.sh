#!/bin/bash
# 手动启动提醒引擎（前台）
cd "$(dirname "$0")"
exec python3 reminder.py
