#!/bin/bash
# Kill anything on port 5000
fuser -k 5000/tcp 2>/dev/null || true
pkill -f "python app.py" 2>/dev/null || true
pkill -f "flask" 2>/dev/null || true
sleep 1
echo "Starting PyJHora ASTRO_OS Flask server on port 5000..."
python app.py
