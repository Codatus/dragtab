#!/bin/sh
# Installs DragTab for the current user.
# ./install.sh              install and start
# ./install.sh --uninstall  remove everything again
set -e
cd "$(dirname "$0")"

BIN="$HOME/.local/bin/dragtab"
UNIT="$HOME/.config/systemd/user/dragtab.service"
AUTOSTART="$HOME/.config/autostart/dragtab-start.desktop"

if [ "$1" = "--uninstall" ]; then
    systemctl --user stop dragtab.service 2>/dev/null || true
    rm -f "$BIN" "$UNIT" "$AUTOSTART"
    systemctl --user daemon-reload
    echo "DragTab removed (~/.config/dragtab.conf was kept)."
    exit 0
fi

for p in python3 xprop xdotool; do
    command -v "$p" >/dev/null || { echo "Missing: $p (sudo apt install xdotool x11-utils)"; exit 1; }
done

install -Dm755 dragtab.py "$BIN"
install -Dm644 dragtab.service "$UNIT"
install -Dm644 dragtab-start.desktop "$AUTOSTART"
systemctl --user daemon-reload
systemctl --user import-environment DISPLAY XAUTHORITY
systemctl --user restart dragtab.service
systemctl --user --no-pager status dragtab.service | head -3
