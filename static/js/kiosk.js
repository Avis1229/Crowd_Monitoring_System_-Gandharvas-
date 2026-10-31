/**
 * static/js/kiosk.js
 * Hardware Dumb Display Logic for Raspberry Pi 4 + Smartphone over USB
 * Real-time Telemetry Poller & Railway PIDS Status Engine
 */

let lastTicker = "";

function updateClock() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const formattedHours = String(hours % 12 || 12).padStart(2, '0');

    const clockElem = document.getElementById('pidsClock');
    if (clockElem) {
        clockElem.textContent = `${formattedHours}:${minutes}:${seconds} ${ampm}`;
    }

    const dateElem = document.getElementById('pidsDate');
    if (dateElem) {
        const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
        dateElem.textContent = now.toLocaleDateString('en-US', options).toUpperCase();
    }
}

async function fetchKioskStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();

        // 1. Update Occupancy & Capacity
        const occElem = document.getElementById('kioskOccupancy');
        const capElem = document.getElementById('kioskCapacity');
        const spotsElem = document.getElementById('availableSpots');
        
        if (occElem) occElem.innerHTML = `${data.occupancy}<span class="metric-slash">/</span><span class="metric-total">${data.capacity}</span>`;
        if (capElem) capElem.textContent = data.capacity;
        
        const remaining = Math.max(0, data.capacity - data.occupancy);
        if (spotsElem) {
            spotsElem.textContent = `${remaining.toLocaleString()} Entry Slots Available`;
        }

        // 2. Entries & Exits Flow
        const entElem = document.getElementById('kioskEntries');
        const exitElem = document.getElementById('kioskExits');
        if (entElem) entElem.textContent = (data.current_entries || 0).toLocaleString();
        if (exitElem) exitElem.textContent = (data.current_exits || 0).toLocaleString();

        // 3. Peak Alert & Weekly Baseline
        const peakElem = document.getElementById('kioskPeakAlert');
        if (peakElem && data.daily_update_alert) {
            peakElem.textContent = `⚠️ ${data.daily_update_alert}`;
        }

        const weeklyElem = document.getElementById('kioskWeekly');
        if (weeklyElem && data.weekly_average) {
            weeklyElem.textContent = data.weekly_average;
        }

        // 4. Congestion Gauge & Traffic Lights
        const ratio = data.capacity > 0 ? (data.occupancy / data.capacity) : 0;
        const percent = Math.min(100, Math.round(ratio * 100));

        const fillElem = document.getElementById('densityFill');
        const percentElem = document.getElementById('densityPercent');
        if (fillElem) fillElem.style.width = `${percent}%`;
        if (percentElem) percentElem.textContent = `${percent}% Capacity (${data.occupancy} in zone)`;

        const dotGreen = document.getElementById('dotGreen');
        const dotAmber = document.getElementById('dotAmber');
        const dotRed = document.getElementById('dotRed');
        const statusText = document.getElementById('statusText');
        const statusInstruction = document.getElementById('statusInstruction');
        const statusCard = document.getElementById('statusCard');

        // Reset lights
        [dotGreen, dotAmber, dotRed].forEach(d => d && d.classList.remove('active'));

        if (ratio >= 0.85 || data.alert_level === 'CRITICAL') {
            if (dotRed) dotRed.classList.add('active');
            if (statusText) {
                statusText.textContent = 'HIGH CONGESTION';
                statusText.className = 'status-main text-red';
            }
            if (statusInstruction) {
                statusInstruction.textContent = 'Entry restricted. Please hold or use alternate exit paths.';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #ffaa00, #ff334b)';
        } else if (ratio >= 0.60 || data.alert_level === 'WARNING') {
            if (dotAmber) dotAmber.classList.add('active');
            if (statusText) {
                statusText.textContent = 'MODERATE CROWD';
                statusText.className = 'status-main text-amber';
            }
            if (statusInstruction) {
                statusInstruction.textContent = 'Moderate footfall. Keep moving forward and avoid bottlenecks.';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #00f076, #ffaa00)';
        } else {
            if (dotGreen) dotGreen.classList.add('active');
            if (statusText) {
                statusText.textContent = 'NORMAL FLOW';
                statusText.className = 'status-main text-green';
            }
            if (statusInstruction) {
                statusInstruction.textContent = 'Safe for entry. Enjoy your visit with minimal wait time.';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #00f076, #ffd60a)';
        }

        // 5. Dynamic Ticker Marquee from Admin
        if (data.ticker_text && data.ticker_text !== lastTicker) {
            lastTicker = data.ticker_text;
            const tickerElem = document.getElementById('kioskTicker');
            if (tickerElem) {
                tickerElem.textContent = `${data.ticker_text}  • • •  ${data.ticker_text}`;
            }
        }

    } catch (e) {
        console.error("Kiosk poll failed:", e);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);

    fetchKioskStats();
    setInterval(fetchKioskStats, 1500);

    // Keep screen awake (WakeLock API for kiosk devices)
    if ('wakeLock' in navigator) {
        try {
            navigator.wakeLock.request('screen');
        } catch (err) {
            console.log("WakeLock error:", err);
        }
    }
});
