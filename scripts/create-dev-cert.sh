#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT_DIR/.certs"
KEY_FILE="$CERT_DIR/localhost-key.pem"
CERT_FILE="$CERT_DIR/localhost-cert.pem"

if [ -f "$KEY_FILE" ] && [ -f "$CERT_FILE" ]; then
  echo "Dev HTTPS certificate already exists in .certs/"
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "Missing required command: openssl" >&2
  echo "Install OpenSSL, then run this script again." >&2
  exit 1
fi

mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1

chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "Created local dev HTTPS certificate in .certs/"
echo "Your browser will show a warning because this certificate is self-signed."
