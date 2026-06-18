#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-onboard-users}"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/$SERVICE_NAME.service"
BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
USE_HTTPS="${HTTPS:-true}"
ENABLE_LINGER="${ENABLE_LINGER:-true}"

usage() {
  cat <<EOF
Usage: install-service.sh [--http] [--https] [--name SERVICE_NAME] [--no-linger]

Installs a systemd user service that starts this app on login/reboot.

Options:
  --http          Serve HTTP instead of HTTPS
  --https         Serve HTTPS (default)
  --name NAME     Service name (default: onboard-users)
  --no-linger     Do not attempt loginctl enable-linger
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --http)
      USE_HTTPS="false"
      shift
      ;;
    --https)
      USE_HTTPS="true"
      shift
      ;;
    --name)
      SERVICE_NAME="$2"
      UNIT_FILE="$UNIT_DIR/$SERVICE_NAME.service"
      shift 2
      ;;
    --no-linger)
      ENABLE_LINGER="false"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is missing. This service installer requires Linux with systemd." >&2
  exit 1
fi

if [ ! -x "$ROOT_DIR/backend/.venv/bin/python" ] || [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Dependencies are missing. Running ./scripts/install.sh first."
  "$ROOT_DIR/scripts/install.sh"
fi

cd "$ROOT_DIR/frontend"
npm run build

if [ "$USE_HTTPS" = "true" ]; then
  "$ROOT_DIR/scripts/create-dev-cert.sh"
fi

mkdir -p "$UNIT_DIR"
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=IT Onboarding App
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
Environment=HTTPS=$USE_HTTPS
Environment=BACKEND_PORT=$BACKEND_PORT
Environment=FRONTEND_PORT=$FRONTEND_PORT
ExecStart=$ROOT_DIR/scripts/run-service.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME.service"

if [ "$ENABLE_LINGER" = "true" ] && command -v loginctl >/dev/null 2>&1; then
  if loginctl enable-linger "$USER" >/dev/null 2>&1; then
    echo "Enabled linger for $USER so the service can start after reboot before login."
  else
    echo "Could not enable linger automatically. If the service does not start after reboot, run:" >&2
    echo "  loginctl enable-linger $USER" >&2
  fi
fi

echo
echo "Installed and started $SERVICE_NAME.service"
echo "Status:"
echo "  systemctl --user status $SERVICE_NAME.service"
echo "Logs:"
echo "  journalctl --user -u $SERVICE_NAME.service -f"
if [ "$USE_HTTPS" = "true" ]; then
  echo "Open:"
  echo "  https://localhost:$FRONTEND_PORT"
else
  echo "Open:"
  echo "  http://localhost:$FRONTEND_PORT"
fi
