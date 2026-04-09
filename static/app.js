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

function updateRatioBar(seaPercent, roadPercent) {
    const seaBar = document.getElementById("ratioBarSea");
    const roadBar = document.getElementById("ratioBarRoad");
    if (seaBar) seaBar.style.width = `${seaPercent}%`;
    if (roadBar) roadBar.style.width = `${roadPercent}%`;
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
        document.getElementById("loading").style.display = "none";
        document.getElementById("content").style.display = "block";
    })
    .catch(err => {
        console.error("Error:", err);
        document.getElementById("loading").innerHTML = '<div class="card" style="text-align:center"><div style="color:red">計算失敗：' + err.message + '</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回重新輸入</button></div>';
    });
}

function formatCurrency(v) {
    return "NT$ " + v.toLocaleString();
}

function displayResults(data) {
    const road = data.road;
    const sea = data.sea;
    
    let html = `
        <div class="result-card">
            <h3>📊 AI 多因子決策分析報告</h3>
            <p>🚢 起點：${data.start_name} → 🏁 終點：${data.end_name}</p>
            <p>📏 距離：<span class="result-value">${data.distance.toLocaleString()}</span> 公里</p>
            <p>📦 貨櫃數量：<span class="result-value">${data.containers.toLocaleString()}</span> FEU</p>
            <div style="margin-top:1rem; padding:1rem; background:rgba(255,255,255,0.2); border-radius:10px">
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
    
    // 即時路況
    if (data.road_condition) {
        const rs = document.getElementById("roadStatus");
        const rsp = document.getElementById("roadSpeed");
        const rsrc = document.getElementById("roadSource");
        const cb = document.getElementById("congestionBar");
        if (rs) rs.innerHTML = data.road_condition.level_text;
        if (rsp) rsp.innerHTML = `平均時速 ${data.road_condition.avg_speed} km/h | 延遲倍數 ${data.road_condition.delay_factor}x`;
        if (rsrc) rsrc.innerHTML = `資料來源：${data.road_condition.source}`;
        if (cb) {
            let width = data.road_condition.level === "high" ? 80 : data.road_condition.level === "medium" ? 50 : 20;
            cb.style.width = `${width}%`;
        }
    }
    
    // 船期
    if (data.ship_schedule) {
        const sn = document.getElementById("shipName");
        const sd = document.getElementById("shipDest");
        const se = document.getElementById("shipEta");
        const sc = document.getElementById("shipCapacity");
        const st = document.getElementById("shipType");
        if (sn) sn.innerHTML = data.ship_schedule.name;
        if (sd) sd.innerHTML = data.ship_schedule.destination;
        if (se) se.innerHTML = data.ship_schedule.eta_hours;
        if (sc) sc.innerHTML = data.ship_schedule.available;
        if (st) st.innerHTML = data.ship_schedule.type;
    }
    
    // 指派建議
    if (data.dispatch) {
        const de = document.getElementById("dispatchResult");
        if (de) {
            let reasonsHtml = data.dispatch.reasons.map(r => `<li>${r}</li>`).join('');
            de.innerHTML = `
                <div style="display:flex; gap:2rem; flex-wrap:wrap">
                    <div style="flex:1">
                        <div class="score-card" style="background:rgba(255,255,255,0.2)">
                            <div class="score-number" id="scoreSea" style="color:white">0</div>
                            <div>🚢 海運分數</div>
                        </div>
                        <div class="score-card" style="background:rgba(255,255,255,0.2); margin-top:0.5rem">
                            <div class="score-number" id="scoreRoad" style="color:white">0</div>
                            <div>🚛 公路分數</div>
                        </div>
                    </div>
                    <div style="flex:2">
                        <div style="background:rgba(255,255,255,0.2); border-radius:15px; padding:1rem; margin-bottom:1rem">
                            <p style="font-size:1.2rem; font-weight:bold">${data.dispatch.action}</p>
                            <p>${data.dispatch.suggestion}</p>
                        </div>
                        <div style="display:flex; gap:1rem; text-align:center; margin-bottom:1rem">
                            <div style="flex:1"><span style="font-size:2rem">🚢</span><br><strong id="seaCount">${data.dispatch.to_sea}</strong> FEU</div>
                            <div style="flex:1"><span style="font-size:2rem">🚛</span><br><strong id="roadCount">${data.dispatch.to_road}</strong> FEU</div>
                        </div>
                        <div class="ratio-bar-container"><div class="ratio-bar-sea" id="ratioBarSea" style="width:0%">🚢 <span id="seaPercent">0</span>%</div></div>
                        <div class="ratio-bar-container"><div class="ratio-bar-road" id="ratioBarRoad" style="width:0%">🚛 <span id="roadPercent">0</span>%</div></div>
                        <div style="background:rgba(255,255,255,0.2); border-radius:15px; padding:1rem; margin-top:1rem">
                            <p style="font-weight:bold">📌 詳細分析：</p>
                            <ul>${reasonsHtml}</ul>
                        </div>
                    </div>
                </div>
            `;
            
            setTimeout(() => {
                animateValue(document.getElementById("scoreSea"), 0, data.dispatch.score_sea, 600);
                animateValue(document.getElementById("scoreRoad"), 0, data.dispatch.score_road, 600);
                animateValue(document.getElementById("seaCount"), 0, data.dispatch.to_sea, 600);
                animateValue(document.getElementById("roadCount"), 0, data.dispatch.to_road, 600);
                updateRatioBar(data.dispatch.ratio, 100 - data.dispatch.ratio);
                const sp = document.getElementById("seaPercent");
                const rp = document.getElementById("roadPercent");
                if (sp) sp.innerText = data.dispatch.ratio;
                if (rp) rp.innerText = (100 - data.dispatch.ratio).toFixed(1);
            }, 100);
        }
    }
}

function drawMap(data) {
    const mapDiv = document.getElementById("map");
    if (!mapDiv) return;
    
    if (typeof L === 'undefined') {
        mapDiv.innerHTML = '<div style="padding:20px; text-align:center">地圖載入中...</div>';
        return;
    }
    
    const startLat = data.start_lat;
    const startLon = data.start_lon;
    const endLat = data.end_lat;
    const endLon = data.end_lon;
    
    const map = L.map('map').setView([(startLat + endLat) / 2, (startLon + endLon) / 2], 8);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
    }).addTo(map);
    
    const latlngs = [[startLat, startLon], [endLat, endLon]];
    L.polyline(latlngs, { color: '#0077b6', weight: 5, opacity: 0.8, dashArray: '10, 10' }).addTo(map);
    
    const startIcon = L.divIcon({ html: '🚢', className: 'custom-icon', iconSize: [30, 30] });
    L.marker([startLat, startLon], { icon: startIcon }).bindPopup(`<b>起點：${data.start_name}</b>`).addTo(map);
    
    const endIcon = L.divIcon({ html: '🏁', className: 'custom-icon', iconSize: [30, 30] });
    L.marker([endLat, endLon], { icon: endIcon }).bindPopup(`<b>終點：${data.end_name}</b>`).addTo(map);
    
    map.fitBounds(L.latLngBounds(latlngs));
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
    })
    .then(res => res.blob())
    .then(blob => {
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
    })
    .then(res => res.json())
    .then(data => alert(data.report));
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_saved);
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
            
            data.reverse().forEach(r => {
                tbody.innerHTML += `<tr>
                    <td>${r.date}</td>
                    <td>${r.start}</td><td>${r.end}</td>
                    <td>${r.containers}</td><td>${r.distance} km</td>
                    <td>${r.sea_carbon?.toLocaleString() || '-'} kg</td>
                    <td>${r.best_mode}</td>
                    <td>${r.carbon_saved?.toLocaleString() || '-'} kg</td>
                    <td>${r.reduction_pct || 0}%</td>
                </tr>`;
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
            const totalCarbon = data.reduce((s, d) => s + (d.carbon_saved || 0), 0);
            const avgPct = data.reduce((s, d) => s + (d.reduction_pct || 0), 0) / data.length;
            const seaCount = data.filter(d => d.best_mode === "海運").length;
            
            document.getElementById("totalReduction").innerText = Math.round(totalCarbon).toLocaleString();
            document.getElementById("avgReduction").innerText = avgPct.toFixed(1) + "%";
            document.getElementById("totalCount").innerText = data.length;
            document.getElementById("seaRate").innerText = Math.round(seaCount / data.length * 100) + "%";
            
            const trendCtx = document.getElementById("trendChart");
            if (trendCtx) {
                new Chart(trendCtx, {
                    type: 'line',
                    data: {
                        labels: data.slice(-14).map(d => d.date?.split(' ')[0] || ''),
                        datasets: [{ label: "減碳量 (kg)", data: data.slice(-14).map(d => d.carbon_saved), borderColor: "#0077b6", fill: true }]
                    }
                });
            }
            
            const modeCtx = document.getElementById("modeChart");
            if (modeCtx) {
                new Chart(modeCtx, {
                    type: 'doughnut',
                    data: { labels: ["海運推薦", "公路推薦"], datasets: [{ data: [seaCount, data.length - seaCount], backgroundColor: ["#00b4d8", "#48cae4"] }] }
                });
            }
        });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("App loaded");
});
// ================= 即時動態路網（1968 等級） =================

let mapInstance = null;
let trafficLayers = [];
let animationMarkers = [];
let trafficUpdateInterval = null;
let routePolyline = null;

// 初始化地圖（升級版）
function initMap(centerLat, centerLon, zoom = 7) {
    // 如果已有地圖實例，先清除
    if (mapInstance) {
        // 清除圖層
        if (trafficLayers.length > 0) {
            trafficLayers.forEach(layer => {
                if (mapInstance.hasLayer(layer)) mapInstance.removeLayer(layer);
            });
        }
        if (animationMarkers.length > 0) {
            animationMarkers.forEach(marker => {
                if (mapInstance.hasLayer(marker)) mapInstance.removeLayer(marker);
            });
        }
        mapInstance.remove();
    }
    
    // 建立新地圖
    mapInstance = L.map('map').setView([centerLat, centerLon], zoom);
    
    // 使用 CartoDB 淺色底圖（乾淨好看）
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
        minZoom: 3
    }).addTo(mapInstance);
    
    return mapInstance;
}

// 載入即時路網並繪製（含動畫）
async function loadTrafficNetwork() {
    try {
        const response = await fetch("/api/traffic");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const roads = await response.json();
        
        // 清除舊圖層
        if (trafficLayers.length > 0) {
            trafficLayers.forEach(layer => {
                if (mapInstance && mapInstance.hasLayer(layer)) mapInstance.removeLayer(layer);
            });
            trafficLayers = [];
        }
        
        if (animationMarkers.length > 0) {
            animationMarkers.forEach(marker => {
                if (mapInstance && mapInstance.hasLayer(marker)) mapInstance.removeLayer(marker);
            });
            animationMarkers = [];
        }
        
        // 繪製每條路段
        roads.forEach(road => {
            if (!road.coords || road.coords.length < 2) return;
            
            // 繪製路線（根據速度決定顏色）
            const polyline = L.polyline(road.coords, {
                color: road.color || (road.speed >= 60 ? "#27ae60" : road.speed >= 35 ? "#f39c12" : "#e74c3c"),
                weight: 5,
                opacity: 0.85,
                smoothFactor: 1
            }).addTo(mapInstance);
            
            trafficLayers.push(polyline);
            
            // 加上車流動畫（速度越慢動畫越慢）
            animateTrafficOnRoad(road.coords, road.speed, road.color);
        });
        
        // 更新壅塞統計面板
        updateCongestionStats(roads);
        
    } catch (error) {
        console.error("載入即時路網失敗:", error);
    }
}

// 在路段上產生動畫車輛
function animateTrafficOnRoad(coords, speed, roadColor) {
    if (!coords || coords.length < 2) return;
    
    // 計算路段總長度（決定要放幾台車）
    let totalLength = 0;
    for (let i = 0; i < coords.length - 1; i++) {
        const p1 = coords[i];
        const p2 = coords[i + 1];
        const d = Math.sqrt(Math.pow(p2[0] - p1[0], 2) + Math.pow(p2[1] - p1[1], 2));
        totalLength += d;
    }
    
    // 根據路段長度和速度決定車輛數量（3-8台）
    const vehicleCount = Math.min(8, Math.max(3, Math.floor(totalLength * 15)));
    
    // 根據速度決定動畫延遲（速度越快，車移動越快）
    const moveDelay = Math.max(30, Math.min(150, 200 - speed * 2));
    
    for (let v = 0; v < vehicleCount; v++) {
        // 隨機起始位置
        let startIndex = Math.floor(Math.random() * (coords.length - 1));
        let progress = Math.random();
        
        // 計算起始點座標
        const start = coords[startIndex];
        const end = coords[startIndex + 1];
        const startLat = start[0] + (end[0] - start[0]) * progress;
        const startLon = start[1] + (end[1] - start[1]) * progress;
        
        // 創建車輛標記（小圓圈）
        const vehicleMarker = L.circleMarker([startLat, startLon], {
            radius: 5,
            color: "#000",
            weight: 1,
            fillColor: roadColor === "#27ae60" ? "#2ecc71" : (roadColor === "#f39c12" ? "#f1c40f" : "#e74c3c"),
            fillOpacity: 1,
            className: "vehicle-marker"
        }).addTo(mapInstance);
        
        animationMarkers.push(vehicleMarker);
        
        // 車輛動畫移動
        let currentSegmentIndex = startIndex;
        let currentProgress = progress;
        
        function moveVehicle() {
            if (currentSegmentIndex >= coords.length - 1) {
                currentSegmentIndex = 0;
                currentProgress = 0;
            }
            
            const segStart = coords[currentSegmentIndex];
            const segEnd = coords[currentSegmentIndex + 1];
            
            currentProgress += 0.03;
            
            if (currentProgress >= 1) {
                currentProgress = 0;
                currentSegmentIndex++;
                
                if (currentSegmentIndex >= coords.length - 1) {
                    currentSegmentIndex = 0;
                }
            }
            
            const lat = segStart[0] + (segEnd[0] - segStart[0]) * currentProgress;
            const lon = segStart[1] + (segEnd[1] - segStart[1]) * currentProgress;
            
            vehicleMarker.setLatLng([lat, lon]);
            
            setTimeout(moveVehicle, moveDelay);
        }
        
        // 隨機延遲啟動，讓車輛不同步
        setTimeout(moveVehicle, v * 300);
    }
}

// 更新壅塞統計面板
function updateCongestionStats(roads) {
    let totalSpeed = 0;
    let congestedCount = 0;
    let smoothCount = 0;
    
    roads.forEach(road => {
        totalSpeed += road.speed;
        if (road.speed < 35) congestedCount++;
        if (road.speed >= 60) smoothCount++;
    });
    
    const avgSpeed = roads.length > 0 ? (totalSpeed / roads.length).toFixed(1) : 0;
    
    // 更新面板（如果存在的話）
    const statsPanel = document.getElementById("trafficStats");
    if (statsPanel) {
        statsPanel.innerHTML = `
            <div style="display:flex; gap:1rem; justify-content:space-around">
                <div style="text-align:center">
                    <div style="font-size:1.5rem; font-weight:bold">${avgSpeed}</div>
                    <div style="font-size:0.8rem">平均車速 (km/h)</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:1.5rem; font-weight:bold; color:#e74c3c">${congestedCount}</div>
                    <div style="font-size:0.8rem">壅塞路段</div>
                </div>
                <div style="text-align:center">
                    <div style="font-size:1.5rem; font-weight:bold; color:#27ae60">${smoothCount}</div>
                    <div style="font-size:0.8rem">順暢路段</div>
                </div>
            </div>
        `;
    }
}

// 開始自動更新路況（每 30 秒）
function startTrafficAutoUpdate() {
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    
    // 立即載入一次
    loadTrafficNetwork();
    
    // 每 30 秒更新
    trafficUpdateInterval = setInterval(() => {
        console.log("🔄 更新即時路況...");
        loadTrafficNetwork();
    }, 30000);
}

// 停止自動更新
function stopTrafficAutoUpdate() {
    if (trafficUpdateInterval) {
        clearInterval(trafficUpdateInterval);
        trafficUpdateInterval = null;
    }
}

// 修改原有的 drawMap 函數（使用新版地圖）
function drawMap(data) {
    const centerLat = (data.start_lat + data.end_lat) / 2;
    const centerLon = (data.start_lon + data.end_lon) / 2;
    
    // 初始化地圖
    initMap(centerLat, centerLon);
    
    // 繪製港口路線
    const latlngs = [
        [data.start_lat, data.start_lon],
        [data.end_lat, data.end_lon]
    ];
    
    routePolyline = L.polyline(latlngs, { 
        color: '#0077b6', 
        weight: 4, 
        opacity: 0.9,
        dashArray: '8, 8'
    }).addTo(mapInstance);
    
    // 起點標記
    const startIcon = L.divIcon({ 
        html: '<div style="font-size:24px">🚢</div>', 
        className: 'custom-icon',
        iconSize: [30, 30]
    });
    L.marker([data.start_lat, data.start_lon], { icon: startIcon })
        .bindPopup(`<b>起點：${data.start_name}</b>`)
        .addTo(mapInstance);
    
    // 終點標記
    const endIcon = L.divIcon({ 
        html: '<div style="font-size:24px">🏁</div>', 
        className: 'custom-icon',
        iconSize: [30, 30]
    });
    L.marker([data.end_lat, data.end_lon], { icon: endIcon })
        .bindPopup(`<b>終點：${data.end_name}</b>`)
        .addTo(mapInstance);
    
    // 調整地圖視野
    mapInstance.fitBounds(L.latLngBounds(latlngs));
    
    // 啟動即時路網
    startTrafficAutoUpdate();
}