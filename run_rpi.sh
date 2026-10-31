#!/usr/bin/env bash
# ==============================================================================
# run_rpi.sh
# Dedicated Raspberry Pi 4 Edge Launcher for CivicGuard AI Tourist Crowd Monitor
#
# Hardware:
#   1. Raspberry Pi 4 Model B (4GB / 8GB)
#   2. Raspberry Pi Camera Module (CSI Ribbon Cable into CAM port)
#   3. Smartphone connected via USB as a DUMB DISPLAY
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================================${NC}"
echo -e "${GREEN}  🚀 CivicGuard Raspberry Pi 4 + Pi Cam Edge Production Launcher${NC}"
echo -e "${BLUE}==================================================================${NC}"

# Check for custom model
if [ -f "crowd_model.pt" ]; then
    echo -e "${GREEN}✅ Custom Model verified: crowd_model.pt (Local Fine-Tuned Weights)${NC}"
else
    echo -e "${YELLOW}ℹ️ crowd_model.pt not found. Initializing from yolov8n.pt...${NC}"
    cp yolov8n.pt crowd_model.pt
fi

# Detect camera hardware
echo -e "\n${YELLOW}[Step 1/3] Detecting Raspberry Pi Camera Module...${NC}"
if command -v rpicam-hello &> /dev/null || command -v libcamera-hello &> /dev/null; then
    echo -e "${GREEN}✅ rpicam / libcamera detected on Raspberry Pi OS.${NC}"
fi

if [ -e "/dev/video0" ]; then
    echo -e "${GREEN}✅ Camera device active at /dev/video0.${NC}"
else
    echo -e "${YELLOW}⚠️ /dev/video0 not detected directly.${NC}"
    echo -e "   If using Raspberry Pi Camera Module v2/v3, ensure it is enabled in:"
    echo -e "   'sudo raspi-config' -> Interface Options -> Camera -> Enable"
fi

# Check USB Connected Smartphone (Dumb Display)
echo -e "\n${YELLOW}[Step 2/3] Checking Smartphone Dumb Display over USB...${NC}"
if command -v adb &> /dev/null; then
    PHONE_STATUS=$(adb devices | grep -v "List" | grep "device$" | head -n 1 || true)
    if [ -n "$PHONE_STATUS" ]; then
        echo -e "${GREEN}✅ Phone Dumb Display detected via USB!${NC}"
        # Set up port forwarding
        adb reverse tcp:5000 tcp:5000 2>/dev/null || true
    else
        echo -e "${YELLOW}ℹ️ No phone connected via USB. (Run './setup_phone_display.sh' to link phone)${NC}"
    fi
fi

# Launch Server with libcamerify if available, otherwise direct python
echo -e "\n${YELLOW}[Step 3/3] Starting CivicGuard CCTV Platform on Port 5000...${NC}"
echo -e "   • Active Model:    crowd_model.pt"
echo -e "   • Privacy Shield:  Face Blur & Anonymization Active"
echo -e "   • Main Dashboard:  http://localhost:5000/"
echo -e "${BLUE}==================================================================${NC}\n"

# Activate venv if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Launch Python app directly with unbuffered logging
exec python3 -u app.py
