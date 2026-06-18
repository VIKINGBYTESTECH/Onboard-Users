#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
SETUP_MODE="${SETUP_MODE:-wizard}"

usage() {
  cat <<EOF
Usage: install.sh [--wizard] [--cli-config]

Options:
  --wizard      Install dependencies and let the browser setup wizard collect config (default)
  --cli-config  Ask for config in the terminal and mark setup complete
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --wizard)
      SETUP_MODE="wizard"
      shift
      ;;
    --cli-config)
      SETUP_MODE="cli"
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

prompt_default() {
  local label="$1"
  local default="$2"
  local secret="${3:-false}"
  local value
  if [ "$secret" = "true" ]; then
    read -r -s -p "$label [$default]: " value
    echo >&2
  else
    read -r -p "$label [$default]: " value
  fi
  echo "${value:-$default}"
}

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

create_venv() {
  cd "$BACKEND_DIR"
  if [ -x ".venv/bin/python" ]; then
    echo "Backend virtualenv already exists"
    return
  fi

  if python3 -m venv .venv >/dev/null 2>&1; then
    echo "Created backend virtualenv with python3 -m venv"
    return
  fi

  echo "python3 venv is unavailable; using virtualenv.pyz fallback"
  need_command curl
  curl -fsSL https://bootstrap.pypa.io/virtualenv.pyz -o /tmp/onboarding-virtualenv.pyz
  python3 /tmp/onboarding-virtualenv.pyz .venv
}

create_backend_env() {
  local env_file="$BACKEND_DIR/.env"
  if [ -f "$env_file" ]; then
    echo "backend/.env already exists"
    return
  fi

  if [ "$SETUP_MODE" = "wizard" ]; then
    echo "Skipping backend/.env prompts; browser setup wizard will collect config."
    return
  fi

  echo
  echo "Backend configuration"
  echo "Leave Entra values empty to run in preview-only mode."
  local frontend_origin tenant_id client_id client_secret domain usage_location portal_url it_email
  frontend_origin="$(prompt_default "Frontend origin" "https://localhost:5174")"
  tenant_id="$(prompt_default "Entra tenant ID" "")"
  client_id="$(prompt_default "Entra app/client ID" "")"
  client_secret="$(prompt_default "Entra client secret (optional, hidden)" "" true)"
  domain="$(prompt_default "Default user domain" "example.com")"
  usage_location="$(prompt_default "Usage location" "NO")"
  portal_url="$(prompt_default "Onboarding portal URL" "https://onboarding.example.com")"
  it_email="$(prompt_default "IT contact email" "it@example.com")"

  cat > "$env_file" <<EOF
FRONTEND_ORIGIN=$frontend_origin
FRONTEND_ORIGIN_REGEX=^https?://(localhost|127\\.0\\.0\\.1|100\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|[a-zA-Z0-9.-]+\\.ts\\.net):5174$
ENTRA_TENANT_ID=$tenant_id
ENTRA_CLIENT_ID=$client_id
ENTRA_CLIENT_SECRET=$client_secret
ENTRA_DEFAULT_DOMAIN=$domain
ENTRA_USAGE_LOCATION=$usage_location
OPTIONS_PATH=app/data/options.json
ONBOARDING_PORTAL_URL=$portal_url
IT_CONTACT_EMAIL=$it_email
SEND_PASSWORD_BY_EMAIL=false
ADMIN_AUTH_DISABLED=false
EOF
  echo "Created backend/.env"
}

create_runtime_files() {
  if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env.local"
    echo "Created frontend/.env.local"
  fi

  if [ ! -f "$BACKEND_DIR/app/data/options.json" ]; then
    cp "$BACKEND_DIR/app/data/options.example.json" "$BACKEND_DIR/app/data/options.json"
    echo "Created backend/app/data/options.json"
  fi

  if [ "$SETUP_MODE" = "wizard" ]; then
    rm -f "$BACKEND_DIR/.setup-complete"
    echo "Setup wizard will run on first browser start"
  elif [ ! -f "$BACKEND_DIR/.setup-complete" ]; then
    printf "complete\n" > "$BACKEND_DIR/.setup-complete"
    echo "Created backend/.setup-complete"
  fi
}

install_dependencies() {
  cd "$BACKEND_DIR"
  . .venv/bin/activate
  pip install -q -r requirements.txt
  echo "Installed backend dependencies"

  cd "$FRONTEND_DIR"
  npm install
  echo "Installed frontend dependencies"
}

main() {
  need_command python3
  need_command npm
  create_venv
  create_backend_env
  create_runtime_files
  install_dependencies

  echo
  echo "Install complete."
  echo "Install and start the service with:"
  echo "  ./scripts/install-service.sh"
  echo
  if [ "$SETUP_MODE" = "wizard" ]; then
    echo "Open https://localhost:5174 after service start to complete the setup wizard."
    echo
  fi
  echo "For temporary development without service:"
  echo "  HTTPS=true ./scripts/run-dev.sh"
  echo
  echo "For Entra app registration guidance:"
  echo "  docs/ENTRA_SETUP.md"
}

main "$@"
