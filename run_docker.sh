#!/usr/bin/env bash
# run_docker.sh
# One-click script to build and launch CivicGuard AI Tourist Crowd Monitor in Docker

set -e

echo "=========================================================="
echo "🚀 Building CivicGuard AI Tourist Crowd Monitor Container"
echo "=========================================================="

# Build image
docker build -t crowd-monitor:latest .

echo "=========================================================="
echo "🎬 Launching Container with Hardware Device Mapping"
echo "=========================================================="

# Check if webcam device /dev/video0 exists
DEVICE_FLAG=""
if [ -e "/dev/video0" ]; then
    echo "📷 Detected camera at /dev/video0. Passing to container..."
    DEVICE_FLAG="--device /dev/video0:/dev/video0"
else
    echo "ℹ️ No /dev/video0 detected. Running with simulated / network video mode."
fi

# Stop any existing container
docker rm -f ai_tourist_crowd_monitor 2>/dev/null || true

# Run container on port 5000
docker run -d \
    --name ai_tourist_crowd_monitor \
    -p 5000:5000 \
    $DEVICE_FLAG \
    -v "$(pwd)/alerts:/app/alerts" \
    crowd-monitor:latest

echo ""
echo "=========================================================="
echo "✅ CivicGuard Smart City Crowd Monitor is live in Docker!"
echo "📺 Municipal CCTV Surveillance: http://localhost:5000/"
echo "🚉 Street/Railway Dumb Kiosk:   http://localhost:5000/kiosk"
echo "🌐 Citizen Remote Portal:       http://localhost:5000/public"
echo "🛡️ Security Admin Console:      http://localhost:5000/admin"
echo "📜 To view live logs:           docker logs -f ai_tourist_crowd_monitor"
echo "⏹️ To stop container:          docker stop ai_tourist_crowd_monitor"
echo "=========================================================="
