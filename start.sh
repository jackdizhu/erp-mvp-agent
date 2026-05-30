#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[ERP Agent MVP] Starting backend and frontend..."

# Backend
cd "$SCRIPT_DIR"
pip install -r app/requirements.txt &>/dev/null &
echo "[ERP Agent MVP] Installing backend dependencies..."

# Wait for install to finish
wait
echo "[ERP Agent MVP] Starting backend on http://localhost:8000"
python -m app.main &

# Give backend a moment to start
sleep 2

# Frontend
echo "[ERP Agent MVP] Starting frontend on http://localhost:5173"
cd "$SCRIPT_DIR/frontend"
npm run dev &

echo "[ERP Agent MVP] Both servers started."
echo "[ERP Agent MVP] Backend:  http://localhost:8000"
echo "[ERP Agent MVP] Frontend: http://localhost:5173"
echo "[ERP Agent MVP] Press Ctrl+C to stop all servers."

# Keep script running and trap signals
trap 'echo ""; echo "[ERP Agent MVP] Stopping all servers..."; kill 0' EXIT INT TERM
wait
