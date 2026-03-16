#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/matt/Documentos/Agente FInanceiro/Agent-Financeiro"
APP_URL="http://127.0.0.1:8501"
LOG_OUT="$PROJECT_DIR/streamlit_local.out.log"
LOG_ERR="$PROJECT_DIR/streamlit_local.err.log"

cd "$PROJECT_DIR"

if ! pgrep -af "streamlit run app.py" >/dev/null 2>&1; then
  setsid -f bash -lc "cd \"$PROJECT_DIR\" && ./run_local_linux.sh >> \"$LOG_OUT\" 2>> \"$LOG_ERR\""
fi

for _ in $(seq 1 60); do
  if curl -fsS "$APP_URL" >/dev/null 2>&1; then
    xdg-open "$APP_URL" >/dev/null 2>&1 &
    exit 0
  fi
  sleep 1
done

exit 1
