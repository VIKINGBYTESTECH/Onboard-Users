#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-onboard-users}"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/$SERVICE_NAME.service"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is missing." >&2
  exit 1
fi

systemctl --user disable --now "$SERVICE_NAME.service" >/dev/null 2>&1 || true
rm -f "$UNIT_FILE"
systemctl --user daemon-reload

echo "Removed $SERVICE_NAME.service"
