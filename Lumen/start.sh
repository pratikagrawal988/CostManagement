#!/usr/bin/env bash
# ── Lumen FinOps OS — one-command startup ────────────────────────────────────
set -e

cd "$(dirname "$0")"

echo ""
echo "  ██╗     ██╗   ██╗███╗   ███╗███████╗███╗   ██╗"
echo "  ██║     ██║   ██║████╗ ████║██╔════╝████╗  ██║"
echo "  ██║     ██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║"
echo "  ██║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║"
echo "  ███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║"
echo "  ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝"
echo "  FinOps OS — Cloud & AI Cost Intelligence"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
  echo "✗ Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "✗ Docker daemon is not running. Start Docker Desktop and try again."
  exit 1
fi

# ── Env file ──────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "→ Creating .env from .env.example"
  cp .env.example .env
fi

# ── Build & start ─────────────────────────────────────────────────────────────
echo "→ Building and starting services (this takes ~60s on first run)..."
echo ""
docker compose up --build -d

# ── Wait for backend ──────────────────────────────────────────────────────────
echo ""
echo "→ Waiting for backend to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8088/health > /dev/null 2>&1; then
    echo "  ✓ Backend ready"
    break
  fi
  sleep 2
  printf "."
done
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ┌────────────────────────────────────────────────┐"
echo "  │  🚀 Lumen FinOps OS is running                 │"
echo "  │                                                 │"
echo "  │  Frontend:   http://localhost:5175              │"
echo "  │  API docs:   http://localhost:8088/docs         │"
echo "  │  API health: http://localhost:8088/health       │"
echo "  │                                                 │"
echo "  │  Navigate to → ✦ AI Cost  in the sidebar       │"
echo "  │  Navigate to → Cloud Credentials to connect    │"
echo "  │                   AWS / Azure / GCP             │"
echo "  │                                                 │"
echo "  │  To stop: docker compose down                  │"
echo "  │  Logs:    docker compose logs -f backend        │"
echo "  └────────────────────────────────────────────────┘"
echo ""
