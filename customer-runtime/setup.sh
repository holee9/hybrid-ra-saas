#!/bin/bash
set -e

# Hybrid RA Customer Runtime — Interactive Setup
# Generates .env with a secure JWT secret and configures CLOUD_SYNC_ENDPOINT.

CLOUD_API="https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io"

echo "=== Hybrid RA Customer Runtime Setup ==="
echo ""

if [ -f .env ]; then
  echo "[!] .env already exists. Overwrite? (y/N)"
  read -r OVERWRITE
  if [ "$OVERWRITE" != "y" ] && [ "$OVERWRITE" != "Y" ]; then
    echo "Aborted. Edit .env manually if needed."
    exit 0
  fi
fi

cp .env.example .env

# Generate JWT secret
if command -v openssl >/dev/null 2>&1; then
  JWT_SECRET=$(openssl rand -hex 32)
else
  JWT_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
fi
sed -i "s|change-me-must-be-at-least-32-characters-long!!|$JWT_SECRET|g" .env

# Organization name
echo "Organization name (e.g. acme-corp):"
read -r ORG_NAME
if [ -n "$ORG_NAME" ]; then
  sed -i "s|your-org-name|$ORG_NAME|g" .env
fi

# DB password
echo "PostgreSQL password (leave blank for random):"
read -r -s DB_PASS
if [ -z "$DB_PASS" ]; then
  DB_PASS=$(openssl rand -hex 16 2>/dev/null || echo "ra_$(date +%s)")
fi
sed -i "s|change-me-strong-password|$DB_PASS|g" .env
echo ""

# MinIO password (same as DB for simplicity, or separate)
MINIO_PASS=$(openssl rand -hex 16 2>/dev/null || echo "minio_$(date +%s)")
# Only replace the second occurrence (MINIO_PASSWORD line)
awk -v pass="$MINIO_PASS" '/MINIO_PASSWORD=/{sub(/change-me-strong-password/, pass)} {print}' .env > .env.tmp && mv .env.tmp .env

# Cloud sync endpoint
echo "Cloud sync endpoint [default: $CLOUD_API]:"
read -r SYNC_EP
if [ -n "$SYNC_EP" ]; then
  sed -i "s|$CLOUD_API|$SYNC_EP|g" .env
fi

echo ""
echo "=== .env configured. Next steps: ==="
echo ""
echo "1. Start services:"
echo "   docker-compose up -d"
echo ""
echo "2. Pull Ollama model (first run only, ~5GB):"
echo "   make pull-model"
echo ""
echo "3. Open UI at http://localhost:8080"
echo ""
