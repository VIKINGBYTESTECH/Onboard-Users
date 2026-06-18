#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/VIKINGBYTESTECH/Onboard-Users}"
BRANCH="${BRANCH:-main}"
TARGET_DIR="${TARGET_DIR:-onboard-users}"
RUN_INSTALL="${RUN_INSTALL:-true}"

usage() {
  cat <<EOF
Usage: install-from-github.sh [--target DIR] [--branch BRANCH] [--no-install]

Environment overrides:
  REPO_URL     GitHub repository URL
  BRANCH       Branch to download
  TARGET_DIR   Destination directory
  RUN_INSTALL  true/false
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --no-install)
      RUN_INSTALL="false"
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
  ./scripts/install.sh
else
  echo "Skipped install. Run later with:"
  echo "  cd $TARGET_DIR && ./scripts/install.sh"
fi
