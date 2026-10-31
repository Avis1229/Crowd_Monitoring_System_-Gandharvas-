/**
 * static/js/public.js
 * Remote Citizen Crowd Status Website Logic
 * Polls aggregate anonymous crowd metrics - zero raw camera feed
 */

async function fetchPublicStatus() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();

        // 1. Clock
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const clockElem = document.getElementById('portalClock');
        if (clockElem) clockElem.textContent = timeStr;

        // 2. Occupancy & Percentage
        const occ = data.occupancy || 0;
        const cap = data.capacity || 2000;
        const ratio = cap > 0 ? (occ / cap) : 0;
        const percent = Math.min(100, Math.round(ratio * 100));

        const occPercentElem = document.getElementById('occPercent');
        if (occPercentElem) occPercentElem.textContent = `${percent}%`;

        const ratioElem = document.getElementById('currentCapacityRatio');
        if (ratioElem) ratioElem.textContent = `${occ.toLocaleString()} / ${cap.toLocaleString()} Visitors`;

        const fillElem = document.getElementById('capacityFill');
        if (fillElem) fillElem.style.width = `${percent}%`;

        // 3. Status Badge, Bubble, and Description
        const bubble = document.getElementById('statusBubble');
        const badge = document.getElementById('statusBadge');
        const headline = document.getElementById('statusHeadline');
        const desc = document.getElementById('statusDesc');
        const circle = document.querySelector('.occupancy-circle');
        const waitElem = document.getElementById('waitTimeVal');

        if (ratio >= 0.85 || data.alert_level === 'CRITICAL') {
            if (bubble) bubble.textContent = '🔴';
            if (badge) {
                badge.textContent = 'HIGH CONGESTION';
                badge.style.color = '#ef4444';
                badge.style.background = 'rgba(239, 68, 68, 0.15)';
            }
            if (headline) headline.textContent = 'Venue is near full capacity! Expect significant delays.';
            if (desc) desc.textContent = 'Access checkpoints are operating under regulated pulse flow. We suggest postponing your arrival or visiting nearby alternate attractions.';
            if (circle) {
                circle.style.borderColor = '#ef4444';
                circle.style.background = 'rgba(239, 68, 68, 0.1)';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #f59e0b, #ef4444)';
            if (waitElem) {
                waitElem.textContent = '~15 - 25 Minutes';
                waitElem.className = 'text-red';
            }
        } else if (ratio >= 0.60 || data.alert_level === 'WARNING') {
            if (bubble) bubble.textContent = '🟡';
            if (badge) {
                badge.textContent = 'MODERATE OCCUPANCY';
                badge.style.color = '#f59e0b';
                badge.style.background = 'rgba(245, 158, 11, 0.15)';
            }
            if (headline) headline.textContent = 'Active footfall. Corridors are busy but moving.';
            if (desc) desc.textContent = 'Expect moderate queues at popular viewpoints and food stalls. Allow an extra 5-10 minutes for your itinerary.';
            if (circle) {
                circle.style.borderColor = '#f59e0b';
                circle.style.background = 'rgba(245, 158, 11, 0.1)';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #10b981, #f59e0b)';
            if (waitElem) {
                waitElem.textContent = '~5 - 8 Minutes';
                waitElem.className = 'text-yellow';
            }
        } else {
            if (bubble) bubble.textContent = '🟢';
            if (badge) {
                badge.textContent = 'COMFORTABLE FLOW';
                badge.style.color = '#10b981';
                badge.style.background = 'rgba(16, 185, 129, 0.15)';
            }
            if (headline) headline.textContent = 'Great time to visit! Minimal waiting lines.';
            if (desc) desc.textContent = 'Current footfall is within comfortable limits. Walking corridors and viewpoint areas are open with smooth pedestrian flow.';
            if (circle) {
                circle.style.borderColor = '#10b981';
                circle.style.background = 'rgba(16, 185, 129, 0.08)';
            }
            if (fillElem) fillElem.style.background = 'linear-gradient(90deg, #10b981, #3b82f6)';
            if (waitElem) {
                waitElem.textContent = '~1 - 3 Minutes';
                waitElem.className = 'text-green';
            }
        }

        // 4. Municipal Advisory Ticker
        const advElem = document.getElementById('portalAdvisory');
        if (advElem && data.ticker_text) {
            advElem.textContent = data.ticker_text;
        }

        // 5. Surge Alert
        const peakElem = document.getElementById('peakAlertText');
        if (peakElem && data.daily_update_alert) {
            peakElem.textContent = `⚠️ ${data.daily_update_alert}`;
        }

        // 6. Baselines
        const weeklyElem = document.getElementById('weeklyBaseline');
        if (weeklyElem && data.weekly_average) {
            weeklyElem.textContent = data.weekly_average;
        }

        const todayInElem = document.getElementById('todayInCount');
        if (todayInElem) {
            todayInElem.textContent = (data.current_entries || 0).toLocaleString();
        }

    } catch (e) {
        console.error("Public portal poll error:", e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchPublicStatus();
    setInterval(fetchPublicStatus, 2000);
});
