#!/bin/bash
# 周报生成器入口（cron 调用）
# 每周一 9:00 跑一次
set -e
cd /home/ttdiy/aierp/leads_pipeline
LOG=/tmp/leads_weekly.log
echo "[$(date '+%Y-%m-%d %H:%M')] 开始跑周报..." >> "$LOG"
python3 run_leads.py run-all --note "cron auto-run" >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M')] 周报跑完 ✅" >> "$LOG"
