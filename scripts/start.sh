#!/bin/bash

# FactFlow Full Stack Startup Script
# Starts backend API + frontend UI with optional virtualenv & dynamic port

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend/factflow-ui"

API_PORT="${API_PORT:-5001}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "🚀 Starting FactFlow (API:${API_PORT} UI:${FRONTEND_PORT})"
echo ""

# Root .env requirements
if [ ! -f "${ROOT_DIR}/.env" ]; then
    echo "❌ Root .env missing. Please create it with required API keys."
    exit 1
fi

# Ensure virtual environment python (fallback to system python3)
PY_BIN="python3"
if [ -d "${ROOT_DIR}/.venv" ] && [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    PY_BIN="${ROOT_DIR}/.venv/bin/python"
fi

# Sync frontend .env with current API_PORT
if [ ! -f "${FRONTEND_DIR}/.env" ]; then
    echo "⚠️  Creating frontend .env"
    echo "VITE_API_URL=http://localhost:${API_PORT}" > "${FRONTEND_DIR}/.env"
else
    # Replace existing VITE_API_URL line deterministically
    if grep -q '^VITE_API_URL=' "${FRONTEND_DIR}/.env"; then
        sed -i.bak "s|^VITE_API_URL=.*|VITE_API_URL=http://localhost:${API_PORT}|" "${FRONTEND_DIR}/.env" && rm -f "${FRONTEND_DIR}/.env.bak"
    else
        echo "VITE_API_URL=http://localhost:${API_PORT}" >> "${FRONTEND_DIR}/.env"
    fi
fi

# Clean stale pid files
rm -f "${FRONTEND_DIR}/frontend.pid" 2>/dev/null || true

cleanup() {
    echo "\n🛑 Shutting down services..."
    [ -n "${API_PID:-}" ] && kill ${API_PID} 2>/dev/null || true
    [ -n "${UI_PID:-}" ] && kill ${UI_PID} 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

echo "📡 Starting Backend API (port ${API_PORT})..."
(
    cd "${ROOT_DIR}"
    API_PORT=${API_PORT} ${PY_BIN} -m backend.api_server
) &
API_PID=$!
echo "   Backend PID: ${API_PID}"

# Wait until port responds or timeout
ATTEMPTS=0
until nc -z localhost ${API_PORT} 2>/dev/null || [ ${ATTEMPTS} -ge 30 ]; do
    ATTEMPTS=$((ATTEMPTS+1))
    sleep 0.2
done
if ! nc -z localhost ${API_PORT} 2>/dev/null; then
    echo "❌ API failed to bind port ${API_PORT}"; exit 1
fi

echo "🎨 Starting Frontend UI..."
pushd "${FRONTEND_DIR}" >/dev/null
if [ ! -d node_modules ]; then
    echo "   Installing frontend dependencies (npm)..."
    npm install || bun install || { echo "❌ Frontend dependency install failed"; exit 1; }
fi
PORT=${FRONTEND_PORT} npm run dev &
UI_PID=$!
popd >/dev/null
echo "   Frontend PID: ${UI_PID}"

echo ""
echo "✅ FactFlow running"
echo "   API:       http://localhost:${API_PORT}"
echo "   Frontend:  http://localhost:${FRONTEND_PORT}"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

wait ${API_PID} ${UI_PID}
