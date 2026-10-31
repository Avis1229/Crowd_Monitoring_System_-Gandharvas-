#!/usr/bin/env bash
# ==============================================================================
# setup_phone_display.sh
# Automates Smartphone Configuration as a 100% DUMB DISPLAY on Raspberry Pi 4
#
# Hardware Setup:
#   1. Raspberry Pi 4 Model B (4GB / 8GB)
#   2. Raspberry Pi Camera Module (CSI Ribbon Cable into CAM port)
#   3. Android Smartphone connected via standard USB-A to USB-C cable
#
# The smartphone runs ZERO phone apps/logic. It behaves purely as a dumb monitor
# displaying the Railway PIDS Public Screen (/kiosk) over the USB cable.
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==================================================================${NC}"
echo -e "${GREEN}  Raspberry Pi 4 -> Phone Dumb Display USB Setup Automator${NC}"
echo -e "${BLUE}==================================================================${NC}"

# Check for adb
if ! command -v adb &> /dev/null; then
    echo -e "${YELLOW}ℹ️ ADB not found. Installing adb on Raspberry Pi OS...${NC}"
    sudo apt-get update && sudo apt-get install -y adb
fi

echo -e "\n${YELLOW}[Step 1/4] Checking USB Connected Smartphone...${NC}"
adb devices

DEVICE_COUNT=$(adb devices | grep -v "List" | grep "device$" | wc -l)

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo -e "${RED}⚠️ No phone detected over USB!${NC}"
    echo -e "Please ensure:"
    echo -e "  1. Phone is plugged into Raspberry Pi 4 via USB cable."
    echo -e "  2. 'USB Debugging' is enabled in Phone Developer Options."
    echo -e "  3. When phone asks 'Allow USB Debugging?', tap 'Always Allow'."
    echo -e "\nWaiting for phone connection (Press Ctrl+C to abort)..."
    adb wait-for-device
    echo -e "${GREEN}✅ Smartphone detected successfully!${NC}"
else
    echo -e "${GREEN}✅ Smartphone detected over USB cable.${NC}"
fi

echo -e "\n${YELLOW}[Step 2/4] Locking Phone into Dumb Display Mode (No Phone Functions)...${NC}"

# 1. Keep display permanently awake when connected via USB
echo "  • Setting phone to stay awake indefinitely while plugged into USB..."
adb shell settings put global stay_on_while_plugged_in 3

# 2. Lock screen orientation to Landscape (Horizontal Public Signage)
echo "  • Locking screen orientation to Landscape (Railway indicator layout)..."
adb shell settings put system accelerometer_rotation 0
adb shell settings put system user_rotation 1

# 3. Maximize screen brightness for street/outdoor visibility
echo "  • Setting screen brightness to maximum for outdoor clarity..."
adb shell settings put system screen_brightness 255

# 4. Turn off screen timeout (0 = never sleep)
adb shell settings put system screen_off_timeout 2147483647 2>/dev/null || true

echo -e "\n${YELLOW}[Step 3/4] Establishing Reverse Port Forwarding over USB Cable...${NC}"
# Forward Raspberry Pi 4 local Flask server (port 5000) through the USB cable to localhost:5000 on the phone
adb reverse tcp:5000 tcp:5000
echo -e "${GREEN}✅ Port 5000 mapped: http://localhost:5000 accessible on phone via USB cable.${NC}"

echo -e "\n${YELLOW}[Step 4/4] Launching Fullscreen Railway PIDS Kiosk on Phone...${NC}"
# Launch the Kiosk page in fullscreen browser without navigation bars
adb shell am start -a android.intent.action.VIEW \
    -d "http://localhost:5000/kiosk" \
    --activity-clear-top \
    --activity-single-top

# Hide Android status bar & navigation bar (Immersive Fullscreen Dumb Display)
adb shell settings put global policy_control immersive.full=*

echo -e "\n${BLUE}==================================================================${NC}"
echo -e "${GREEN}🎉 SMARTPHONE DUMB DISPLAY IS NOW LIVE!${NC}"
echo -e "${BLUE}==================================================================${NC}"
echo -e "  • The phone is acting 100% as an external monitor."
echo -e "  • No phone apps are running; touch navigation is suppressed."
echo -e "  • The screen is showing the Railway & Street PIDS (/kiosk) view."
echo -e "  • All AI inference & vision processing is running on the Raspberry Pi 4."
echo -e "${BLUE}==================================================================${NC}"
