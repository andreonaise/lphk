#!/usr/bin/env bash
# Run as your normal desktop user: bash SETUP_CACHYOS.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if (( EUID == 0 )); then
    echo 'Run this as your normal user. It invokes sudo for packages and the input helper only.'
    exit 1
fi
if ! command -v pacman >/dev/null; then
    echo 'This setup script is for CachyOS/Arch Linux with pacman.'
    exit 1
fi

echo 'Installing packages and a per-user ydotoold system service.'
echo 'Only the input helper runs as root. LPHK and its Python environment run as your user.'
# -Syu avoids unsupported partial upgrades on Arch-derived distributions.
sudo pacman -Syu --needed uv tk ydotool wtype xorg-xwayland

uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -c 'import tkinter'

desktop_uid="$(id -u)"
desktop_gid="$(id -g)"
service_name="lphk-ydotool-${desktop_uid}.service"
service_file="/etc/systemd/system/${service_name}"
temporary_unit="$(mktemp)"
trap 'rm -f -- "$temporary_unit"' EXIT
cat > "$temporary_unit" <<UNIT
[Unit]
Description=LPHK virtual input helper for UID ${desktop_uid}
After=systemd-udevd.service

[Service]
Type=simple
ExecStartPre=/usr/bin/modprobe uinput
ExecStart=/usr/bin/ydotoold --socket-path=/run/lphk-ydotool-${desktop_uid}/socket --socket-own=${desktop_uid}:${desktop_gid} --socket-perm=0600
RuntimeDirectory=lphk-ydotool-${desktop_uid}
RuntimeDirectoryMode=0711
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
sudo install -m 0644 -- "$temporary_unit" "$service_file"
sudo systemctl daemon-reload
sudo systemctl enable "$service_name"
sudo systemctl restart "$service_name"

.venv/bin/python configure_mango.py
# Recreate the virtual device so the compositor applies its dedicated rule.
sudo systemctl restart "$service_name"

# Wait for the helper's virtual device to be registered before returning.
for attempt in {1..30}; do
    if [[ -S "/run/lphk-ydotool-${desktop_uid}/socket" ]]; then
        break
    fi
    sleep 0.1
done
if [[ ! -S "/run/lphk-ydotool-${desktop_uid}/socket" ]]; then
    echo "Input helper did not create its socket. Check: systemctl status ${service_name}"
    exit 1
fi
sleep 1
.venv/bin/python check_system.py
echo
echo 'Setup complete. Start LPHK from a MangoWM terminal: bash RUN.bash'
echo 'Read-only diagnostic: .venv/bin/python check_system.py'
