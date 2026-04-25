let currentResult = null;
let currentCertificate = null;
let mapInstance = null;
let trafficLayers = new Map();
let trafficUpdateInterval = null;
let costChartInstance = null;
let carbonChartInstance = null;
let historyChartInstance = null;
let trendChartInstance = null;
let modeChartInstance = null;

function updateLoadingStep(step) {
    const steps = ['step1', 'step2', 'step3', 'step4', 'step5'];
    const texts = [
        '正在分析最佳運輸方案...',
        '模擬即時交通資料...',
        '查詢船期資訊...',
        '計算成本與碳排...',
        'AI 多因子決策分析中...'
    ];

    steps.forEach((id, index) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('active');
        if (index < step) el.classList.add('completed');
        if (index === step) el.classList.add('active');
    });

    const text = document.getElementById('loadingText');
    if (text && texts[step]) text.textContent = texts[step];
}

function goToResult() {
    const start = document.getElementById('start').value;
    const end = document.getElementById('end').value;
    const containers = Number(document.getElementById('containers').value);

    if (!containers || containers <= 0) {
        alert('請輸入正確的貨櫃數量');
        return;
    }
    if (start === end) {
        alert('起點與終點不可相同');
        return;
    }

    localStorage.setItem('imarine_start', start);
    localStorage.setItem('imarine_end', end);
    localStorage.setItem('imarine_containers', String(containers));
    window.location.href = '/result';
}

function formatCurrency(value) {
    return 'NT$ ' + Number(value ?? 0).toLocaleString();
}

function animateValue(el, start, end, duration = 800, decimals = 0, suffix = '') {
    if (!el) return;
    const startTime = performance.now();
    function tick(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const value = start + (end - start) * progress;
        el.textContent = `${value.toFixed(decimals)}${suffix}`;
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

async function calculate() {
    const start = localStorage.getItem('imarine_start');
    const end = localStorage.getItem('imarine_end');
    const containers = localStorage.getItem('imarine_containers');

    if (!start || !end || !containers) {
        alert('請先到輸入頁輸入資料');
        window.location.href = '/input';
        return;
    }

    try {
        updateLoadingStep(0);
        const response = await fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start, end, containers })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || '計算失敗');

        currentResult = data;
        localStorage.setItem('imarine_record_id', data.record_id);

        updateLoadingStep(1);
        setTimeout(() => updateLoadingStep(2), 150);
        setTimeout(() => updateLoadingStep(3), 300);
        setTimeout(() => updateLoadingStep(4), 450);

        setTimeout(async () => {
            displayResults(data);
            drawCharts(data);
            await initMapAndTraffic(data);
            document.getElementById('loadingOverlay').style.display = 'none';
            document.getElementById('content').style.display = 'block';
        }, 600);
    } catch (error) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.innerHTML = `<div class="loading-container"><div style="color:#d62828; font-weight:700; margin-bottom:1rem;">${error.message}</div><button class="btn btn-primary" onclick="location.href='/input'">返回重新輸入</button></div>`;
        }
    }
}

function displayResults(data) {
    const road = data.road;
    const sea = data.sea;
    const resultEl = document.getElementById('result');
    if (!resultEl) return;

    resultEl.innerHTML = `
        <div class="result-card fade-in">
            <h3>📊 AI 多因子決策分析報告</h3>
            <p>🚢 ${data.start_name} → 🏁 ${data.end_name}</p>
            <p>📏 直線距離：<span class="result-value">${data.distance.toLocaleString()}</span> 公里</p>
            <p>🛣️ 道路估算距離：<span class="result-value">${data.road_distance.toLocaleString()}</span> 公里</p>
            <p>🌊 海運估算距離：<span class="result-value">${data.sea_distance.toLocaleString()}</span> 公里</p>
            <p>📦 貨櫃數量：<span class="result-value">${data.containers.toLocaleString()}</span> FEU</p>
            <div class="recommendation-box">🤖 <strong>AI 推薦：${data.best_mode}</strong><br>${data.recommendation}</div>
        </div>
        <div class="card fade-in">
            <h3>💰 社會總成本比較</h3>
            <table class="cost-table">
                <thead>
                    <tr>
                        <th>成本項目</th>
                        <th>🚛 公路</th>
                        <th>🚢 海運</th>
                        <th>差異</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>運費</td><td>${formatCurrency(road.freight)}</td><td>${formatCurrency(sea.freight)}</td><td>${formatCurrency(road.freight - sea.freight)}</td></tr>
                    <tr><td>時間成本</td><td>${formatCurrency(road.time)}</td><td>${formatCurrency(sea.time)}</td><td>${formatCurrency(road.time - sea.time)}</td></tr>
                    <tr><td>社會成本</td><td>${formatCurrency(road.social)}</td><td>${formatCurrency(sea.social)}</td><td>${formatCurrency(road.social - sea.social)}</td></tr>
                    <tr><td>風險成本</td><td>${formatCurrency(road.risk)}</td><td>${formatCurrency(sea.risk)}</td><td>${formatCurrency(road.risk - sea.risk)}</td></tr>
                    <tr><td>碳外部成本</td><td>${formatCurrency(road.carbon_externality)}</td><td>${formatCurrency(sea.carbon_externality)}</td><td>${formatCurrency(road.carbon_externality - sea.carbon_externality)}</td></tr>
                    <tr><td><strong>總成本</strong></td><td><strong>${formatCurrency(road.total)}</strong></td><td><strong>${formatCurrency(sea.total)}</strong></td><td><strong>${formatCurrency(data.social_savings)}</strong></td></tr>
                </tbody>
            </table>
        </div>
    `;

    fillShipSchedule(data.ship_schedule);
    fillDispatch(data.dispatch);
    fillOptimization(data.optimization, data.optimal_transfer_ratio);
}

function fillShipSchedule(ship) {
    if (!ship) return;
    const mapping = {
        shipName: ship.name,
        shipRoute: ship.route || '-',
        shipDest: ship.destination || '-',
        shipEta: `${ship.eta_hours} 小時後`,
        shipCapacity: `${ship.available} FEU`,
        shipSchedule: ship.eta === 'FRI' ? '每週五 / 日' : '每週二 / 四 / 六'
    };
    Object.entries(mapping).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    });
}

function fillDispatch(dispatch) {
    const target = document.getElementById('dispatchResult');
    if (!target || !dispatch) return;
    const reasonsHtml = dispatch.reasons.map(item => `<li>${item}</li>`).join('');
    target.innerHTML = `
        <div class="dispatch-grid">
            <div>
                <div class="score-card"><div class="score-number" id="scoreSea">0.0</div><div>🚢 海運分數</div></div>
                <div class="score-card"><div class="score-number" id="scoreRoad">0.0</div><div>🚛 公路分數</div></div>
            </div>
            <div>
                <div class="action-box"><strong>${dispatch.action}</strong><br>${dispatch.suggestion}</div>
                <div class="count-box">
                    <div><div>🚢 海運</div><strong id="seaCount">0</strong> FEU</div>
                    <div><div>🚛 公路</div><strong id="roadCount">0</strong> FEU</div>
                </div>
                <div class="ratio-bar-container"><div id="ratioBarSea" class="ratio-bar-sea" style="width:0%">🚢 <span id="seaPercent">0</span>%</div></div>
                <div class="ratio-bar-container"><div id="ratioBarRoad" class="ratio-bar-road" style="width:0%">🚛 <span id="roadPercent">0</span>%</div></div>
                <div class="reason-box"><strong>📌 分析理由</strong><ul>${reasonsHtml}</ul></div>
            </div>
        </div>
    `;

    setTimeout(() => {
        animateValue(document.getElementById('scoreSea'), 0, dispatch.score_sea, 600, 1);
        animateValue(document.getElementById('scoreRoad'), 0, dispatch.score_road, 600, 1);
        animateValue(document.getElementById('seaCount'), 0, dispatch.to_sea, 600, 0);
        animateValue(document.getElementById('roadCount'), 0, dispatch.to_road, 600, 0);
        const seaPercent = dispatch.ratio;
        const roadPercent = Number((100 - seaPercent).toFixed(1));
        document.getElementById('seaPercent').textContent = seaPercent;
        document.getElementById('roadPercent').textContent = roadPercent;
        document.getElementById('ratioBarSea').style.width = `${seaPercent}%`;
        document.getElementById('ratioBarRoad').style.width = `${roadPercent}%`;
    }, 100);
}

function fillOptimization(optimization, optimalTransferRatio) {
    const target = document.getElementById('optimizationResult');
    if (!target || !optimization) return;
    const best = optimalTransferRatio?.best || {};

    target.innerHTML = `
        <div class="model-desc">目標函數：Min Z = 運輸成本 + 碳排成本 + 事故成本 + 時間成本</div>
        <table class="cost-table">
            <thead>
                <tr>
                    <th>成本項目</th>
                    <th>🚛 公路</th>
                    <th>🚢 海運</th>
                    <th>節省</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>運輸成本</td><td>${formatCurrency(optimization.road.transport)}</td><td>${formatCurrency(optimization.sea.transport)}</td><td>${formatCurrency(optimization.savings.transport)}</td></tr>
                <tr><td>碳排成本</td><td>${formatCurrency(optimization.road.carbon)}</td><td>${formatCurrency(optimization.sea.carbon)}</td><td>${formatCurrency(optimization.savings.carbon)}</td></tr>
                <tr><td>事故成本</td><td>${formatCurrency(optimization.road.accident)}</td><td>${formatCurrency(optimization.sea.accident)}</td><td>${formatCurrency(optimization.savings.accident)}</td></tr>
                <tr><td>時間成本</td><td>${formatCurrency(optimization.road.time)}</td><td>${formatCurrency(optimization.sea.time)}</td><td>${formatCurrency(optimization.savings.time)}</td></tr>
                <tr><td><strong>總成本</strong></td><td><strong>${formatCurrency(optimization.road.total)}</strong></td><td><strong>${formatCurrency(optimization.sea.total)}</strong></td><td><strong>${formatCurrency(optimization.savings.total)}</strong></td></tr>
            </tbody>
        </table>
        <div class="benefit-grid" style="margin-top:1rem;">
            <div class="benefit-card">
                <div>🌱 減碳量</div>
                <div class="stat-value">${optimization.carbon_reduction_kg.toLocaleString()}</div>
                <div>${optimization.carbon_reduction_pct}%</div>
            </div>
            <div class="benefit-card">
                <div>🚸 風險節省</div>
                <div class="stat-value">${formatCurrency(optimization.vsl_saved)}</div>
                <div>約減少 ${optimization.deaths_reduced} 人死亡風險</div>
            </div>
            <div class="benefit-card">
                <div>⚖️ 最佳移轉比例</div>
                <div class="stat-value">${best.sea_ratio ?? 0}% 海運</div>
                <div>海運 ${best.sea_containers ?? 0} FEU / 公路 ${best.road_containers ?? 0} FEU</div>
            </div>
        </div>
    `;
}

async function initMapAndTraffic(data) {
    const centerLat = (data.start_lat + data.end_lat) / 2;
    const centerLon = (data.start_lon + data.end_lon) / 2;
    if (mapInstance) mapInstance.remove();
    if (typeof L === 'undefined') return;

    mapInstance = L.map('map').setView([centerLat, centerLon], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        subdomains: 'abcd'
    }).addTo(mapInstance);

    L.marker([data.start_lat, data.start_lon]).addTo(mapInstance).bindPopup(`起點：${data.start_name}`);
    L.marker([data.end_lat, data.end_lon]).addTo(mapInstance).bindPopup(`終點：${data.end_name}`);

    try {
        const response = await fetch('/static/taiwan_freeway.geojson');
        const geojson = await response.json();
        geojson.features.forEach(feature => {
            const layer = L.geoJSON(feature, {
                style: { color: '#b0bec5', weight: 4 }
            }).addTo(mapInstance);
            trafficLayers.set(feature.properties.id, layer);
        });
    } catch (error) {
        console.error('路網載入失敗', error);
    }

    await loadTrafficLight();
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    trafficUpdateInterval = setInterval(loadTrafficLight, 30000);
}

async function loadTrafficLight() {
    if (!mapInstance) return;
    try {
        const response = await fetch('/api/traffic');
        const speedData = await response.json();
        let totalSpeed = 0;
        let congested = 0;
        let smooth = 0;
        speedData.forEach(item => {
            totalSpeed += item.speed;
            if (item.speed < 35) congested += 1;
            if (item.speed >= 60) smooth += 1;
            const layer = trafficLayers.get(item.id);
            if (layer) {
                const color = item.speed >= 60 ? '#2a9d8f' : item.speed >= 35 ? '#f4a261' : '#e63946';
                layer.setStyle({ color, weight: 6 });
            }
        });

        const avgSpeed = speedData.length ? (totalSpeed / speedData.length).toFixed(1) : 0;
        const target = document.getElementById('trafficStats');
        if (target) {
            target.innerHTML = `
                <div class="stats-row">
                    <div class="stat-item"><div class="stat-value">${avgSpeed}</div><div class="stat-label">平均車速</div></div>
                    <div class="stat-item"><div class="stat-value" style="color:#d62828;">${congested}</div><div class="stat-label">壅塞路段</div></div>
                    <div class="stat-item"><div class="stat-value" style="color:#2a9d8f;">${smooth}</div><div class="stat-label">順暢路段</div></div>
                </div>
            `;
        }
    } catch (error) {
        console.error('讀取路況失敗', error);
    }
}

function destroyChart(instance) {
    if (instance) instance.destroy();
}

function drawCharts(data) {
    const costCtx = document.getElementById('costChart');
    const carbonCtx = document.getElementById('carbonChart');
    if (!costCtx || !carbonCtx || typeof Chart === 'undefined') return;

    destroyChart(costChartInstance);
    destroyChart(carbonChartInstance);

    costChartInstance = new Chart(costCtx, {
        type: 'bar',
        data: {
            labels: ['公路', '海運'],
            datasets: [
                { label: '運費', data: [data.road.freight, data.sea.freight], backgroundColor: 'rgba(2,62,138,0.8)' },
                { label: '時間成本', data: [data.road.time, data.sea.time], backgroundColor: 'rgba(0,119,182,0.8)' },
                { label: '社會成本', data: [data.road.social, data.sea.social], backgroundColor: 'rgba(0,180,216,0.8)' },
                { label: '風險成本', data: [data.road.risk, data.sea.risk], backgroundColor: 'rgba(72,202,228,0.8)' },
                { label: '碳外部成本', data: [data.road.carbon_externality, data.sea.carbon_externality], backgroundColor: 'rgba(144,224,239,0.8)' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: true }
    });

    carbonChartInstance = new Chart(carbonCtx, {
        type: 'bar',
        data: {
            labels: ['公路', '海運'],
            datasets: [{
                label: '碳排放 (kg CO2e)',
                data: [data.road.carbon, data.sea.carbon],
                backgroundColor: ['rgba(214,40,40,0.8)', 'rgba(42,157,143,0.8)']
            }]
        },
        options: { responsive: true, maintainAspectRatio: true }
    });
}

function goToCertificate() {
    if (!currentResult?.record_id) {
        alert('尚未找到本次計算紀錄');
        return;
    }
    localStorage.setItem('imarine_record_id', currentResult.record_id);
    window.location.href = '/certificate_page';
}

async function generateCertificate() {
    const companyName = document.getElementById('companyName').value.trim();
    const recordId = localStorage.getItem('imarine_record_id');
    if (!companyName) {
        alert('請輸入公司名稱');
        return;
    }
    if (!recordId) {
        alert('查無最近一次計算紀錄，請先重新計算');
        return;
    }

    try {
        const response = await fetch('/certificate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ company_name: companyName, record_id: recordId })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || '建立證書失敗');
        currentCertificate = data;

        const target = document.getElementById('certResult');
        target.innerHTML = `
            <div class="card" style="margin-bottom:0;">
                <h3>✅ 證書已建立</h3>
                <p>公司：${data.company_name}</p>
                <p>證書編號：${data.cert_id}</p>
                <p>路線：${data.route}</p>
                <p>減碳量：${data.carbon_improvement} kg CO2e</p>
                <p>驗證網址：<a href="/verify/${data.cert_id}" target="_blank">/verify/${data.cert_id}</a></p>
                <div class="action-buttons" style="margin-top:1rem; justify-content:flex-start;">
                    <button class="btn btn-primary" onclick="downloadCertificate('zh')">📄 中文 PDF</button>
                    <button class="btn btn-primary" onclick="downloadCertificate('en')">📄 English PDF</button>
                </div>
            </div>
        `;
    } catch (error) {
        alert(error.message);
    }
}

function downloadCertificate(lang) {
    if (!currentCertificate?.cert_id) {
        alert('請先建立證書');
        return;
    }
    window.location.href = `/download_certificate/${currentCertificate.cert_id}/${lang}`;
}

async function loadHistory() {
    const tbody = document.getElementById('historyBody');
    if (!tbody) return;
    try {
        const response = await fetch('/get_history');
        const data = await response.json();
        const rows = [...data].reverse();
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="9">暫無歷史記錄</td></tr>';
            return;
        }

        tbody.innerHTML = rows.map(row => `
            <tr>
                <td>${row.date}</td>
                <td>${row.start}</td>
                <td>${row.end}</td>
                <td>${row.containers}</td>
                <td>${row.road_distance} km</td>
                <td>${row.sea_distance} km</td>
                <td>${row.best_mode}</td>
                <td>${Number(row.carbon_improvement).toLocaleString()} kg</td>
                <td>${row.reduction_pct}%</td>
            </tr>
        `).join('');

        drawHistoryChart(rows);
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="9">載入失敗</td></tr>';
    }
}

function drawHistoryChart(history) {
    const ctx = document.getElementById('historyChart');
    if (!ctx || typeof Chart === 'undefined') return;
    destroyChart(historyChartInstance);
    const latest = history.slice(0, 7).reverse();
    historyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: latest.map(item => item.date.split(' ')[0]),
            datasets: [
                { label: '公路碳排', data: latest.map(item => item.road_carbon), borderColor: '#d62828', fill: false },
                { label: '海運碳排', data: latest.map(item => item.sea_carbon), borderColor: '#0077b6', fill: false }
            ]
        },
        options: { responsive: true }
    });
}

async function loadDashboard() {
    try {
        const response = await fetch('/get_history');
        const data = await response.json();
        if (!data.length) return;

        const totalReduction = data.reduce((sum, item) => sum + Number(item.carbon_improvement || 0), 0);
        const avgReduction = data.reduce((sum, item) => sum + Number(item.reduction_pct || 0), 0) / data.length;
        const seaCount = data.filter(item => item.best_mode === '海運').length;

        animateValue(document.getElementById('totalReduction'), 0, totalReduction, 1000, 0);
        document.getElementById('avgReduction').textContent = `${avgReduction.toFixed(1)}%`;
        document.getElementById('totalCount').textContent = data.length;
        document.getElementById('seaRate').textContent = `${Math.round((seaCount / data.length) * 100)}%`;

        const trendCtx = document.getElementById('trendChart');
        const modeCtx = document.getElementById('modeChart');
        const latest = data.slice(-14);

        destroyChart(trendChartInstance);
        destroyChart(modeChartInstance);

        trendChartInstance = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: latest.map(item => item.date.split(' ')[0]),
                datasets: [{
                    label: '減碳量 (kg)',
                    data: latest.map(item => item.carbon_improvement),
                    borderColor: '#0077b6',
                    fill: false
                }]
            },
            options: { responsive: true }
        });

        modeChartInstance = new Chart(modeCtx, {
            type: 'doughnut',
            data: {
                labels: ['海運推薦', '公路推薦'],
                datasets: [{
                    data: [seaCount, data.length - seaCount],
                    backgroundColor: ['#00b4d8', '#d62828']
                }]
            },
            options: { responsive: true }
        });
    } catch (error) {
        console.error('Dashboard 載入失敗', error);
    }
}
