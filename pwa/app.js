/* DispatchMind PWA — app.js */

let DATA = null;
let currentRole = null;
let clearedJunctions = {};
let totalCleared = 0;
let totalRecovered = 0;

// --- Data Loading ---
async function loadData() {
    const resp = await fetch('data/dashboard.json');
    DATA = await resp.json();
}

// --- Screen Navigation ---
function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    window.scrollTo(0, 0);
}

// --- Role Selection ---
document.querySelectorAll('.role-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        currentRole = btn.dataset.role;
        if (currentRole === 'constable') initConstable();
        else if (currentRole === 'si') initSI();
        else if (currentRole === 'acp') initACP();
    });
});

document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', () => showScreen(btn.dataset.target));
});

// --- Constable View ---
function initConstable() {
    const select = document.getElementById('constable-beat-select');
    select.innerHTML = '';
    Object.keys(DATA.beats).forEach(beat => {
        const opt = document.createElement('option');
        opt.value = beat;
        opt.textContent = beat;
        select.appendChild(opt);
    });
    select.addEventListener('change', () => renderConstableCards(select.value));
    showScreen('constable-view');
    renderConstableCards(select.value);
}

function renderConstableCards(beatName) {
    const beat = DATA.beats[beatName];
    if (!beat) return;

    document.getElementById('constable-beat-name').textContent = beatName;
    document.getElementById('constable-violations').textContent = `${beat.violation_count.toLocaleString()} violations`;
    document.getElementById('constable-delay').textContent = `${beat.total_delay.toLocaleString()} veh-min`;

    const container = document.getElementById('constable-cards');
    container.innerHTML = '';

    const recurrence = {};
    DATA.recurrence.forEach(r => { recurrence[r.mapped_junction] = r; });

    beat.junctions.forEach((j, idx) => {
        const rank = idx + 1;
        const isCleared = clearedJunctions[j.name];
        const tierClass = isCleared ? 'cleared' : `tier-${j.tier}`;
        const pulseClass = (rank === 1 && j.tier === 'CRITICAL' && !isCleared) ? ' pulse' : '';

        const card = document.createElement('div');
        card.className = `priority-card ${tierClass}${pulseClass}`;

        // Header
        let html = `<div class="card-header">`;
        html += `<span class="card-rank r-${isCleared ? 'LOW' : j.tier}">#${rank}</span>`;
        html += `<span class="card-junction">${j.name}</span>`;
        if (isCleared) html += `<span class="card-cleared-badge">CLEARED</span>`;
        else html += `<span class="tier-badge t-${j.tier}">${j.tier}</span>`;
        html += `</div>`;

        // Stats
        html += `<div class="card-stats">`;
        html += `<span class="card-stat"><strong>${j.total_delay.toLocaleString()}</strong> veh-min</span>`;
        html += `<span class="card-stat"><strong>${j.violation_count}</strong> violations</span>`;
        html += `<span class="card-stat"><strong>${j.top_vehicle}</strong></span>`;
        html += `</div>`;

        if (!isCleared && j.top_violations.length > 0) {
            const top = j.top_violations[0];
            html += `<div class="card-details">`;
            html += `<div class="card-clear-first"><strong>Clear first:</strong> ${top.vehicle} — ${top.violation} (${top.duration} min, score ${top.score})</div>`;
            html += `<div class="card-reason">${top.reason}</div>`;
            html += `</div>`;
        }

        // Warnings
        const rec = recurrence[j.name];
        if (!isCleared && rec) {
            html += `<div class="card-warnings">`;
            html += `<div class="warning-badge recurrence">Repeat spot: ${rec.recurrence_count} violations came back within 2 hrs after enforcement (${rec.avg_gap_hours.toFixed(1)}h avg gap)</div>`;
            html += `</div>`;
        }

        // Button
        if (isCleared) {
            html += `<button class="clear-btn done" disabled>✅ Cleared — ${isCleared.delay.toLocaleString()} veh-min recovered</button>`;
        } else {
            html += `<button class="clear-btn pending" data-junction="${j.name}" data-delay="${j.total_delay}" data-beat="${beatName}">✅ Clear This Spot</button>`;
        }

        card.innerHTML = html;
        container.appendChild(card);
    });

    // Bind clear buttons
    container.querySelectorAll('.clear-btn.pending').forEach(btn => {
        btn.addEventListener('click', () => {
            const junction = btn.dataset.junction;
            const delay = parseFloat(btn.dataset.delay);
            clearedJunctions[junction] = { beat: beatName, delay: delay };
            totalCleared++;
            totalRecovered += delay;
            renderConstableCards(beatName);
            updateShiftSummary();
        });
    });

    updateShiftSummary();
}

function updateShiftSummary() {
    const summary = document.getElementById('shift-summary');
    if (totalCleared > 0) {
        summary.style.display = 'block';
        document.getElementById('shift-delay-recovered').textContent = totalRecovered.toLocaleString();
    }
    document.getElementById('constable-cleared-count').textContent = `${totalCleared} cleared`;
}

// --- SMS ---
document.getElementById('sms-btn')?.addEventListener('click', () => {
    const beatName = document.getElementById('constable-beat-select').value;
    const beat = DATA.beats[beatName];
    if (!beat) return;

    let sms = `🚨 DISPATCHMIND — ${beatName} Beat (Hoysala):\n`;
    beat.junctions.forEach((j, i) => {
        const status = clearedJunctions[j.name] ? '✅ CLEARED' : '🔴 PENDING';
        sms += `#${i+1}: ${j.name} — ${j.top_vehicle}, ${j.total_delay.toLocaleString()} veh-min [${status}]\n`;
    });
    sms += `Shift: ${totalCleared} cleared, ${totalRecovered.toLocaleString()} veh-min recovered.`;

    document.getElementById('sms-text').textContent = sms;
    document.getElementById('sms-modal').style.display = 'flex';
});

document.getElementById('sms-close')?.addEventListener('click', () => {
    document.getElementById('sms-modal').style.display = 'none';
});

// --- Sub-Inspector View ---
function initSI() {
    const select = document.getElementById('si-station-select');
    select.innerHTML = '';
    Object.keys(DATA.beats).forEach(beat => {
        const opt = document.createElement('option');
        opt.value = beat;
        opt.textContent = beat;
        select.appendChild(opt);
    });
    select.addEventListener('change', () => renderSI(select.value));
    showScreen('si-view');
    renderSI(select.value);
}

function renderSI(stationName) {
    const beat = DATA.beats[stationName];
    if (!beat) return;

    document.getElementById('si-station-name').textContent = stationName;

    const totalDelay = Object.values(DATA.beats).reduce((s, b) => s + b.total_delay, 0);
    const pct = ((beat.total_delay / totalDelay) * 100).toFixed(1);

    document.getElementById('si-metrics').innerHTML = `
        <div class="si-metric">
            <div class="si-metric-value">${beat.total_delay.toLocaleString()}</div>
            <div class="si-metric-label">Station Delay (veh-min)</div>
        </div>
        <div class="si-metric">
            <div class="si-metric-value">${beat.violation_count.toLocaleString()}</div>
            <div class="si-metric-label">Violations</div>
        </div>
        <div class="si-metric">
            <div class="si-metric-value">${pct}%</div>
            <div class="si-metric-label">Share of City</div>
        </div>
    `;

    // Bar chart
    const chart = document.getElementById('si-beat-chart');
    chart.innerHTML = '';
    const maxDelay = Math.max(...beat.junctions.map(j => j.total_delay));
    const tierColors = { CRITICAL: '#DC2626', HIGH: '#F59E0B', MEDIUM: '#FBBF24', LOW: '#22C55E' };

    beat.junctions.forEach(j => {
        const pct = (j.total_delay / maxDelay) * 100;
        const color = tierColors[j.tier] || '#22C55E';
        chart.innerHTML += `
            <div class="bar-row">
                <span class="bar-label">${j.name}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pct}%;background:${color}">
                        <span class="bar-fill-text">${j.total_delay.toLocaleString()}</span>
                    </div>
                </div>
            </div>`;
    });

    // Hourly distribution chart (real data)
    const heatmap = document.getElementById('si-heatmap');
    const hours = DATA.hourly_distribution || [];
    if (hours.length > 0) {
        const maxH = Math.max(...hours.map(h => h.count));
        let heatHTML = '<div style="display:flex;align-items:flex-end;gap:2px;height:120px">';
        hours.forEach(h => {
            const pct = (h.count / maxH) * 100;
            const isPeak = h.hour >= 7 && h.hour <= 10 || h.hour >= 17 && h.hour <= 20;
            const color = isPeak ? 'var(--red)' : 'var(--bg-elevated)';
            heatHTML += `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px"><div style="width:100%;height:${pct}%;background:${color};border-radius:2px;min-height:2px"></div><span style="font-size:0.55rem;color:var(--text-dim)">${h.hour}</span></div>`;
        });
        heatHTML += '</div>';
        heatmap.innerHTML = heatHTML;
    } else {
        heatmap.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem;padding:1rem">No hourly data available</div>';
    }

    // Reassignment
    const reassign = document.getElementById('si-reassign');
    if (beat.junctions.length >= 2) {
        const heavy = beat.junctions[0];
        const quiet = beat.junctions[beat.junctions.length - 1];
        reassign.innerHTML = `<strong>Suggestion:</strong> Move 1 constable from ${quiet.name} (${quiet.total_delay.toLocaleString()} veh-min) → <strong>${heavy.name}</strong> (${heavy.total_delay.toLocaleString()} veh-min)`;
    }
}

// --- ACP View ---
function initACP() {
    document.querySelectorAll('.acp-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.acp-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderACPTab(tab.dataset.tab);
        });
    });
    showScreen('acp-view');
    renderACPTab('priority');
}

function renderACPTab(tab) {
    const container = document.getElementById('acp-content');
    container.innerHTML = '';

    if (tab === 'priority') renderACPPriority(container);
    else if (tab === 'futility') renderACPFutility(container);
    else if (tab === 'cascade') renderACPCascade(container);
    else if (tab === 'repeat') renderACPRepeat(container);
}

function renderACPPriority(container) {
    const g = DATA.global;
    const ci = DATA.counter_intuitive;

    // 7% Rule
    let html = `<div class="acp-section">`;
    html += `<div class="big-number">${g.pareto_pct}%</div>`;
    html += `<div class="big-label">of violations cause 82% of total congestion damage</div>`;
    html += `</div>`;

    // Formula
    const f = g.formula;
    html += `<div class="acp-section"><h2>How Impact Is Calculated</h2>`;
    html += `<div class="metric-grid">`;
    html += `<div class="metric-card"><div class="metric-value">${f.duration_example} min</div><div class="metric-label">Duration</div></div>`;
    html += `<div class="metric-card"><div class="metric-value">×${f.peak_example}</div><div class="metric-label">Rush Hour</div></div>`;
    html += `<div class="metric-card"><div class="metric-value">×${f.junction_mult_example}</div><div class="metric-label">Junction</div></div>`;
    html += `</div>`;
    html += `<div class="formula-box" style="margin-top:0.75rem">`;
    html += `Score = ${f.duration_example} × ${f.vehicle_mult_example} (vehicle) × ${f.junction_mult_example} (junction) × ${f.peak_example} (peak) × ${f.severity_example} (severity)`;
    html += `</div></div>`;

    // Counter-intuitive
    html += `<div class="acp-section"><h2>Why Counting Violations Is Wrong</h2>`;
    html += `<div class="metric-grid">`;
    html += `<div class="metric-card"><div class="metric-value" style="color:var(--red)">${ci.tanker_delay.toLocaleString()}</div><div class="metric-label">Tanker Delay (${ci.tanker_count} tickets)</div></div>`;
    html += `<div class="metric-card"><div class="metric-value" style="color:var(--blue)">${ci.scooter_delay.toLocaleString()}</div><div class="metric-label">Scooter Delay (${ci.scooter_count} tickets)</div></div>`;
    html += `<div class="metric-card"><div class="metric-value" style="color:var(--amber)">${ci.ratio}×</div><div class="metric-label">Tanker Impact Ratio</div></div>`;
    html += `</div></div>`;

    // What-If Simulator
    html += `<div class="acp-section"><h2>What-If Simulator</h2>`;
    html += `<p>Drag the slider to see how much delay you recover by clearing the top N violations.</p>`;
    html += `<input type="range" class="sim-slider" id="sim-slider" min="10" max="500" value="50" step="10">`;
    html += `<div id="sim-result" class="metric-grid" style="margin-top:0.75rem"></div>`;
    html += `<div id="sim-insight" style="margin-top:0.75rem;font-size:0.85rem;color:var(--text-secondary)"></div>`;
    html += `</div>`;

    // Pareto chart
    html += `<div class="acp-section"><h2>Top 30 Junctions by Delay</h2>`;
    html += `<div id="pareto-chart"></div></div>`;

    container.innerHTML = html;

    // Render pareto chart
    const paretoChart = document.getElementById('pareto-chart');
    const maxDelay = Math.max(...DATA.pareto.map(p => p.total_delay));
    DATA.pareto.forEach(p => {
        const pct = (p.total_delay / maxDelay) * 100;
        paretoChart.innerHTML += `
            <div class="bar-row">
                <span class="bar-label">${p.mapped_junction}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pct}%;background:var(--red)">
                        <span class="bar-fill-text">${p.total_delay.toLocaleString()}</span>
                    </div>
                </div>
            </div>`;
    });

    // What-if logic
    const slider = document.getElementById('sim-slider');
    const sorted = [...DATA.map].sort((a, b) => b.total_delay - a.total_delay);
    const totalDelay = sorted.reduce((s, m) => s + m.total_delay, 0);

    function updateSim() {
        const n = parseInt(slider.value);
        const topN = sorted.slice(0, n);
        const recovered = topN.reduce((s, m) => s + m.total_delay, 0);
        const pct = ((recovered / totalDelay) * 100).toFixed(1);
        document.getElementById('sim-result').innerHTML = `
            <div class="metric-card"><div class="metric-value">${n}</div><div class="metric-label">Violations Cleared</div></div>
            <div class="metric-card"><div class="metric-value" style="color:var(--green)">${recovered.toLocaleString()}</div><div class="metric-label">Delay Recovered</div></div>
            <div class="metric-card"><div class="metric-value">${pct}%</div><div class="metric-label">of Total</div></div>`;
        document.getElementById('sim-insight').innerHTML = `<strong>7% rule:</strong> Clearing ${n} violations (${(n / g.total_violations * 100).toFixed(1)}%) recovers ${pct}% of all congestion delay.`;
    }
    slider.addEventListener('input', updateSim);
    updateSim();
}

function renderACPFutility(container) {
    let html = `<div class="acp-section"><h2>Enforcement Futility — Where Ticketing Doesn't Work</h2>`;
    html += `<p>These spots get ticketed repeatedly but violations keep coming back. They need <strong>infrastructure fixes</strong>, not more constables.</p>`;
    html += `</div>`;

    if (DATA.recurrence.length > 0) {
        html += `<div class="acp-section"><h2>Repeat Spots (Violation Returns Within 2 Hours)</h2>`;
        html += `<table class="data-table"><thead><tr><th>Junction</th><th>Recurrences</th><th>Avg Gap</th><th>Futility %</th></tr></thead><tbody>`;
        DATA.recurrence.slice(0, 15).forEach(r => {
            html += `<tr><td>${r.mapped_junction}</td><td>${r.recurrence_count}</td><td>${r.avg_gap_hours.toFixed(1)}h</td><td>${r.futility_score}%</td></tr>`;
        });
        html += `</tbody></table></div>`;
    }

    container.innerHTML = html;
}

function renderACPCascade(container) {
    const c = DATA.cascade;
    let html = `<div class="acp-section"><h2>Cascade Proof — The Domino Effect</h2>`;
    html += `<p>When one junction jams, nearby junctions follow within 15 minutes. Proven from historical data.</p>`;

    html += `<div class="metric-grid">`;
    html += `<div class="metric-card"><div class="metric-value">${c.pairs_tested.toLocaleString()}</div><div class="metric-label">Pairs Tested</div></div>`;
    html += `<div class="metric-card"><div class="metric-value" style="color:var(--red)">${c.strong_pairs}</div><div class="metric-label">Strong (r>0.3)</div></div>`;
    html += `<div class="metric-card"><div class="metric-value" style="color:var(--amber)">${c.cascade_chains.toLocaleString()}</div><div class="metric-label">Cascade Chains</div></div>`;
    html += `</div></div>`;

    if (c.top_pairs.length > 0) {
        html += `<div class="acp-section"><h2>Top Linked Junction Pairs</h2>`;
        html += `<table class="data-table"><thead><tr><th>From</th><th>To</th><th>Distance</th><th>Correlation</th></tr></thead><tbody>`;
        c.top_pairs.forEach(p => {
            html += `<tr><td>${p.from_junction}</td><td>${p.to_junction}</td><td>${p.distance_m}m</td><td>${p.lag_correlation}</td></tr>`;
        });
        html += `</tbody></table></div>`;
    }

    html += `<div class="acp-section"><h2>Correlation ≠ Causation — Our Defense</h2>`;
    html += `<table class="defense-table">`;
    html += `<tr><td>r = 0.978 at 15-min lag</td><td>Probability of random: < 0.001</td></tr>`;
    html += `<tr><td>15-min > 5-min > 30-min</td><td>Matches physical propagation speed</td></tr>`;
    html += `<tr><td>Forward > Reverse</td><td>Directional cascade (not symmetric)</td></tr>`;
    html += `<tr><td>Geographic direction</td><td>Lalbagh upstream of Mysore Bank</td></tr>`;
    html += `<tr><td>Practical action</td><td>Clearing upstream STILL reduces downstream</td></tr>`;
    html += `</table></div>`;

    container.innerHTML = html;
}

function renderACPRepeat(container) {
    let html = `<div class="acp-section"><h2>Repeat Offenders — Cross-Jurisdiction</h2>`;
    html += `<p>The <1% of vehicles responsible for >20% of high-impact violations.</p>`;
    html += `</div>`;

    if (DATA.offenders.length > 0) {
        html += `<div class="acp-section"><table class="data-table"><thead><tr><th>Vehicle</th><th>Count</th><th>Stations</th><th>Delay</th><th>Type</th></tr></thead><tbody>`;
        DATA.offenders.slice(0, 15).forEach(o => {
            html += `<tr><td style="font-family:'JetBrains Mono',monospace;font-size:0.75rem">${o.vehicle_number}</td><td>${o.violation_count}</td><td style="font-size:0.7rem">${o.stations}</td><td>${Math.round(o.total_delay).toLocaleString()}</td><td>${o.top_vehicle}</td></tr>`;
        });
        html += `</tbody></table></div>`;
    }

    // Camera ROI
    html += `<div class="acp-section"><h2>Camera ROI Audit</h2>`;
    html += `<p>Which cameras catch high-impact violations? Which are wasting resources?</p>`;
    if (DATA.cameras.length > 0) {
        html += `<table class="data-table"><thead><tr><th>Camera</th><th>Tickets</th><th>High-Impact %</th><th>Delay/Violation</th></tr></thead><tbody>`;
        DATA.cameras.slice(0, 10).forEach(cam => {
            html += `<tr><td>${cam.device_id}</td><td>${cam.total_violations}</td><td style="color:${cam.high_impact_pct > 20 ? 'var(--red)' : 'var(--text-secondary)'}">${cam.high_impact_pct}%</td><td>${cam.delay_per_violation}</td></tr>`;
        });
        html += `</tbody></table>`;
    }
    html += `</div>`;

    container.innerHTML = html;
}

// --- Init ---
loadData().then(() => {
    console.log('DispatchMind data loaded');
}).catch(err => {
    console.error('Failed to load data:', err);
});
