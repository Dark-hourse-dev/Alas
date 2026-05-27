#!/bin/bash
# ALAS Launcher (Backend + Desktop App)

# 1. Start the ALAS backend server in the background
echo "🧬 Starting ALAS Backend Server..."
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to initialize
sleep 3
echo "✅ Backend started (PID: $BACKEND_PID)"

# 2. Start the ALAS Desktop App
echo "💻 Starting ALAS Desktop App..."
cd desktop
npm start

# When the desktop app closes, kill the backend
echo "🛑 Shutting down ALAS..."
kill $BACKEND_PID
