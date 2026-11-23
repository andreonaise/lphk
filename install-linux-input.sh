#!/usr/bin/env bash
# One-time Wayland input permission setup for the prebuilt Linux release.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if (( EUID == 0 )); then
    echo 'Run as your desktop user. This script uses sudo for the input helper only.'
    exit 1
fi
[[ -x ./LPHK && -x ./_internal/tools/ydotoold ]] || {
    echo 'Extract the complete Linux release archive before running this script.'
    exit 1
}
desktop_uid="$(id -u)"
desktop_gid="$(id -g)"
service_name="lphk-ydotool-${desktop_uid}.service"
temporary_unit="$(mktemp)"
trap 'rm -f -- "$temporary_unit"' EXIT
echo 'Installing the bundled virtual-input helper. No packages or Python downloads are required.'
sudo install -d -m 0755 /usr/local/lib/lphk
sudo install -m 0755 -- ./_internal/tools/ydotoold /usr/local/lib/lphk/ydotoold
cat > "$temporary_unit" <<UNIT
[Unit]
Description=LPHK virtual input helper for UID ${desktop_uid}
After=systemd-udevd.service

[Service]
Type=simple
ExecStartPre=/usr/bin/modprobe uinput
ExecStart=/usr/local/lib/lphk/ydotoold --socket-path=/run/lphk-ydotool-${desktop_uid}/socket --socket-own=${desktop_uid}:${desktop_gid} --socket-perm=0600
RuntimeDirectory=lphk-ydotool-${desktop_uid}
RuntimeDirectoryMode=0711
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
sudo install -m 0644 -- "$temporary_unit" "/etc/systemd/system/${service_name}"
sudo systemctl daemon-reload
sudo systemctl enable "$service_name"
./LPHK --configure-mango
sudo systemctl restart "$service_name"
for attempt in {1..30}; do
    [[ -S "/run/lphk-ydotool-${desktop_uid}/socket" ]] && break
    sleep 0.1
done
[[ -S "/run/lphk-ydotool-${desktop_uid}/socket" ]] || {
    echo "Helper failed to start. Check: systemctl status ${service_name}"
    exit 1
}
sleep 1
./LPHK --check-system
echo 'Input setup complete. Start the application with ./LPHK'
