#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    echo 'Run bash SETUP.sh first.'
    exit 1
fi
if [[ -z "${DISPLAY:-}" ]]; then
    echo 'The Tk interface needs X11 or XWayland. Start from a desktop terminal (CachyOS: install xorg-xwayland).'
    exit 1
fi
.venv/bin/python check_system.py || echo 'Input setup is incomplete. Soundtracks and demo editing are still available.'
exec .venv/bin/python LPHK.py "$@"
