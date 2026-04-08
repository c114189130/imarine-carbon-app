// 全域變數
let currentResult = null;
let currentWeights = { cost: 0.4, carbon: 0.4, risk: 0.2 };

// 頁面導航
function goToResult() {
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;
    const containers = document.getElementById("containers").value;
    const cargoType = document.getElementById("cargoType").value;
    
    if (!containers || containers <= 0) {
        alert("請輸入貨櫃數量");
        return;
    }
    
    localStorage.setItem("start", start);
    localStorage.setItem("end", end);
    localStorage.setItem("containers", containers);
    localStorage.setItem("cargoType", cargoType);
    localStorage.setItem("weights", JSON.stringify(currentWeights));
    window.location = "/result";
}

// 權重控制
function updateWeight(type, value) {
    let numValue = parseFloat(value);
    if (isNaN(numValue)) numValue = 0;
    currentWeights[type] = numValue;
    document.getElementById(`${type}Value`).innerText = Math.round(numValue * 100) + "%";
    
    const total = currentWeights.cost + currentWeights.carbon + currentWeights.risk;
    if (Math.abs(total - 1) > 0.01 && total > 0) {
        currentWeights.cost /= total;
        currentWeights.carbon /= total;
        currentWeights.risk /= total;
        
        const cs = document.getElementById("costSlider");
        const cs2 = document.getElementById("carbonSlider");
        const rs = document.getElementById("riskSlider");
        if (cs) cs.value = currentWeights.cost;
        if (cs2) cs2.value = currentWeights.carbon;
        if (rs) rs.value = currentWeights.risk;
        
        document.getElementById("costValue").innerText = Math.round(currentWeights.cost * 100) + "%";
        document.getElementById("carbonValue").innerText = Math.round(currentWeights.carbon * 100) + "%";
        document.getElementById("riskValue").innerText = Math.round(currentWeights.risk * 100) + "%";
    }
}

function setPreset(preset) {
    const presets = {
        balanced: { cost: 0.33, carbon: 0.34, risk: 0.33 },
        cost: { cost: 0.7, carbon: 0.2, risk: 0.1 },
        green: { cost: 0.2, carbon: 0.7, risk: 0.1 },
        safe: { cost: 0.3, carbon: 0.2, risk: 0.5 }
    };
    const w = presets[preset];
    if (w) {
        currentWeights = w;
        const cs = document.getElementById("costSlider");
        const cs2 = document.getElementById("carbonSlider");
        const rs = document.getElementById("riskSlider");
        if (cs) cs.value = w.cost;
        if (cs2) cs2.value = w.carbon;
        if (rs) rs.value = w.risk;
        document.getElementById("costValue").innerText = Math.round(w.cost * 100) + "%";
        document.getElementById("carbonValue").innerText = Math.round(w.carbon * 100) + "%";
        document.getElementById("riskValue").innerText = Math.round(w.risk * 100) + "%";
    }
}

function initWeightControls() {
    const cs = document.getElementById("costSlider");
    const cs2 = document.getElementById("carbonSlider");
    const rs = document.getElementById("riskSlider");
    
    if (cs) {
        cs.value = currentWeights.cost;
        cs.oninput = (e) => updateWeight('cost', e.target.value);
        document.getElementById("costValue").innerText = Math.round(currentWeights.cost * 100) + "%";
    }
    if (cs2) {
        cs2.value = currentWeights.carbon;
        cs2.oninput = (e) => updateWeight('carbon', e.target.value);
        document.getElementById("carbonValue").innerText = Math.round(currentWeights.carbon * 100) + "%";
    }
    if (rs) {
        rs.value = currentWeights.risk;
        rs.oninput = (e) => updateWeight('risk', e.target.value);
        document.getElementById("riskValue").innerText = Math.round(currentWeights.risk * 100) + "%";
    }
    
    const b = document.getElementById("preset-balanced");
    const c = document.getElementById("preset-cost");
    const g = document.getElementById("preset-green");
    const s = document.getElementById("preset-safe");
    if (b) b.onclick = () => setPreset('balanced');
    if (c) c.onclick = () => setPreset('cost');
    if (g) g.onclick = () => setPreset('green');
    if (s) s.onclick = () => setPreset('safe');
}

// 動畫函數
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
    
    if (seaBar) {
        seaBar.style.width = `${seaPercent}%`;
        seaBar.style.setProperty('--target-width', `${seaPercent}%`);
        seaBar.classList.add('progress-bar-animate');
        setTimeout(() => seaBar.classList.remove('progress-bar-animate'), 1000);
    }
    if (roadBar) {
        roadBar.style.width = `${roadPercent}%`;
    }
}

// 主要計算函數
function calculate() {
    const start = localStorage.getItem("start");
    const end = localStorage.getItem("end");
    const containers = localStorage.getItem("containers");
    const cargoType = localStorage.getItem("cargoType") || "general";
    const weights = JSON.parse(localStorage.getItem("weights") || '{"cost":0.4,"carbon":0.4,"risk":0.2}');
    
    if (!start || !end || !containers) {
        alert("請先返回輸入頁面填寫資料");
        window.location = "/input";
        return;
    }
    
    fetch("/calculate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start, end, containers, cargo_type: cargoType, weights: weights })
    })
    .then(res => res.json())
    .then(data => {
        currentResult = data;
        displayResults(data);
        drawCharts(data);
        
        // 數字跳動動畫 - 貨櫃數量
        const containerElem = document.querySelector(".result-value");
        if (containerElem) {
            animateValue(containerElem, 0, data.containers, 800);
        }
        
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
            <p>${data.cargo_icon} 貨物類型：<strong>${data.cargo_name}</strong></p>
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
        
        <div class="card">
            <h3>🌍 碳排放分析</h3>
            <table class="cost-table">
                <tr><td>🚛 公路碳排放</td><td><strong>${road.carbon.toLocaleString()} kg CO2e</strong></td><td>🔴 基準值</td></tr>
                <tr><td>🚢 海運碳排放</td><td><strong>${sea.carbon.toLocaleString()} kg CO2e</strong></td><td class="savings-number">🟢 減少 ${data.carbon_saved.toLocaleString()} kg (${data.reduction_pct}%)</td></tr>
            </table>
            <div style="margin-top:1rem; padding:1rem; background:var(--light-cyan); border-radius:10px">
                💡 <strong>選擇 ${data.best_mode} 的效益：</strong><br>
                • 節省社會成本：<strong class="savings-number">${formatCurrency(data.social_savings)}</strong><br>
                • 減少碳排放：<strong>${data.carbon_saved.toLocaleString()} kg CO2e</strong><br>
                • 相當於種植 <strong>${Math.ceil(data.carbon_saved / 44)}</strong> 棵樹一年的吸碳量
            </div>
        </div>
    `;
    
    document.getElementById("result").innerHTML = html;
    
    // 即時路況
    if (data.road_condition) {
        const rs = document.getElementById("roadStatus");
        const rsp = document.getElementById("roadSpeed");
        const rsrc = document.getElementById("roadSource");
        if (rs) rs.innerHTML = data.road_condition.level_text;
        if (rsp) rsp.innerHTML = `平均時速 ${data.road_condition.avg_speed} km/h | 延遲倍數 ${data.road_condition.delay_factor}x`;
        if (rsrc) rsrc.innerHTML = `(${data.road_condition.source})`;
    }
    
    // 船期
    if (data.ship_schedule) {
        const ss = document.getElementById("shipStatus");
        const si = document.getElementById("shipInfo");
        if (ss) ss.innerHTML = data.ship_schedule.status;
        if (si) si.innerHTML = `艙位容量 ${data.ship_schedule.available_capacity.toLocaleString()} FEU | ${data.ship_schedule.next_hours} 小時後到港`;
    }
    
    // 調度建議
    if (data.dispatch) {
        const de = document.getElementById("dispatchResult");
        if (de) {
            de.innerHTML = `
                <div style="display:flex; gap:2rem; flex-wrap:wrap">
                    <div style="flex:1">
                        <div class="score-card"><div class="score-number score-sea" id="scoreSea">0</div><div>🚢 海運分數</div></div>
                        <div class="score-card" style="margin-top:0.5rem"><div class="score-number score-road" id="scoreRoad">0</div><div>🚛 公路分數</div></div>
                    </div>
                    <div style="flex:2">
                        <div style="display:flex; gap:1rem; text-align:center; margin-bottom:1rem">
                            <div style="flex:1"><span style="font-size:2rem">🚢</span><br><strong id="seaCount">${data.dispatch.to_sea}</strong> FEU</div>
                            <div style="flex:1"><span style="font-size:2rem">🚛</span><br><strong id="roadCount">${data.dispatch.to_road}</strong> FEU</div>
                        </div>
                        <div class="ratio-bar-container"><div class="ratio-bar-sea" id="ratioBarSea" style="width:0%">🚢 <span id="seaPercent">0</span>%</div></div>
                        <div class="ratio-bar-container"><div class="ratio-bar-road" id="ratioBarRoad" style="width:0%">🚛 <span id="roadPercent">0</span>%</div></div>
                        <p><strong>📌 決策原因：</strong><br>${data.dispatch.reason}</p>
                    </div>
                </div>
            `;
            
            // 觸發動畫
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

function drawCharts(data) {
    // 成本圖表
    new Chart(document.getElementById("costChart"), {
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
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } } }
    });
    
    // 社會成本圖表
    new Chart(document.getElementById("socialChart"), {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{ label: '社會外部成本 (NTD)', data: [data.road.social, data.sea.social], backgroundColor: ['rgba(231,76,60,0.7)', 'rgba(46,204,113,0.7)'] }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } } }
    });
    
    // VSL 圖表
    new Chart(document.getElementById("vslChart"), {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{ label: 'VSL 人命風險成本 (NTD)', data: [data.road.vsl, data.sea.vsl], backgroundColor: ['rgba(231,76,60,0.7)', 'rgba(46,204,113,0.7)'] }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } } }
    });
    
    // 時間成本圖表
    new Chart(document.getElementById("timeChart"), {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{ label: '時間成本 (NTD)', data: [data.road.time, data.sea.time], backgroundColor: ['rgba(52,152,219,0.7)', 'rgba(241,196,15,0.7)'] }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } } }
    });
    
    // 碳排放圖表
    new Chart(document.getElementById("carbonChart"), {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{ label: '碳排放量 (kg CO2e)', data: [data.road.carbon, data.sea.carbon], backgroundColor: ['rgba(231,76,60,0.7)', 'rgba(46,204,113,0.7)'] }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: 'kg CO2e' } } } }
    });
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

// 歷史記錄
function loadHistory() {
    fetch("/get_history")
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("historyBody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10">暫無歷史記錄</td></tr>';
                return;
            }
            
            data.reverse().forEach(r => {
                tbody.innerHTML += `<tr>
                    <td>${r.date}</td>
                    <td>${r.start}</td>
                    <td>${r.end}</td>
                    <td>${r.containers}</td>
                    <td>${r.cargo_type || '-'}</td>
                    <td>${r.distance} km</td>