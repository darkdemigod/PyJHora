#!/bin/bash

# Kill any existing Python processes that might be holding port 5000
pkill -9 -f "python.*app.py" 2>/dev/null
pkill -9 -f "flask" 2>/dev/null

# Wait for processes to fully terminate
sleep 2

# Check if port 5000 is still in use and kill the process
PORT=5000
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    echo "Killing process $PID using port $PORT"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# Start the Flask application
echo "Starting Flask server on port $PORT..."
exec python3 app.py
