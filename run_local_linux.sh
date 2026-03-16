#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import streamlit" >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

python database.py
python -m streamlit run app.py --server.address 127.0.0.1 --server.headless true
