/**
 * CivicGuard Admin Console Controller
 * Manages live telemetry polling, dynamic ticker broadcasts, and camera/threshold controls
 */

document.addEventListener('DOMContentLoaded', () => {
    initAdminTelemetry();
    loadInitialValues();
});

// Load current configuration from backend
async function loadInitialValues() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();

        if (data.ticker_text) document.getElementById('inputTicker').value = data.ticker_text;
        if (data.daily_update_alert) document.getElementById('inputDailyAlert').value = data.daily_update_alert;
        if (data.accuracy) document.getElementById('inputAccuracy').value = parseInt(data.accuracy) || 87;
        if (data.capacity) document.getElementById('inputCapacity').value = data.capacity;
        if (data.weekly_average) document.getElementById('inputWeekly').value = data.weekly_average;
        if (data.warning_threshold) document.getElementById('inputWarning').value = data.warning_threshold;
        if (data.critical_threshold) document.getElementById('inputCritical').value = data.critical_threshold;
        if (data.privacy_mode) document.getElementById('selectPrivacy').value = data.privacy_mode;

        // Load initial custom zones from backend
        if (data.entry_zone) entryZone = data.entry_zone;
        if (data.exit_zone) exitZone = data.exit_zone;
        updateZoneSummaryLabel();
        drawCanvasZones();
    } catch (err) {
        console.warn('Initial admin sync waiting...', err);
    }
}

// Live telemetry polling for mini-monitor in admin panel
function initAdminTelemetry() {
    async function sync() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();

            const elHc = document.getElementById('miniHeadcount');
            const elIn = document.getElementById('miniIn');
            const elOut = document.getElementById('miniOut');
            const elStatus = document.getElementById('miniStatus');
            const elFps = document.getElementById('adminFps');

            if (elHc) elHc.textContent = data.headcount;
            if (elIn) elIn.textContent = data.current_entries;
            if (elOut) elOut.textContent = data.current_exits;
            if (elStatus) {
                elStatus.textContent = data.alert_level;
                elStatus.className = 'mini-stat-val ' + (
                    data.alert_level === 'CRITICAL' ? 'text-red' :
                        data.alert_level === 'WARNING' ? 'text-yellow' : 'text-green'
                );
            }
            if (elFps) elFps.textContent = `${data.fps} FPS`;

            // Threshold Alert Box State (Turns Red when Warning Threshold is Reached)
            const cardThresh = document.getElementById('cardThresholds');
            const bannerThresh = document.getElementById('thresholdAlertBanner');
            const badgeThresh = document.getElementById('thresholdLiveBadge');
            const inputWarn = document.getElementById('inputWarning');

            if (data.threshold_exceeded || data.alert_level === 'WARNING' || data.alert_level === 'CRITICAL') {
                if (cardThresh) cardThresh.classList.add('card-threshold-red');
                if (bannerThresh) {
                    bannerThresh.style.display = 'flex';
                    bannerThresh.innerHTML = `⚠️ <strong>WARNING ALERT:</strong> Crowd Threshold Limit (${data.warning_threshold}) Reached! Current Occupancy: <strong>${data.occupancy}</strong> (Headcount: ${data.headcount})`;
                }
                if (badgeThresh) {
                    badgeThresh.textContent = data.is_critical ? '🚨 CRITICAL BREACH' : '🔴 ⚠️ WARNING ACTIVE';
                    badgeThresh.style.background = 'rgba(239, 68, 68, 0.25)';
                    badgeThresh.style.color = '#f87171';
                }
                if (inputWarn) inputWarn.classList.add('input-warning-red');
            } else {
                if (cardThresh) cardThresh.classList.remove('card-threshold-red');
                if (bannerThresh) bannerThresh.style.display = 'none';
                if (badgeThresh) {
                    badgeThresh.textContent = '🟢 NORMAL FLOW';
                    badgeThresh.style.background = 'rgba(16, 185, 129, 0.2)';
                    badgeThresh.style.color = '#34d399';
                }
                if (inputWarn) inputWarn.classList.remove('input-warning-red');
            }

            // Sync active zones from backend if not actively dragging
            if (!isDrawing) {
                let changed = false;
                if (JSON.stringify(entryZone) !== JSON.stringify(data.entry_zone)) {
                    entryZone = data.entry_zone;
                    changed = true;
                }
                if (JSON.stringify(exitZone) !== JSON.stringify(data.exit_zone)) {
                    exitZone = data.exit_zone;
                    changed = true;
                }
                if (changed) {
                    updateZoneSummaryLabel();
                    drawCanvasZones();
                }
            }
        } catch (e) { }
    }

    sync();
    setInterval(sync, 1000);
}

// Fast Presets for Ticker
function setTickerPreset(text) {
    document.getElementById('inputTicker').value = text;
}

// Broadcast Ticker to Public Display
async function updateTicker() {
    const text = document.getElementById('inputTicker').value.trim();
    const feedback = document.getElementById('tickerFeedback');

    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker_text: text })
        });

        if (res.ok) {
            feedback.textContent = '✅ Broadcasted to Public Screen!';
            setTimeout(() => { feedback.textContent = ''; }, 3000);
        }
    } catch (err) {
        alert('Failed to update ticker: ' + err);
    }
}

// Update Daily Alert and Accuracy in HUD
async function updateHUDMeta() {
    const dailyAlert = document.getElementById('inputDailyAlert').value.trim();
    const accuracy = document.getElementById('inputAccuracy').value.trim() + '%';
    const weekly = document.getElementById('inputWeekly').value.trim();
    const feedback = document.getElementById('hudFeedback');

    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                daily_update_alert: dailyAlert,
                accuracy: accuracy,
                weekly_average: weekly
            })
        });

        if (res.ok) {
            feedback.textContent = '✅ HUD Data Updated!';
            setTimeout(() => { feedback.textContent = ''; }, 3000);
        }
    } catch (err) {
        alert('Failed to update HUD: ' + err);
    }
}

// Update Capacity and Alert Thresholds
async function updateThresholds() {
    const cap = parseInt(document.getElementById('inputCapacity').value) || 2000;
    const warn = parseInt(document.getElementById('inputWarning').value) || 30;
    const crit = parseInt(document.getElementById('inputCritical').value) || 45;

    try {
        const res = await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                capacity: cap,
                warning_threshold: warn,
                critical_threshold: crit
            })
        });

        if (res.ok) {
            const fb = document.getElementById('thresholdFeedback');
            if (fb) {
                fb.textContent = '✅ Thresholds Saved & Active!';
                setTimeout(() => { fb.textContent = ''; }, 3000);
            } else {
                alert('✅ Capacity & Alarm Thresholds Updated!');
            }
        }
    } catch (err) {
        alert('Failed: ' + err);
    }
}

// Reset In/Out Counters
async function resetCounts() {
    if (!confirm('Are you sure you want to reset the In/Out footfall counters to zero?')) return;

    try {
        const res = await fetch('/api/admin/reset_counts', { method: 'POST' });
        if (res.ok) {
            alert('✅ Footfall counters reset to 0!');
        }
    } catch (err) {
        alert('Failed to reset: ' + err);
    }
}

// Video Source Switcher
function toggleCustomUrl(val) {
    const group = document.getElementById('groupCustomUrl');
    group.style.display = (val === 'custom') ? 'block' : 'none';
}

async function changeVideoSource() {
    const sel = document.getElementById('selectSource').value;
    let finalSource = sel;

    if (sel === 'custom') {
        finalSource = document.getElementById('inputCustomUrl').value.trim();
        if (!finalSource) {
            alert('Please enter a valid Raspberry Pi or RTSP stream URL');
            return;
        }
    }

    const feedback = document.getElementById('sourceFeedback');
    feedback.textContent = 'Switching source...';

    try {
        const res = await fetch('/api/admin/change_source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: finalSource })
        });

        if (res.ok) {
            feedback.textContent = '✅ Stream Source Switched!';
            // Refresh preview
            setTimeout(() => {
                document.getElementById('adminPreviewImg').src = '/video_feed?t=' + new Date().getTime();
                feedback.textContent = '';
            }, 1500);
        }
    } catch (err) {
        alert('Error switching source: ' + err);
    }
}

// Change Privacy Anonymization Mode
async function changePrivacyMode(mode) {
    try {
        await fetch('/api/admin/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ privacy_mode: mode })
        });
    } catch (err) {
        console.error('Error changing privacy mode', err);
    }
}

// Fetch Raspberry Pi 4 Hardware Health Telemetry
async function fetchSystemHealth() {
    try {
        const res = await fetch('/api/system/health');
        if (!res.ok) return;
        const data = await res.json();

        const elPlatform = document.getElementById('hwPlatform');
        const elCamera = document.getElementById('hwCamera');
        const elDisplay = document.getElementById('hwDisplay');
        const elTemp = document.getElementById('hwTemp');
        const elRam = document.getElementById('hwRam');

        if (elPlatform) elPlatform.textContent = data.hardware_platform;
        if (elCamera) elCamera.textContent = data.camera_sensor;
        if (elDisplay) elDisplay.textContent = data.display_output;
        if (elTemp) elTemp.textContent = data.cpu_temperature;
        if (elRam) elRam.textContent = data.ram_usage;
    } catch (e) {
        console.error("Hardware health poll failed", e);
    }
}

// Fetch 36-Hour Ground Truth Benchmark Evidence Metrics
async function fetchEvidenceMetrics() {
    try {
        const res = await fetch('/api/evidence/metrics');
        if (!res.ok) return;
        const data = await res.json();

        const elMae = document.getElementById('metricMAE');
        const elRmse = document.getElementById('metricRMSE');
        const elAcc = document.getElementById('metricAcc');
        const elF1 = document.getElementById('metricF1');

        if (elMae) elMae.textContent = data.mae;
        if (elRmse) elRmse.textContent = data.rmse;
        if (elAcc) elAcc.textContent = `${data.accuracy_pct}%`;
        if (elF1) elF1.textContent = `${data.alert_f1}%`;
    } catch (e) {
        console.error("Evidence metrics poll failed", e);
    }
}

// Initialize health & metrics and interactive zone drawer
document.addEventListener('DOMContentLoaded', () => {
    fetchSystemHealth();
    fetchEvidenceMetrics();
    setInterval(fetchSystemHealth, 5000);
    initZoneDrawer();
});

// ============================================================================
// Interactive Entry/Exit Zone Drawer
// ============================================================================
let activeDrawMode = null; // 'entry' | 'exit' | null
let entryZone = null;      // [x1, y1, x2, y2] normalized 0.0 - 1.0
let exitZone = null;       // [x1, y1, x2, y2] normalized 0.0 - 1.0
let isDrawing = false;
let drawStartX = 0;
let drawStartY = 0;
let currentDragBox = null;

function initZoneDrawer() {
    const canvas = document.getElementById('zoneCanvas');
    const container = document.getElementById('previewContainer');
    const img = document.getElementById('adminPreviewImg');
    if (!canvas || !container) return;

    // Resize canvas to match container's rendered size
    function syncCanvasSize() {
        if (canvas.clientWidth && canvas.clientHeight) {
            canvas.width = canvas.clientWidth;
            canvas.height = canvas.clientHeight;
            drawCanvasZones();
        }
    }

    syncCanvasSize();
    window.addEventListener('resize', syncCanvasSize);
    if (img) img.addEventListener('load', syncCanvasSize);

    function getCoords(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: Math.max(0, Math.min(canvas.width, clientX - rect.left)),
            y: Math.max(0, Math.min(canvas.height, clientY - rect.top))
        };
    }

    function onPointerDown(e) {
        if (!activeDrawMode) return;
        e.preventDefault();
        const pt = getCoords(e);
        isDrawing = true;
        drawStartX = pt.x;
        drawStartY = pt.y;
        currentDragBox = { x: pt.x, y: pt.y, w: 0, h: 0 };
    }

    function onPointerMove(e) {
        if (!isDrawing || !activeDrawMode) return;
        e.preventDefault();
        const pt = getCoords(e);
        const x = Math.min(drawStartX, pt.x);
        const y = Math.min(drawStartY, pt.y);
        const w = Math.abs(pt.x - drawStartX);
        const h = Math.abs(pt.y - drawStartY);
        currentDragBox = { x, y, w, h };
        drawCanvasZones();
    }

    function onPointerUp(e) {
        if (!isDrawing || !activeDrawMode) return;
        isDrawing = false;

        if (currentDragBox && currentDragBox.w > 15 && currentDragBox.h > 15) {
            const x1 = Math.max(0, Math.min(1, currentDragBox.x / canvas.width));
            const y1 = Math.max(0, Math.min(1, currentDragBox.y / canvas.height));
            const x2 = Math.max(0, Math.min(1, (currentDragBox.x + currentDragBox.w) / canvas.width));
            const y2 = Math.max(0, Math.min(1, (currentDragBox.y + currentDragBox.h) / canvas.height));

            const normalizedBox = [
                parseFloat(x1.toFixed(3)),
                parseFloat(y1.toFixed(3)),
                parseFloat(x2.toFixed(3)),
                parseFloat(y2.toFixed(3))
            ];

            const instr = document.getElementById('drawInstructions');
            if (activeDrawMode === 'entry') {
                entryZone = normalizedBox;
                if (instr) instr.innerHTML = '✅ <strong>Entry Zone Saved!</strong> Now click "Draw Exit Box" or test people passing through.';
            } else if (activeDrawMode === 'exit') {
                exitZone = normalizedBox;
                if (instr) instr.innerHTML = '✅ <strong>Exit Zone Saved!</strong> System will count exits when people walk into this red zone.';
            }

            saveZonesToServer();
        } else {
            const instr = document.getElementById('drawInstructions');
            if (instr) instr.innerHTML = '⚠️ Box too small, click and drag a larger rectangular area on the video.';
        }

        currentDragBox = null;
        setZoneDrawMode(null); // finish current drawing pass
        drawCanvasZones();
    }

    canvas.addEventListener('mousedown', onPointerDown);
    canvas.addEventListener('mousemove', onPointerMove);
    canvas.addEventListener('mouseup', onPointerUp);
    canvas.addEventListener('mouseleave', () => {
        if (isDrawing) {
            isDrawing = false;
            currentDragBox = null;
            drawCanvasZones();
        }
    });

    // Touch support for mobile/tablets
    canvas.addEventListener('touchstart', onPointerDown, { passive: false });
    canvas.addEventListener('touchmove', onPointerMove, { passive: false });
    canvas.addEventListener('touchend', onPointerUp, { passive: false });
}

function setZoneDrawMode(mode) {
    if (activeDrawMode === mode) {
        activeDrawMode = null;
    } else {
        activeDrawMode = mode;
    }

    const btnEntry = document.getElementById('btnModeEntry');
    const btnExit = document.getElementById('btnModeExit');
    const instr = document.getElementById('drawInstructions');

    if (btnEntry) btnEntry.classList.toggle('active', activeDrawMode === 'entry');
    if (btnExit) btnExit.classList.toggle('active', activeDrawMode === 'exit');

    if (instr) {
        if (activeDrawMode === 'entry') {
            instr.innerHTML = '🟢 <strong>ENTRY DRAW MODE:</strong> Drag your mouse across video to draw the Entry Area box.';
            instr.style.borderColor = '#22c55e';
            instr.style.color = '#4ade80';
        } else if (activeDrawMode === 'exit') {
            instr.innerHTML = '🔴 <strong>EXIT DRAW MODE:</strong> Drag your mouse across video to draw the Exit Area box.';
            instr.style.borderColor = '#ef4444';
            instr.style.color = '#f87171';
        } else {
            instr.innerHTML = '👆 Select "Draw Entry Box" or "Draw Exit Box" above, then drag across video.';
            instr.style.borderColor = 'rgba(59, 130, 246, 0.4)';
            instr.style.color = '#93c5fd';
        }
    }
}

function drawCanvasZones() {
    const canvas = document.getElementById('zoneCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    function drawBox(zone, color, fillColor, label) {
        if (!zone || zone.length !== 4) return;
        const x = zone[0] * canvas.width;
        const y = zone[1] * canvas.height;
        const w = (zone[2] - zone[0]) * canvas.width;
        const h = (zone[3] - zone[1]) * canvas.height;

        // Semi-transparent fill
        ctx.fillStyle = fillColor;
        ctx.fillRect(x, y, w, h);

        // Border
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.setLineDash([]);
        ctx.strokeRect(x, y, w, h);

        // Corner accents
        const cLen = Math.min(16, w / 4, h / 4);
        ctx.lineWidth = 4;
        ctx.beginPath();
        // Top-left
        ctx.moveTo(x, y + cLen); ctx.lineTo(x, y); ctx.lineTo(x + cLen, y);
        // Top-right
        ctx.moveTo(x + w - cLen, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + cLen);
        // Bottom-right
        ctx.moveTo(x + w, y + h - cLen); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - cLen, y + h);
        // Bottom-left
        ctx.moveTo(x + cLen, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - cLen);
        ctx.stroke();

        // Label pill
        ctx.font = 'bold 11px system-ui, sans-serif';
        const txtWidth = ctx.measureText(label).width;
        const pillH = 20;
        const pillW = txtWidth + 14;
        const pillX = x + 4;
        const pillY = Math.max(2, y - pillH - 4);

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(pillX, pillY, pillW, pillH, 4);
        ctx.fill();

        ctx.fillStyle = '#000000';
        ctx.fillText(label, pillX + 7, pillY + 14);
    }

    // Render Entry Zone
    if (entryZone) {
        drawBox(entryZone, '#22c55e', 'rgba(34, 197, 94, 0.22)', 'ENTRY ZONE (IN)');
    }

    // Render Exit Zone
    if (exitZone) {
        drawBox(exitZone, '#ef4444', 'rgba(239, 68, 68, 0.22)', 'EXIT ZONE (OUT)');
    }

    // Render Active Drag Box
    if (isDrawing && currentDragBox) {
        const color = activeDrawMode === 'entry' ? '#22c55e' : '#ef4444';
        const fill = activeDrawMode === 'entry' ? 'rgba(34, 197, 94, 0.28)' : 'rgba(239, 68, 68, 0.28)';

        ctx.fillStyle = fill;
        ctx.fillRect(currentDragBox.x, currentDragBox.y, currentDragBox.w, currentDragBox.h);

        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(currentDragBox.x, currentDragBox.y, currentDragBox.w, currentDragBox.h);
        ctx.setLineDash([]);
    }
}

async function saveZonesToServer() {
    try {
        const res = await fetch('/api/admin/set_zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entry_zone: entryZone,
                exit_zone: exitZone,
                zones_enabled: Boolean(entryZone || exitZone)
            })
        });

        if (res.ok) {
            updateZoneSummaryLabel();
        }
    } catch (err) {
        console.error('Failed to save zones to server', err);
    }
}

function updateZoneSummaryLabel() {
    const lbl = document.getElementById('zoneSummaryLabel');
    if (!lbl) return;

    if (entryZone && exitZone) {
        lbl.innerHTML = '<span style="color:#22c55e;">🟩 Entry</span> & <span style="color:#ef4444;">🟥 Exit</span> Active';
    } else if (entryZone) {
        lbl.innerHTML = '<span style="color:#22c55e;">🟩 Entry Active</span> (Tripwire for Exit)';
    } else if (exitZone) {
        lbl.innerHTML = '<span style="color:#ef4444;">🟥 Exit Active</span> (Tripwire for Entry)';
    } else {
        lbl.textContent = 'None (Using standard tripwire)';
    }
}

async function clearZones() {
    entryZone = null;
    exitZone = null;
    activeDrawMode = null;
    currentDragBox = null;

    setZoneDrawMode(null);
    drawCanvasZones();

    const instr = document.getElementById('drawInstructions');
    if (instr) instr.innerHTML = '🗑️ Boxes cleared! Reverted to standard tripwire line.';

    try {
        await fetch('/api/admin/set_zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entry_zone: null,
                exit_zone: null,
                zones_enabled: false
            })
        });
        updateZoneSummaryLabel();
    } catch (err) {
        console.error('Failed to clear zones on server', err);
    }
}

function applyPresetZones(preset) {
    if (preset === 'split_vertical') {
        // Left half Entry, Right half Exit
        entryZone = [0.05, 0.15, 0.45, 0.85];
        exitZone = [0.55, 0.15, 0.95, 0.85];
    } else if (preset === 'split_horizontal') {
        // Top half Entry, Bottom half Exit
        entryZone = [0.15, 0.05, 0.85, 0.45];
        exitZone = [0.15, 0.55, 0.85, 0.95];
    } else if (preset === 'center_gate') {
        // Two side-by-side turnstiles in the center
        entryZone = [0.15, 0.35, 0.48, 0.70];
        exitZone = [0.52, 0.35, 0.85, 0.70];
    }

    setZoneDrawMode(null);
    drawCanvasZones();
    saveZonesToServer();

    const instr = document.getElementById('drawInstructions');
    if (instr) instr.innerHTML = `⚡ Preset applied: <strong>${preset}</strong>! Both Entry and Exit zones are active.`;
}

