let currentResult = null;

function goToResult() {
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;
    const containers = document.getElementById("containers").value;
    
    if (!containers || containers <= 0) {
        alert("請輸入貨櫃數量");
        return;
    }
    
    localStorage.setItem("start", start);
    localStorage.setItem("end", end);
    localStorage.setItem("containers", containers);
    window.location = "/result";
}

function animateValue(element, start, end, duration = 800) {
    if (!element) return;
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

function formatCurrency(v) {
    return "NT$ " + v.toLocaleString();
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
    
    fetch("/calculate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start, end, containers })
    })
    .then(res => res.json())
    .then(data => {
        currentResult = data;
        displayResults(data);
        drawCharts(data);
        drawMap(data);
        loadTrafficNetwork();
        startTrafficAutoUpdate();
        displayOptimizationResults(data);
        
        document.getElementById("loading").style.display = "none";
        document.getElementById("content").style.display = "block";
    })
    .catch(err => {
        console.error("Error:", err);
        document.getElementById("loading").innerHTML = '<div class="loading-card" style="text-align:center"><div style="color:var(--error)">計算失敗：' + err.message + '</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回重新輸入</button></div>';
    });
}

function displayResults(data) {
    const road = data.road;
    const sea = data.sea;
    
    let html = `
        <div class="result-card">
            <div class="result-header">
                <h3>📊 AI 多因子決策分析報告</h3>
            </div>
            <div class="result-info">
                <p>🚢 起點：${data.start_name} → 🏁 終點：${data.end_name}</p>
                <p>📏 距離：<span class="result-value">${data.distance.toLocaleString()}</span> 公里</p>
                <p>📦 貨櫃數量：<span class="result-value">${data.containers.toLocaleString()}</span> FEU</p>
            </div>
            <div class="recommendation-box">
                🤖 <strong>AI 推薦方案：${data.best_mode}</strong><br>
                ${data.recommendation}
            </div>
        </div>
        
        <div class="card">
            <h3>💰 總體社會成本分析</h3>
            <table class="cost-table">
                <thead><tr><th>成本項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th><th>節省金額</th></tr></thead>
                <tbody>
                    <tr><td><strong>💰 運費</strong></td><td>${formatCurrency(road.freight)}</td><td>${formatCurrency(sea.freight)}</td><td>${formatCurrency(road.freight - sea.freight)}</td></tr>
                    <tr><td><strong>⏳ 時間成本</strong></td><td>${formatCurrency(road.time)}</td><td>${formatCurrency(sea.time)}</td><td>${formatCurrency(road.time - sea.time)}</td></tr>
                    <tr><td><strong>🏛️ 社會成本</strong></td><td>${formatCurrency(road.social)}</td><td>${formatCurrency(sea.social)}</td><td class="savings-number">${formatCurrency(road.social - sea.social)}</td></tr>
                    <tr><td><strong>⚠️ VSL風險成本</strong></td><td>${formatCurrency(road.vsl)}</td><td>${formatCurrency(sea.vsl)}</td><td class="savings-number">${formatCurrency(road.vsl - sea.vsl)}</td></tr>
                    <tr style="background:var(--light-cyan); font-weight:bold"><td><strong>📊 總成本</strong></td><td>${formatCurrency(road.total)}</td><td>${formatCurrency(sea.total)}</td><td class="savings-number">${formatCurrency(data.social_savings)}</td></tr>
                </tbody>
            </table>
        </div>
    `;
    
    document.getElementById("result").innerHTML = html;
    
    // 長榮船期詳細資訊
    if (data.ship_schedule) {
        document.getElementById("shipName") && (document.getElementById("shipName").innerHTML = data.ship_schedule.name);
        document.getElementById("shipRoute") && (document.getElementById("shipRoute").innerHTML = data.ship_schedule.route || "TBS 藍色公路");
        document.getElementById("shipDest") && (document.getElementById("shipDest").innerHTML = data.ship_schedule.destination);
        document.getElementById("shipEta") && (document.getElementById("shipEta").innerHTML = data.ship_schedule.eta_hours + " 小時後");
        document.getElementById("shipCapacity") && (document.getElementById("shipCapacity").innerHTML = data.ship_schedule.available + " FEU");
        document.getElementById("shipSchedule") && (document.getElementById("shipSchedule").innerHTML = data.ship_schedule.eta === "FRI" ? "每週五、日" : "每週二、四、六");
    }
    
    // 指派建議
    if (data.dispatch) {
        const de = document.getElementById("dispatchResult");
        if (de) {
            let reasonsHtml = data.dispatch.reasons.map(r => `<li>${r}</li>`).join('');
            de.innerHTML = `
                <div class="dispatch-grid">
                    <div class="score-section">
                        <div class="score-card sea">
                            <div class="score-number" id="scoreSea">0</div>
                            <div class="score-label">🚢 海運分數</div>
                        </div>
                        <div class="score-card road">
                            <div class="score-number" id="scoreRoad">0</div>
                            <div class="score-label">🚛 公路分數</div>
                        </div>
                    </div>
                    <div class="decision-section">
                        <div class="action-box">
                            <p class="action-title">${data.dispatch.action}</p>
                            <p>${data.dispatch.suggestion}</p>
                        </div>
                        <div class="count-box">
                            <div><span class="emoji">🚢</span><br><strong id="seaCount">${data.dispatch.to_sea}</strong> FEU</div>
                            <div><span class="emoji">🚛</span><br><strong id="roadCount">${data.dispatch.to_road}</strong> FEU</div>
                        </div>
                        <div class="ratio-bars">
                            <div class="ratio-bar-container"><div class="ratio-bar-sea" id="ratioBarSea" style="width:0%">🚢 <span id="seaPercent">0</span>%</div></div>
                            <div class="ratio-bar-container"><div class="ratio-bar-road" id="ratioBarRoad" style="width:0%">🚛 <span id="roadPercent">0</span>%</div></div>
                        </div>
                        <div class="reason-box">
                            <p class="reason-title">📌 詳細分析</p>
                            <ul>${reasonsHtml}</ul>
                            <hr>
                            <p class="why-sea">🌱 <strong>為什麼走海運比較好？</strong><br>海運碳排放僅為公路的 1/3，且長榮 TBS/TBS2 藍色公路航班穩定。</p>
                        </div>
                    </div>
                </div>
            `;
            
            setTimeout(() => {
                animateValue(document.getElementById("scoreSea"), 0, data.dispatch.score_sea, 600);
                animateValue(document.getElementById("scoreRoad"), 0, data.dispatch.score_road, 600);
                animateValue(document.getElementById("seaCount"), 0, data.dispatch.to_sea, 600);
                animateValue(document.getElementById("roadCount"), 0, data.dispatch.to_road, 600);
                const sp = document.getElementById("seaPercent");
                const rp = document.getElementById("roadPercent");
                if (sp) sp.innerText = data.dispatch.ratio;
                if (rp) rp.innerText = (100 - data.dispatch.ratio).toFixed(1);
                const seaBar = document.getElementById("ratioBarSea");
                const roadBar = document.getElementById("ratioBarRoad");
                if (seaBar) seaBar.style.width = `${data.dispatch.ratio}%`;
                if (roadBar) roadBar.style.width = `${100 - data.dispatch.ratio}%`;
            }, 100);
        }
    }
}

function displayOptimizationResults(data) {
    if (!data.optimization) return;
    
    const opt = data.optimization;
    const optDiv = document.getElementById("optimizationResult");
    if (optDiv) {
        optDiv.innerHTML = `
            <table class="cost-table">
                <thead><tr><th>成本項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th><th>節省金額</th></tr></thead>
                <tbody>
                    <tr><td><strong>運輸成本</strong></td><td>${formatCurrency(opt.road.transport)}</td><td>${formatCurrency(opt.sea.transport)}</td><td>${formatCurrency(opt.savings.transport)}</td></tr>
                    <tr><td><strong>碳排成本</strong></td><td>${formatCurrency(opt.road.carbon)}</td><td>${formatCurrency(opt.sea.carbon)}</td><td>${formatCurrency(opt.savings.carbon)}</td></tr>
                    <tr><td><strong>事故成本</strong></td><td>${formatCurrency(opt.road.accident)}</td><td>${formatCurrency(opt.sea.accident)}</td><td class="savings-number">${formatCurrency(opt.savings.accident)}</td></tr>
                    <tr><td><strong>時間成本</strong></td><td>${formatCurrency(opt.road.time)}</td><td>${formatCurrency(opt.sea.time)}</td><td>${formatCurrency(opt.savings.time)}</td></tr>
                    <tr style="background:var(--light-cyan); font-weight:bold">
                        <td><strong>總社會成本</strong></td>
                        <td>${formatCurrency(opt.road.total)}</td>
                        <td>${formatCurrency(opt.sea.total)}</td>
                        <td class="savings-number">${formatCurrency(opt.savings.total)}</td>
                    </tr>
                </tbody>
            </table>
            <div class="benefit-grid">
                <div class="benefit-card carbon">
                    <div class="benefit-icon">🌱</div>
                    <div class="benefit-value">${opt.carbon_reduction_kg.toLocaleString()} kg</div>
                    <div class="benefit-label">減碳量 (${opt.carbon_reduction_pct}%)</div>
                </div>
                <div class="benefit-card vsl">
                    <div class="benefit-icon">🚸</div>
                    <div class="benefit-value">${formatCurrency(opt.vsl_saved)}</div>
                    <div class="benefit-label">人命價值節省</div>
                    <div class="benefit-sub">相當於減少 ${opt.deaths_reduced} 人死亡</div>
                </div>
            </div>
        `;
    }
    
    if (data.optimal_transfer_ratio) {
        const optRatio = data.optimal_transfer_ratio;
        const conclusionDiv = document.getElementById("researchConclusion");
        if (conclusionDiv) {
            conclusionDiv.innerHTML += `
                <div class="optimal-box">
                    <p class="optimal-title">📈 最佳轉移比例分析</p>
                    <p>將 <strong>${optRatio.sea_ratio}%</strong> 貨櫃轉移至海運（<strong>${optRatio.sea_containers}</strong> FEU），可達最低社會成本 <strong>${formatCurrency(optRatio.total_cost)}</strong></p>
                </div>
            `;
        }
    }
}

// ================= 即時路網地圖 =================

let mapInstance = null;
let trafficLayers = [];
let trafficUpdateInterval = null;

function initMap(centerLat, centerLon, zoom = 7) {
    if (mapInstance) { mapInstance.remove(); }
    if (typeof L === 'undefined') { return null; }
    mapInstance = L.map('map').setView([centerLat, centerLon], zoom);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors',
        subdomains: 'abcd', maxZoom: 19
    }).addTo(mapInstance);
    return mapInstance;
}

async function loadTrafficNetwork() {
    if (!mapInstance) return;
    try {
        const response = await fetch("/api/traffic");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const roads = await response.json();
        
        trafficLayers.forEach(layer => { if (mapInstance && mapInstance.hasLayer(layer)) mapInstance.removeLayer(layer); });
        trafficLayers = [];
        
        let totalSpeed = 0, congested = 0, smooth = 0;
        roads.forEach(road => {
            if (!road.coords || road.coords.length < 2) return;
            const polyline = L.polyline(road.coords, { color: road.color || "#888", weight: 5, opacity: 0.8 }).addTo(mapInstance);
            trafficLayers.push(polyline);
            totalSpeed += road.speed;
            if (road.speed < 35) congested++;
            if (road.speed >= 60) smooth++;
        });
        
        const avgSpeed = roads.length > 0 ? (totalSpeed / roads.length).toFixed(1) : 0;
        const statsDiv = document.getElementById("trafficStats");
        if (statsDiv) {
            statsDiv.innerHTML = `
                <div class="stats-row">
                    <div class="stat-item"><div class="stat-value">${avgSpeed}</div><div class="stat-label">平均車速 (km/h)</div></div>
                    <div class="stat-item"><div class="stat-value" style="color:#e74c3c">${congested}</div><div class="stat-label">壅塞路段</div></div>
                    <div class="stat-item"><div class="stat-value" style="color:#27ae60">${smooth}</div><div class="stat-label">順暢路段</div></div>
                </div>
            `;
        }
    } catch (error) { console.error("載入即時路網失敗:", error); }
}

function startTrafficAutoUpdate() {
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    trafficUpdateInterval = setInterval(loadTrafficNetwork, 30000);
}

function drawMap(data) {
    const centerLat = (data.start_lat + data.end_lat) / 2;
    const centerLon = (data.start_lon + data.end_lon) / 2;
    initMap(centerLat, centerLon);
    loadTrafficNetwork();
}

function drawCharts(data) {
    const costCtx = document.getElementById("costChart");
    if (costCtx) {
        new Chart(costCtx, {
            type: 'bar',
            data: {
                labels: ['公路運輸', '海運運輸'],
                datasets: [
                    { label: '運費', data: [data.road.freight, data.sea.freight], backgroundColor: 'rgba(0,119,182,0.7)' },
                    { label: '時間成本', data: [data.road.time, data.sea.time], backgroundColor: 'rgba(0,180,216,0.7)' },
                    { label: '社會成本', data: [data.road.social, data.sea.social], backgroundColor: 'rgba(72,202,228,0.7)' },
                    { label: 'VSL風險', data: [data.road.vsl, data.sea.vsl], backgroundColor: 'rgba(144,224,239,0.7)' }
                ]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
    }
    const carbonCtx = document.getElementById("carbonChart");
    if (carbonCtx) {
        new Chart(carbonCtx, {
            type: 'bar',
            data: {
                labels: ['公路運輸', '海運運輸'],
                datasets: [{ label: '碳排放量 (kg CO2e)', data: [data.road.carbon, data.sea.carbon], backgroundColor: ['rgba(231,76,60,0.7)', 'rgba(46,204,113,0.7)'] }]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
    }
}

// 認證功能
function generateCert() {
    const name = document.getElementById("name").value;
    if (!name) { alert("請輸入公司名稱"); return; }
    const carbonSaved = localStorage.getItem("savedCO2") || 0;
    const reductionPct = localStorage.getItem("reductionPct") || 0;
    fetch("/certificate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, carbon_saved: parseFloat(carbonSaved), reduction_pct: parseFloat(reductionPct) })
    }).then(res => res.json()).then(data => {
        localStorage.setItem("cert", JSON.stringify(data));
        document.getElementById("certResult").innerHTML = `
            <div class="card" style="text-align:center; margin-top:1rem">
                <h3>✅ 碳排認證已產生</h3>
                <p><strong>公司：</strong>${data.name}</p>
                <p><strong>編號：</strong>${data.cert_id}</p>
                <p><strong>日期：</strong>${data.date}</p>
                <button class="btn btn-primary" onclick="downloadPDF()">📄 下載 PDF 證書</button>
                <button class="btn btn-outline" onclick="generateESG()">📊 產生 ESG 報告</button>
            </div>
        `;
    });
}

function downloadPDF() {
    const cert = JSON.parse(localStorage.getItem("cert"));
    if (!cert) { alert("請先產生認證"); return; }
    fetch("/download_pdf", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cert)
    }).then(res => res.blob()).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `certificate_${cert.cert_id}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
    });
}

function generateESG() {
    const cert = JSON.parse(localStorage.getItem("cert"));
    if (!cert) { alert("請先產生認證"); return; }
    fetch("/esg_report", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cert.name, carbon_saved: cert.carbon_saved })
    }).then(res => res.json()).then(data => alert(data.report));
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_saved);
        localStorage.setItem("reductionPct", currentResult.reduction_pct);
    }
    window.location = "/certificate_page";
}

function loadHistory() {
    fetch("/get_history").then(res => res.json()).then(data => {
        const tbody = document.getElementById("historyBody");
        if (!tbody) return;
        tbody.innerHTML = "";
        if (data.length === 0) { tbody.innerHTML = '<tr><td colspan="9">暫無歷史記錄</td></tr>'; return; }
        data.reverse().forEach(r => {
            tbody.innerHTML += `<tr><td>${r.date}</td><td>${r.start}</td><td>${r.end}</td><td>${r.containers}</td><td>${r.distance} km</td><td>${r.sea_carbon?.toLocaleString() || '-'} kg</td><td>${r.best_mode}</td><td>${r.carbon_saved?.toLocaleString() || '-'} kg</td><td>${r.reduction_pct || 0}%</td></tr>`;
        });
        drawHistoryChart(data);
    });
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
    fetch("/get_history").then(res => res.json()).then(data => {
        if (data.length === 0) {
            document.getElementById("totalReduction").innerText = "0";
            document.getElementById("avgReduction").innerText = "0%";
            document.getElementById("totalCount").innerText = "0";
            document.getElementById("seaRate").innerText = "0%";
            return;
        }
        const totalCarbon = data.reduce((s, d) => s + (d.carbon_saved || 0), 0);
        const avgPct = data.reduce((s, d) => s + (d.reduction_pct || 0), 0) / data.length;
        const seaCount = data.filter(d => d.best_mode === "海運").length;
        document.getElementById("totalReduction").innerText = Math.round(totalCarbon).toLocaleString();
        document.getElementById("avgReduction").innerText = avgPct.toFixed(1) + "%";
        document.getElementById("totalCount").innerText = data.length;
        document.getElementById("seaRate").innerText = Math.round(seaCount / data.length * 100) + "%";
        new Chart(document.getElementById("trendChart"), {
            type: 'line',
            data: { labels: data.slice(-14).map(d => d.date?.split(' ')[0] || ''), datasets: [{ label: "減碳量 (kg)", data: data.slice(-14).map(d => d.carbon_saved), borderColor: "#0077b6", fill: true }] }
        });
        new Chart(document.getElementById("modeChart"), {
            type: 'doughnut',
            data: { labels: ["海運推薦", "公路推薦"], datasets: [{ data: [seaCount, data.length - seaCount], backgroundColor: ["#00b4d8", "#48cae4"] }] }
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("App loaded");
});