#!/bin/bash
# Start both sandbox and dashboard servers
set -e

echo "Starting OpsAgent sandbox on port ${SANDBOX_PORT:-8001}..."
python -m uvicorn opsagent.sandbox.server:app --host 0.0.0.0 --port "${SANDBOX_PORT:-8001}" &
SANDBOX_PID=$!

echo "Starting OpsAgent dashboard on port ${DASHBOARD_PORT:-8000}..."
python -m uvicorn opsagent.dashboard.app:app --host 0.0.0.0 --port "${DASHBOARD_PORT:-8000}" &
DASHBOARD_PID=$!

echo "Both servers running. Sandbox PID=$SANDBOX_PID, Dashboard PID=$DASHBOARD_PID"

# Wait for either to exit
wait -n $SANDBOX_PID $DASHBOARD_PID
exit $?
