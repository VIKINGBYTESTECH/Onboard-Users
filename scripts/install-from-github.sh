#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/VIKINGBYTESTECH/Onboard-Users}"
BRANCH="${BRANCH:-main}"
TARGET_DIR="${TARGET_DIR:-onboard-users}"
RUN_INSTALL="${RUN_INSTALL:-true}"
RUN_SERVICE="${RUN_SERVICE:-true}"
TARGET_WAS_DEFAULT="true"

usage() {
  cat <<EOF
Usage: install-from-github.sh [--target DIR] [--branch BRANCH] [--no-install] [--no-service]

Environment overrides:
  REPO_URL     GitHub repository URL
  BRANCH       Branch to download
  TARGET_DIR   Destination directory
  RUN_INSTALL  true/false
  RUN_SERVICE  true/false
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      TARGET_WAS_DEFAULT="false"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --no-install)
      RUN_INSTALL="false"
      RUN_SERVICE="false"
      shift
      ;;
    --no-service)
      RUN_SERVICE="false"
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

if ! command -v curl >/dev/null 2>&1; then
  echo "Missing required command: curl" >&2
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  echo "Missing required command: tar" >&2
  exit 1
fi

if [ "${EUID:-$(id -u)}" = "0" ] && [ "${ALLOW_ROOT:-false}" != "true" ]; then
  echo "Do not run this installer with sudo/root." >&2
  echo "Run it as your normal user from a writable directory, for example:" >&2
  echo "  cd ~" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/VIKINGBYTESTECH/Onboard-Users/main/scripts/install-from-github.sh | bash" >&2
  echo "Set ALLOW_ROOT=true only if you intentionally want root-owned files." >&2
  exit 1
fi

if [ "$TARGET_WAS_DEFAULT" = "true" ] && [ ! -w "$PWD" ]; then
  TARGET_DIR="$HOME/onboard-users"
  echo "Current directory is not writable; using $TARGET_DIR"
fi

TARGET_PARENT="$(dirname "$TARGET_DIR")"
if [ ! -d "$TARGET_PARENT" ] || [ ! -w "$TARGET_PARENT" ]; then
  echo "Target parent is not writable: $TARGET_PARENT" >&2
  echo "Choose a writable location, for example:" >&2
  echo "  curl -fsSL https://raw.githubusercontent.com/VIKINGBYTESTECH/Onboard-Users/main/scripts/install-from-github.sh | bash -s -- --target \"\$HOME/onboard-users\"" >&2
  exit 1
fi

if [ -e "$TARGET_DIR" ]; then
  echo "Target already exists: $TARGET_DIR" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ARCHIVE_URL="$REPO_URL/archive/refs/heads/$BRANCH.tar.gz"
echo "Downloading $ARCHIVE_URL"
curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR"

EXTRACTED_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
mv "$EXTRACTED_DIR" "$TARGET_DIR"

cd "$TARGET_DIR"
chmod +x scripts/*.sh

echo "Downloaded to $TARGET_DIR"

if [ "$RUN_INSTALL" = "true" ]; then
  ./scripts/install.sh --wizard
  if [ "$RUN_SERVICE" = "true" ]; then
    if command -v systemctl >/dev/null 2>&1; then
      ./scripts/install-service.sh
    else
      echo "systemctl not found; skipping automatic service setup."
      echo "Start manually with:"
      echo "  cd $TARGET_DIR && HTTPS=true ./scripts/run-dev.sh"
    fi
  else
    echo "Skipped service setup. Start manually with:"
    echo "  cd $TARGET_DIR && HTTPS=true ./scripts/run-dev.sh"
  fi
else
  echo "Skipped install. Run later with:"
  echo "  cd $TARGET_DIR && ./scripts/install.sh"
fi
