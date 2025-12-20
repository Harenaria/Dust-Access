#!/bin/bash

# 1. CLEANUP: Kill any lingering python processes related to this project
echo "--- Killing old processes ---"
pkill -f "networking.server"
pkill -f "client_views.fletapp.client_flet"
# Give them a moment to die
sleep 1

# 2. HOUSEKEEPING: Delete logs and cached bytecode
echo "--- Cleaning logs and caches ---"
rm -rf .runlogs
mkdir -p .runlogs
# Delete __pycache__ to force Python to read your new code changes
find . -name "__pycache__" -type d -exec rm -rf {} +

# 3. ENVIRONMENT: Force Python to look in the CURRENT directory first
export PYTHONPATH=".:${PYTHONPATH}"
export SERVER_URL="ws://127.0.0.1:8765"

# 4. START SERVER
echo "--- Starting Server ---"
# We use nohup to ensure it doesn't die if the terminal blinks, but we log to file
poetry run python -m networking.server > .runlogs/server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Blind wait to let server start (no fancy check)
sleep 3

# 5. START CLIENTS
echo "--- Starting Clients ---"
poetry run python -m client_views.fletapp.client_flet > .runlogs/client1.log 2>&1 &
CLIENT1_PID=$!
echo "Client 1 PID: $CLIENT1_PID"

sleep 1

poetry run python -m client_views.fletapp.client_flet > .runlogs/client2.log 2>&1 &
CLIENT2_PID=$!
echo "Client 2 PID: $CLIENT2_PID"

echo "--- System Running ---"
echo "Press Ctrl+C to stop everything."

# 6. LOG MONITORING & TRAP
# When you hit Ctrl+C, this function runs to kill the PIDs we just started
cleanup() {
    echo "Stopping..."
    kill $SERVER_PID $CLIENT1_PID $CLIENT2_PID 2>/dev/null
    exit
}
trap cleanup INT

# Watch the logs
tail -f .runlogs/*.log