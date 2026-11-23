#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import tkinter' || {
  echo 'Install Python with Tk and venv support (Ubuntu/Debian: sudo apt install python3-tk python3-venv).'
  exit 1
}
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
echo 'Setup complete. Start with: bash RUN.bash'
