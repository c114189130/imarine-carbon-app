let currentResult = null;
let mapInstance = null;
let trafficLayers = new Map();
let trafficUpdateInterval = null;

function formatCurrency(v) {
    const value = Number(v ?? 0);
    return "NT$ " + value.toLocaleString();
}

function animateValue(el, start, end, duration = 800, decimals = 0) {
    if (!el) return;
    const range = end - start;
    const inc = range / (duration / 16);
    let current = start;
    const timer = setInterval(() => {
        current += inc;
        if ((inc > 0 && current >= end) || (inc < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        el.textContent = decimals > 0 ? current.toFixed(decimals) : Math.round(current);
    }, 16);
}

function updateLoadingStep(step) {
    const steps = ['step1', 'step2', 'step3', 'step4', 'step5'];
    const texts = ['正在分析最佳運輸方案...', '串接即時交通資料...', '查詢長榮海運船期...', '計算碳排效益與社會成本...', 'AI 多因子決策分析中...'];
    for (let i = 0; i < steps.length; i++) {
        const el = document.getElementById(steps[i]);
        if (el) {
            if (i < step) { el.classList.add('completed'); el.innerHTML = el.innerHTML.replace('⏳', '✅'); }
            else if (i === step) el.classList.add('active');
            if (document.getElementById('loadingText')) {
                document.getElementById('loadingText').innerText = texts[step];
            }
        }
    }
}

function goToResult() {
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;
    const containers = document.getElementById("containers").value;
    if (!containers || containers <= 0) { alert("請輸入貨櫃數量"); return; }
    localStorage.setItem("start", start);
    localStorage.setItem("end", end);
    localStorage.setItem("containers", containers);
    window.location = "/result";
}

function calculate() {
    const start = localStorage.getItem("start");
    const end = localStorage.getItem("end");
    const containers = localStorage.getItem("containers");
    if (!start || !end || !containers) {
        alert("請先返回輸入頁面填寫資料");
        window.location = "/input";
        return;
    }
    updateLoadingStep(0);
    fetch("/calculate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start, end, containers })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        updateLoadingStep(1);
        setTimeout(() => {
            updateLoadingStep(2);
            setTimeout(() => {
                updateLoadingStep(3);
                setTimeout(() => {
                    updateLoadingStep(4);
                    setTimeout(() => {
                        currentResult = data;
                        displayResults(data);
                        drawCharts(data);
                        initMapAndTraffic(data);
                        document.getElementById("loadingOverlay").style.display = "none";
                        document.getElementById("content").style.display = "block";
                    }, 300);
                }, 300);
            }, 300);
        }, 300);
    })
    .catch(err => {
        console.error(err);
        const overlay = document.getElementById("loadingOverlay");
        if (overlay) {
            overlay.innerHTML = `<div class="loading-container"><div style="color:#e74c3c">計算失敗：${err.message}</div><button class="btn btn-primary" onclick="location.href='/input'">返回重新輸入</button></div>`;
        }
    });
}

function displayResults(data) {
    const road = data.road, sea = data.sea;
    let html = `
        <div class="result-card">
            <div><h3>📊 AI 多因子決策分析報告</h3></div>
            <div><p>🚢 ${data.start_name} → 🏁 ${data.end_name}</p><p>📏 距離：<span class="result-value">${Number(data.distance).toLocaleString()}</span> 公里</p><p>📦 貨櫃數量：<span class="result-value">${Number(data.containers).toLocaleString()}</span> FEU</p></div>
            <div class="recommendation-box">🤖 <strong>AI 推薦方案：${data.best_mode}</strong><br>${data.recommendation}</div>
        </div>
        <div class="card"><h3>💰 總體社會成本分析</h3>
        <table class="cost-table"><thead><tr><th>成本項目</th><th>🚛 公路</th><th>🚢 海運</th><th>節省</th></tr></thead><tbody>
        <tr><td><strong>💰 運費</strong></td><td>${formatCurrency(road.freight)}</td><td>${formatCurrency(sea.freight)}</td><td>${formatCurrency(road.freight - sea.freight)}</td></tr>
        <tr><td><strong>⏳ 時間成本</strong></td><td>${formatCurrency(road.time)}</td><td>${formatCurrency(sea.time)}</td><td>${formatCurrency(road.time - sea.time)}</td></tr>
        <tr><td><strong>🏛️ 社會成本</strong></td><td>${formatCurrency(road.social)}</td><td>${formatCurrency(sea.social)}</td><td class="savings-number">${formatCurrency(road.social - sea.social)}</td></tr>
        <tr><td><strong>⚠️ VSL風險</strong></td><td>${formatCurrency(road.vsl)}</td><td>${formatCurrency(sea.vsl)}</td><td class="savings-number">${formatCurrency(road.vsl - sea.vsl)}</td></tr>
        <tr style="background:var(--light-cyan);font-weight:bold"><td><strong>📊 總成本</strong></td><td>${formatCurrency(road.total)}</td><td>${formatCurrency(sea.total)}</td><td class="savings-number">${formatCurrency(data.improvement)}</td></tr>
        </tbody></table></div>`;
    document.getElementById("result").innerHTML = html;
    
    if (data.ship_schedule) {
        if (document.getElementById("shipName")) document.getElementById("shipName").innerHTML = data.ship_schedule.name;
        if (document.getElementById("shipRoute")) document.getElementById("shipRoute").innerHTML = data.ship_schedule.route || "TBS";
        if (document.getElementById("shipDest")) document.getElementById("shipDest").innerHTML = data.ship_schedule.destination;
        if (document.getElementById("shipEta")) document.getElementById("shipEta").innerHTML = data.ship_schedule.eta_hours + " 小時後";
        if (document.getElementById("shipCapacity")) document.getElementById("shipCapacity").innerHTML = data.ship_schedule.available + " FEU";
        if (document.getElementById("shipSchedule")) document.getElementById("shipSchedule").innerHTML = data.ship_schedule.eta === "FRI" ? "每週五、日" : "每週二、四、六";
    }
    
    if (data.dispatch) {
        const de = document.getElementById("dispatchResult");
        if (de) {
            let reasonsHtml = data.dispatch.reasons.map(r => `<li>${r}</li>`).join('');
            de.innerHTML = `<div class="dispatch-grid">
                <div class="score-section">
                    <div class="score-card sea"><div class="score-number" id="scoreSea">0</div><div>🚢 海運分數</div></div>
                    <div class="score-card road"><div class="score-number" id="scoreRoad">0</div><div>🚛 公路分數</div></div>
                </div>
                <div class="decision-section">
                    <div class="action-box"><p class="action-title">${data.dispatch.action}</p><p>${data.dispatch.suggestion}</p></div>
                    <div class="count-box"><div><span class="emoji">🚢</span><br><strong id="seaCount">${data.dispatch.to_sea}</strong> FEU</div><div><span class="emoji">🚛</span><br><strong id="roadCount">${data.dispatch.to_road}</strong> FEU</div></div>
                    <div class="ratio-bars">
                        <div class="ratio-bar-container"><div id="ratioBarSea" class="ratio-bar-sea" style="width:0%">🚢 <span id="seaPercent">0</span>%</div></div>
                        <div class="ratio-bar-container"><div id="ratioBarRoad" class="ratio-bar-road" style="width:0%">🚛 <span id="roadPercent">0</span>%</div></div>
                    </div>
                    <div class="reason-box"><p class="reason-title">📌 詳細分析</p><ul>${reasonsHtml}</ul><hr><p class="why-sea">🌱 海運碳排放僅為公路的 1/3</p></div>
                </div>
            </div>`;
            setTimeout(() => {
                animateValue(document.getElementById("scoreSea"), 0, data.dispatch.score_sea, 600, 1);
                animateValue(document.getElementById("scoreRoad"), 0, data.dispatch.score_road, 600, 1);
                animateValue(document.getElementById("seaCount"), 0, data.dispatch.to_sea, 600);
                animateValue(document.getElementById("roadCount"), 0, data.dispatch.to_road, 600);
                if (document.getElementById("seaPercent")) document.getElementById("seaPercent").innerText = data.dispatch.ratio;
                if (document.getElementById("roadPercent")) document.getElementById("roadPercent").innerText = (100 - data.dispatch.ratio).toFixed(1);
                if (document.getElementById("ratioBarSea")) document.getElementById("ratioBarSea").style.width = `${data.dispatch.ratio}%`;
                if (document.getElementById("ratioBarRoad")) document.getElementById("ratioBarRoad").style.width = `${100 - data.dispatch.ratio}%`;
            }, 100);
        }
    }
    
    if (data.optimization) {
        const opt = data.optimization;
        const optDiv = document.getElementById("optimizationResult");
        if (optDiv) {
            optDiv.innerHTML = `
                <table class="cost-table">
                    <thead><tr><th>成本項目</th><th>🚛 公路</th><th>🚢 海運</th><th>節省</th></tr></thead>
                    <tbody>
                        <tr><td>運輸成本</td><td>${formatCurrency(opt.road.transport)}</td><td>${formatCurrency(opt.sea.transport)}</td><td>${formatCurrency(opt.savings.transport)}</td></tr>
                        <tr><td>碳排成本</td><td>${formatCurrency(opt.road.carbon)}</td><td>${formatCurrency(opt.sea.carbon)}</td><td>${formatCurrency(opt.savings.carbon)}</td></tr>
                        <tr><td>事故成本</td><td>${formatCurrency(opt.road.accident)}</td><td>${formatCurrency(opt.sea.accident)}</td><td class="savings-number">${formatCurrency(opt.savings.accident)}</td></tr>
                        <tr><td>時間成本</td><td>${formatCurrency(opt.road.time)}</td><td>${formatCurrency(opt.sea.time)}</td><td>${formatCurrency(opt.savings.time)}</td></tr>
                        <tr style="background:var(--light-cyan);font-weight:bold"><td>總成本</td><td>${formatCurrency(opt.road.total)}</td><td>${formatCurrency(opt.sea.total)}</td><td class="savings-number">${formatCurrency(opt.savings.total)}</td></tr>
                    </tbody>
                </table>
                <div class="benefit-grid">
                    <div class="benefit-card carbon"><div class="benefit-icon">🌱</div><div class="benefit-value">${Number(opt.carbon_reduction_kg).toLocaleString()} kg</div><div class="benefit-label">減碳量</div></div>
                    <div class="benefit-card vsl"><div class="benefit-icon">🚸</div><div class="benefit-value">${formatCurrency(opt.vsl_saved)}</div><div class="benefit-label">人命價值節省</div><div class="benefit-sub">相當於減少 ${opt.deaths_reduced} 人死亡</div></div>
                </div>`;
        }
    }
}

async function initMapAndTraffic(data) {
    const centerLat = (data.start_lat + data.end_lat) / 2;
    const centerLon = (data.start_lon + data.end_lon) / 2;
    if (mapInstance) mapInstance.remove();
    if (typeof L === 'undefined') return;
    mapInstance = L.map('map').setView([centerLat, centerLon], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; OSM', subdomains: 'abcd' }).addTo(mapInstance);
    try {
        const response = await fetch('/static/taiwan_freeway.geojson');
        const geojson = await response.json();
        geojson.features.forEach(f => {
            const layer = L.geoJSON(f, { style: { color: '#ccc', weight: 3 } }).addTo(mapInstance);
            trafficLayers.set(f.properties.id, layer);
        });
    } catch(e) { console.error("載入路網失敗:", e); }
    setTimeout(() => loadTrafficLight(), 500);
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    trafficUpdateInterval = setInterval(loadTrafficLight, 30000);
}

async function loadTrafficLight() {
    if (!mapInstance) return;
    try {
        const response = await fetch("/api/traffic");
        if (!response.ok) throw new Error();
        const speedData = await response.json();
        let totalSpeed = 0, congested = 0, smooth = 0;
        speedData.forEach(item => {
            const layer = trafficLayers.get(item.id);
            if (layer) {
                const color = item.speed >= 60 ? "#27ae60" : (item.speed >= 35 ? "#f39c12" : "#e74c3c");
                layer.setStyle({ color: color, weight: 5 });
                totalSpeed += item.speed;
                if (item.speed < 35) congested++;
                if (item.speed >= 60) smooth++;
            }
        });
        const avgSpeed = speedData.length > 0 ? (totalSpeed / speedData.length).toFixed(1) : 0;
        const statsDiv = document.getElementById("trafficStats");
        if (statsDiv) statsDiv.innerHTML = `<div class="stats-row"><div class="stat-item"><div class="stat-value">${avgSpeed}</div><div class="stat-label">平均車速</div></div><div class="stat-item"><div class="stat-value" style="color:#e74c3c">${congested}</div><div class="stat-label">壅塞路段</div></div><div class="stat-item"><div class="stat-value" style="color:#27ae60">${smooth}</div><div class="stat-label">順暢路段</div></div></div>`;
    } catch(error) { console.error("載入即時路況失敗:", error); }
}

function drawCharts(data) {
    new Chart(document.getElementById("costChart"), {
        type: 'bar',
        data: {
            labels: ['公路', '海運'],
            datasets: [
                { label: '運費', data: [data.road.freight, data.sea.freight], backgroundColor: 'rgba(0,119,182,0.7)' },
                { label: '時間成本', data: [data.road.time, data.sea.time], backgroundColor: 'rgba(0,180,216,0.7)' },
                { label: '社會成本', data: [data.road.social, data.sea.social], backgroundColor: 'rgba(72,202,228,0.7)' },
                { label: 'VSL風險', data: [data.road.vsl, data.sea.vsl], backgroundColor: 'rgba(144,224,239,0.7)' }
            ]
        },
        options: { responsive: true }
    });
    new Chart(document.getElementById("carbonChart"), {
        type: 'bar',
        data: {
            labels: ['公路', '海運'],
            datasets: [{ label: '碳排放 (kg CO2e)', data: [data.road.carbon, data.sea.carbon], backgroundColor: ['rgba(231,76,60,0.7)', 'rgba(46,204,113,0.7)'] }]
        },
        options: { responsive: true }
    });
}

function generateCert() {
    const name = document.getElementById("name").value;
    if (!name) { alert("請輸入公司名稱"); return; }
    const carbonSaved = localStorage.getItem("savedCO2") || 0;
    const reductionPct = localStorage.getItem("reductionPct") || 0;
    fetch("/certificate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, carbon_saved: parseFloat(carbonSaved), reduction_pct: parseFloat(reductionPct) })
    })
    .then(res => res.json())
    .then(data => {
        localStorage.setItem("cert", JSON.stringify(data));
        document.getElementById("certResult").innerHTML = `
            <div class="card" style="text-align:center"><h3>✅ 碳排認證已產生</h3>
            <p>公司：${data.name}</p><p>編號：${data.cert_id}</p><p>日期：${data.date}</p>
            <button class="btn btn-primary" onclick="downloadPDF('chinese')">📄 中文證書</button>
            <button class="btn btn-primary" onclick="downloadPDF('english')">📄 English Certificate</button></div>`;
    });
}

function downloadPDF(lang) {
    const cert = JSON.parse(localStorage.getItem("cert"));
    if (!cert) { alert("請先產生認證"); return; }
    const endpoint = lang === 'chinese' ? '/download_pdf_chinese' : '/download_pdf_english';
    fetch(endpoint, {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cert)
    })
    .then(res => res.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `certificate_${cert.cert_id}_${lang}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
    });
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_improvement);
        localStorage.setItem("reductionPct", currentResult.reduction_pct);
    }
    window.location = "/certificate_page";
}

function loadHistory() {
    fetch("/get_history")
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("historyBody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9">暫無歷史記錄</td></tr>';
                return;
            }
            const reversed = [...data].reverse();
            reversed.forEach(r => {
                tbody.innerHTML += `<tr>
                    <td>${r.date}</td><td>${r.start}</td><td>${r.end}</td>
                    <td>${r.containers}</td><td>${r.distance} km</td>
                    <td>${Number(r.sea_carbon || 0).toLocaleString()} kg</td>
                    <td>${r.best_mode}</td>
                    <td>${Number(r.carbon_improvement || 0).toLocaleString()} kg</td>
                    <td>${r.reduction_pct || 0}%</td>
                </tr>`;
            });
            drawHistoryChart(data);
        })
        .catch(err => console.error(err));
}

function drawHistoryChart(history) {
    const ctx = document.getElementById("historyChart");
    if (!ctx) return;
    const last7 = history.slice(-7);
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: last7.map(h => h.date?.split(' ')[0] || ''),
            datasets: [
                { label: '公路碳排', data: last7.map(h => h.road_carbon || 0), borderColor: '#e74c3c', fill: true },
                { label: '海運碳排', data: last7.map(h => h.sea_carbon || 0), borderColor: '#0077b6', fill: true }
            ]
        }
    });
}

function loadDashboard() {
    fetch("/get_history")
        .then(res => res.json())
        .then(data => {
            if (data.length === 0) {
                document.getElementById("totalReduction").innerText = "0";
                document.getElementById("avgReduction").innerText = "0%";
                document.getElementById("totalCount").innerText = "0";
                document.getElementById("seaRate").innerText = "0%";
                return;
            }
            const total = data.reduce((s, d) => s + (d.carbon_improvement || 0), 0);
            const avg = data.reduce((s, d) => s + (d.reduction_pct || 0), 0) / data.length;
            const seaCount = data.filter(d => d.best_mode === "海運").length;
            animateValue(document.getElementById("totalReduction"), 0, total, 1000);
            document.getElementById("avgReduction").innerText = avg.toFixed(1) + "%";
            document.getElementById("totalCount").innerText = data.length;
            document.getElementById("seaRate").innerText = Math.round(seaCount / data.length * 100) + "%";
            new Chart(document.getElementById("trendChart"), {
                type: 'line',
                data: {
                    labels: data.slice(-14).map(d => d.date?.split(' ')[0] || ''),
                    datasets: [{ label: "減碳量 (kg)", data: data.slice(-14).map(d => d.carbon_improvement || 0), borderColor: "#0077b6", fill: true }]
                }
            });
            new Chart(document.getElementById("modeChart"), {
                type: 'doughnut',
                data: { labels: ["海運推薦", "公路推薦"], datasets: [{ data: [seaCount, data.length - seaCount], backgroundColor: ["#00b4d8", "#48cae4"] }] }
            });
        });
}