#!/bin/bash
# ALAS 2.0 Launcher (Backend + Desktop App + Mesh Daemon)

# 1. Start the ALAS backend server in the background
echo "🧬 Starting ALAS 2.0 Backend Server..."
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to initialize
sleep 3
echo "✅ Backend started (PID: $BACKEND_PID)"

# 2. Start the Mesh Daemon (if compiled)
if [ -f "mesh_daemon/target/debug/mesh_daemon" ]; then
    echo "🕸️ Starting Rust Mesh Daemon..."
    ./mesh_daemon/target/debug/mesh_daemon &
    MESH_PID=$!
    echo "✅ Mesh Daemon started (PID: $MESH_PID)"
else
    echo "⚠️ Mesh Daemon not compiled. Run 'cd mesh_daemon && cargo build' to enable P2P sync."
fi

# 3. Start the ALAS Desktop App
echo "💻 Starting ALAS Desktop App..."
cd desktop
npm start -- --no-sandbox

# When the desktop app closes, kill the backend and mesh daemon
echo "🛑 Shutting down ALAS..."
kill $BACKEND_PID
if [ -n "$MESH_PID" ]; then
    kill $MESH_PID
fi
