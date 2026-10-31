/**
 * static/js/dashboard.js
 * CivicGuard Live CCTV Surveillance Controller & Slide-Over Admin Drawer
 * Replicates the exact municipal CCTV telemetry layout from the reference image.
 */

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    startTelemetryPolling();
    initShortcuts();
    syncDrawerFields();
    startHardwareHealthPolling();
    initStreamMonitor();
});

// -----------------------------------------------------------------------------
// 1. Digital Clock (08:56 pm format)
// -----------------------------------------------------------------------------
function initClock() {
    const clockEl = document.getElementById('digitalClock');
    
    function updateTime() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const ampm = hours >= 12 ? 'pm' : 'am';
        hours = hours % 12;
        hours = hours ? String(hours).padStart(2, '0') : '12';
        if (clockEl) clockEl.textContent = `${hours}:${minutes} ${ampm}`;
    }
    
    updateTime();
    setInterval(updateTime, 1000);
}

// -----------------------------------------------------------------------------
// 2. Real-time Telemetry Poller (Yellow HUD & Blue Ticker)
// -----------------------------------------------------------------------------
let currentTicker = "";

function startTelemetryPolling() {
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            
            // Update Yellow HUD values (matching reference image)
            const elEntries = document.getElementById('statEntries');
            const elExits = document.getElementById('statExits');
            const elOccupancy = document.getElementById('statOccupancy');
            const elAccuracy = document.getElementById('statAccuracy');
            const elDailyAlert = document.getElementById('dailyUpdateAlert');
            const elWeekly = document.getElementById('statWeekly');
            const elTicker = document.getElementById('tickerText');
            const elTickerDup = document.getElementById('tickerTextDup');
            const elLiveHeadcount = document.getElementById('statLiveHeadcount');
            
            if (elLiveHeadcount) elLiveHeadcount.textContent = data.headcount;
            if (elEntries) elEntries.textContent = data.current_entries;
            if (elExits) elExits.textContent = data.current_exits;
            if (elOccupancy) elOccupancy.textContent = `${data.occupancy}/${data.capacity}`;
            if (elAccuracy) elAccuracy.textContent = data.accuracy.includes('%') ? data.accuracy : `${data.accuracy} %`;
            if (elDailyAlert) elDailyAlert.textContent = data.daily_update_alert;
            
            // Sync radio button in admin drawer if not active user change
            const radioLive = document.getElementById('modeLiveRealtime');
            const radioShift = document.getElementById('modeShiftBaseline');
            if (radioLive && radioShift && document.activeElement !== radioLive && document.activeElement !== radioShift) {
                if (data.counter_mode === 'shift_baseline') {
                    radioShift.checked = true;
                } else {
                    radioLive.checked = true;
                }
            }
            
            if (elWeekly && data.weekly_average) {
                elWeekly.innerHTML = `approx<br><span class="weekly-range">${data.weekly_average}</span><br>Per day`;
            }
            
            // Dynamic Ticker update from Admin Panel
            if (data.ticker_text && data.ticker_text !== currentTicker) {
                currentTicker = data.ticker_text;
                if (elTicker) elTicker.textContent = currentTicker;
                if (elTickerDup) elTickerDup.textContent = currentTicker;
            }
            
            // Threshold Alert in Yellow HUD (Occupancy Box turns Red)
            const cellOcc = document.getElementById('cellOccupancy');
            const occLabel = document.getElementById('occupancyLabel');
            const warnPill = document.getElementById('occupancyWarningPill');
            
            if (data.threshold_exceeded || data.alert_level === 'WARNING' || data.alert_level === 'CRITICAL') {
                if (cellOcc) cellOcc.classList.add('threshold-warning-red');
                if (occLabel) occLabel.textContent = data.is_critical ? '🚨 CRITICAL BREACH' : '⚠️ CROWD WARNING';
                if (warnPill) {
                    warnPill.style.display = 'block';
                    warnPill.textContent = `LIMIT: ${data.warning_threshold}`;
                }
            } else {
                if (cellOcc) cellOcc.classList.remove('threshold-warning-red');
                if (occLabel) occLabel.textContent = 'Live Occupancy';
                if (warnPill) warnPill.style.display = 'none';
            }
            
            // Critical Overcrowding visual hint on HUD border
            const hud = document.getElementById('telemetryHud');
            if (hud) {
                if (data.alert_level === 'CRITICAL' || data.threshold_exceeded) {
                    hud.style.borderColor = '#d32f2f';
                    hud.style.boxShadow = '0 0 25px rgba(211, 47, 47, 0.75), 0 10px 30px rgba(0, 0, 0, 0.65)';
                } else if (data.alert_level === 'WARNING') {
                    hud.style.borderColor = '#f59e0b';
                    hud.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.65), 0 10px 30px rgba(0, 0, 0, 0.65)';
                } else {
                    hud.style.borderColor = '#141414';
                    hud.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.15) inset';
                }
            }
        } catch (err) {
            console.warn('[CCTV Dashboard] Telemetry sync waiting...', err);
        }
    }
    
    fetchStats();
    setInterval(fetchStats, 1000);
}

// -----------------------------------------------------------------------------
// 3. Slide-Over Admin Drawer & Controller
// -----------------------------------------------------------------------------
function toggleAdminDrawer() {
    const drawer = document.getElementById('adminDrawer');
    const backdrop = document.getElementById('drawerBackdrop');
    if (drawer && backdrop) {
        drawer.classList.toggle('open');
        backdrop.classList.toggle('open');
    }
}

// Sync initial values into the drawer inputs
async function syncDrawerFields() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        
        const inpTicker = document.getElementById('drawerInputTicker');
        const inpAlert = document.getElementById('drawerInputAlert');
        const inpAcc = document.getElementById('drawerInputAccuracy');
        const inpCap = document.getElementById('drawerInputCapacity');
        const inpWk = document.getElementById('drawerInputWeekly');
        const inpWarn = document.getElementById('drawerInputWarning');
        const inpCrit = document.getElementById('drawerInputCritical');
        const selPrivacy = document.getElementById('drawerSelectPrivacy');
        const selSource = document.getElementById('drawerSelectSource');
        
        if (inpTicker && data.ticker_text) inpTicker.value = data.ticker_text;
        if (inpAlert && data.daily_update_alert) inpAlert.value = data.daily_update_alert;
        if (inpAcc && data.accuracy) inpAcc.value = parseInt(data.accuracy) || 87;
        if (inpCap && data.capacity) inpCap.value = data.capacity;
        if (inpWk && data.weekly_average) inpWk.value = data.weekly_average;
        if (inpWarn && data.warning_threshold) inpWarn.value = data.warning_threshold;
        if (inpCrit && data.critical_threshold) inpCrit.value = data.critical_threshold;
        if (selPrivacy && data.privacy_mode) selPrivacy.value = data.privacy_mode;
        if (selSource && data.video_source) selSource.value = data.video_source;
    } catch (e) {
        console.warn("Drawer sync error:", e);
    }
}

function setDrawerTicker(text) {
    const el = document.getElementById('drawerInputTicker');
    if (el) el.value = text;
}

async function broadcastDrawerTicker() {
    const text = document.getElementById('drawerInputTicker').value.trim();
    const status = document.getElementById('drawerTickerStatus');
    
    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker_text: text })
        });
        
        if (res.ok) {
            if (status) {
                status.textContent = '✅ Broadcasted to Blue Ticker!';
                setTimeout(() => { status.textContent = ''; }, 2500);
            }
        }
    } catch (err) {
        alert('Failed to update ticker: ' + err);
    }
}

async function updateDrawerHUD() {
    const alertText = document.getElementById('drawerInputAlert').value.trim();
    const acc = document.getElementById('drawerInputAccuracy').value.trim() + ' %';
    const cap = parseInt(document.getElementById('drawerInputCapacity').value) || 2000;
    const weekly = document.getElementById('drawerInputWeekly').value.trim();
    const warn = parseInt(document.getElementById('drawerInputWarning')?.value) || 30;
    const crit = parseInt(document.getElementById('drawerInputCritical')?.value) || 45;
    const status = document.getElementById('drawerHUDStatus');
    
    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                daily_update_alert: alertText,
                accuracy: acc,
                capacity: cap,
                weekly_average: weekly,
                warning_threshold: warn,
                critical_threshold: crit
            })
        });
        
        if (res.ok) {
            if (status) {
                status.textContent = '✅ Yellow HUD & Thresholds Updated!';
                setTimeout(() => { status.textContent = ''; }, 2500);
            }
        }
    } catch (err) {
        alert('Failed to update HUD: ' + err);
    }
}

async function changeDrawerSource(src) {
    try {
        await fetch('/api/admin/change_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: src })
        });
        
        // Refresh video stream
        setTimeout(() => {
            const feed = document.getElementById('videoFeed');
            if (feed) feed.src = '/video_feed?t=' + new Date().getTime();
        }, 1200);
    } catch (err) {
        console.error("Source switch failed:", err);
    }
}

async function changeDrawerPrivacy(mode) {
    try {
        await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ privacy_mode: mode })
        });
    } catch (err) {
        console.error("Privacy switch failed:", err);
    }
}

async function setCounterMode(mode) {
    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ counter_mode: mode })
        });
        const status = document.getElementById('drawerCounterStatus');
        if (status) {
            status.textContent = mode === 'live_realtime' ? '✅ Switched to Live Real-Time Counting' : '✅ Switched to Municipal Baseline Mode';
            status.style.color = '#4ade80';
            setTimeout(() => { status.textContent = ''; }, 3500);
        }
    } catch(err) {
        console.error('Failed to change counter mode:', err);
    }
}

async function resetLiveCounters() {
    try {
        await fetch('/api/admin/reset_counts', { method: 'POST' });
        const status = document.getElementById('drawerCounterStatus');
        if (status) {
            status.textContent = '🔄 Live Tripwire Counters reset to 0!';
            status.style.color = '#facc15';
            setTimeout(() => { status.textContent = ''; }, 3500);
        }
    } catch (e) {
        console.error('Error resetting counters:', e);
    }
}

async function resetDrawerCounts() {
    return resetLiveCounters();
}

// -----------------------------------------------------------------------------
// 4. Raspberry Pi 4 Hardware Health Telemetry
// -----------------------------------------------------------------------------
function startHardwareHealthPolling() {
    async function fetchHealth() {
        try {
            const res = await fetch('/api/system/health');
            if (!res.ok) return;
            const data = await res.json();
            
            const elTemp = document.getElementById('dTelTemp');
            const elRam = document.getElementById('dTelRam');
            const elFps = document.getElementById('dTelFps');
            
            if (elTemp) elTemp.textContent = data.cpu_temperature;
            if (elRam) elRam.textContent = data.ram_usage;
            if (elFps) elFps.textContent = data.inference_fps;
        } catch (e) {}
    }
    
    fetchHealth();
    setInterval(fetchHealth, 4000);
}

// -----------------------------------------------------------------------------
// 5. Dumb Display Lock Mode (For Phone Screen via USB on Street)
// -----------------------------------------------------------------------------
function toggleDumbDisplayMode() {
    document.body.classList.toggle('dumb-display-mode');
    toggleAdminDrawer(); // Close drawer
    
    const isLocked = document.body.classList.contains('dumb-display-mode');
    if (isLocked) {
        // Request browser fullscreen for pure dumb display
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(() => {});
        }
        console.log("Dumb display mode locked. Press 'A' or ESC to unlock.");
    }
}

// -----------------------------------------------------------------------------
// 6. Keyboard Shortcuts & Video Fallback
// -----------------------------------------------------------------------------
function initShortcuts() {
    window.addEventListener('keydown', (e) => {
        // 'A' toggles Admin Drawer (only if not typing in text input)
        if ((e.key === 'a' || e.key === 'A') && !e.ctrlKey && !e.metaKey && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            toggleAdminDrawer();
        }
        // 'ESC' closes Admin Drawer or unlocks Dumb Display
        if (e.key === 'Escape') {
            const drawer = document.getElementById('adminDrawer');
            if (drawer && drawer.classList.contains('open')) {
                toggleAdminDrawer();
            } else if (document.body.classList.contains('dumb-display-mode')) {
                document.body.classList.remove('dumb-display-mode');
            }
        }
    });
}

// -----------------------------------------------------------------------------
// 7. Bulletproof CCTV Stream Watchdog & Seamless Snapshot Fallback
// -----------------------------------------------------------------------------
let streamFallbackTimer = null;
let streamFallbackActive = false;

function initStreamMonitor() {
    const feed = document.getElementById('videoFeed');
    if (!feed) return;

    let receivedFrame = false;

    feed.onload = () => {
        receivedFrame = true;
        // If snapshot fallback was running and MJPEG recovered, we can keep it or leave it smooth
        const fallback = document.getElementById('streamFallback');
        if (fallback) fallback.style.display = 'none';
    };

    feed.onerror = () => {
        console.warn('[CCTV Feed] Direct MJPEG stream failed. Activating snapshot streamer...');
        activateSnapshotStream();
    };

    // Watchdog: If browser hasn't rendered a video frame within 2 seconds, activate snapshot stream
    setTimeout(() => {
        if (!receivedFrame || !feed.naturalWidth || feed.naturalWidth === 0) {
            console.log('[CCTV Feed] Video canvas blank after 2s. Switching to instant snapshot stream...');
            activateSnapshotStream();
        }
    }, 2000);
}

function activateSnapshotStream() {
    if (streamFallbackActive) return;
    streamFallbackActive = true;

    const feed = document.getElementById('videoFeed');
    const fallback = document.getElementById('streamFallback');
    if (fallback) fallback.style.display = 'none';
    if (!feed) return;

    let inFlight = false;
    const bufferImg = new Image();

    streamFallbackTimer = setInterval(() => {
        if (inFlight) return;
        inFlight = true;

        const nextUrl = '/api/snapshot?t=' + Date.now();
        bufferImg.onload = () => {
            feed.src = nextUrl;
            inFlight = false;
        };
        bufferImg.onerror = () => {
            inFlight = false;
        };
        bufferImg.src = nextUrl;
    }, 180); // ~5.5 FPS smooth live video stream
}

function handleStreamError(img) {
    activateSnapshotStream();
}

function retryStream() {
    const feed = document.getElementById('videoFeed');
    if (feed) feed.src = '/video_feed?t=' + Date.now();
    const fallback = document.getElementById('streamFallback');
    if (fallback) fallback.style.display = 'none';
    setTimeout(() => {
        if (!feed.naturalWidth || feed.naturalWidth === 0) {
            activateSnapshotStream();
        }
    }, 1500);
}
