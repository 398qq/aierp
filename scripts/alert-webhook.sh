#!/bin/bash
# Standalone AlertManager webhook receiver.
# Runs on port 9099 (configured in ops/alertmanager/alertmanager.yml).
#
# Start:   make alert-webhook-start
# Stop:    make alert-webhook-stop
# Status:  make alert-webhook-status
# Logs:    make alert-webhook-logs
#
# Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (required)
#      TELEGRAM_DISABLED=1 (silence)

set -e

PORT="${ALERT_WEBHOOK_PORT:-9099}"
HOST="${ALERT_WEBHOOK_HOST:-0.0.0.0}"
LOG_DIR="$HOME/aierp/logs"
PID_FILE="$LOG_DIR/alert-webhook.pid"
LOG_FILE="$LOG_DIR/alert-webhook.log"

mkdir -p "$LOG_DIR"

cd "$HOME/aierp/backend"

case "${1:-status}" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Already running (pid $(cat "$PID_FILE"))"
      exit 0
    fi
    source venv/bin/activate
    nohup python -m uvicorn app.services.alertmanager_webhook:app \
      --host "$HOST" --port "$PORT" --log-level info \
      >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Started (pid $(cat "$PID_FILE"), port $PORT)"
    else
      echo "Failed to start — see $LOG_FILE"
      exit 1
    fi
    ;;
  stop)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE"
      echo "Stopped"
    else
      echo "Not running"
      rm -f "$PID_FILE"
    fi
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Running (pid $(cat "$PID_FILE"), port $PORT)"
    else
      echo "Not running"
    fi
    ;;
  logs)
    tail -f "$LOG_FILE"
    ;;
  *)
    echo "Usage: $0 {start|stop|status|logs}"
    exit 1
    ;;
esac
