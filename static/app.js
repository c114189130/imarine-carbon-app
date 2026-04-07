// 全域變數
let currentResult = null;
let currentWeights = { cost: 0.4, carbon: 0.4, risk: 0.2 };

// ================= 頁面導航 =================
function goToInput() {
    window.location = "/input";
}

function goToResult() {
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;
    const containers = document.getElementById("containers").value;
    const cargoType = document.getElementById("cargoType").value;
    
    if (!containers || containers <= 0) {
        alert("請輸入貨櫃數量（至少 1 TEU）");
        return;
    }
    
    localStorage.setItem("start", start);
    localStorage.setItem("end", end);
    localStorage.setItem("containers", containers);
    localStorage.setItem("cargoType", cargoType);
    window.location = "/result";
}

// ================= AI 權重控制 =================
function updateWeight(type, value) {
    let numValue = parseFloat(value);
    if (isNaN(numValue)) numValue = 0;
    
    currentWeights[type] = numValue;
    
    const percent = Math.round(numValue * 100);
    document.getElementById(`${type}Value`).innerText = percent + "%";
    
    const total = currentWeights.cost + currentWeights.carbon + currentWeights.risk;
    
    if (Math.abs(total - 1) > 0.01 && total > 0) {
        currentWeights.cost = currentWeights.cost / total;
        currentWeights.carbon = currentWeights.carbon / total;
        currentWeights.risk = currentWeights.risk / total;
        
        const costSlider = document.getElementById("costSlider");
        const carbonSlider = document.getElementById("carbonSlider");
        const riskSlider = document.getElementById("riskSlider");
        
        if (costSlider) costSlider.value = currentWeights.cost;
        if (carbonSlider) carbonSlider.value = currentWeights.carbon;
        if (riskSlider) riskSlider.value = currentWeights.risk;
        
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
        
        const costSlider = document.getElementById("costSlider");
        const carbonSlider = document.getElementById("carbonSlider");
        const riskSlider = document.getElementById("riskSlider");
        
        if (costSlider) costSlider.value = w.cost;
        if (carbonSlider) carbonSlider.value = w.carbon;
        if (riskSlider) riskSlider.value = w.risk;
        
        document.getElementById("costValue").innerText = Math.round(w.cost * 100) + "%";
        document.getElementById("carbonValue").innerText = Math.round(w.carbon * 100) + "%";
        document.getElementById("riskValue").innerText = Math.round(w.risk * 100) + "%";
    }
}

function initWeightControls() {
    const costSlider = document.getElementById("costSlider");
    const carbonSlider = document.getElementById("carbonSlider");
    const riskSlider = document.getElementById("riskSlider");
    
    if (costSlider) {
        costSlider.value = currentWeights.cost;
        costSlider.oninput = function(e) { updateWeight('cost', e.target.value); };
        document.getElementById("costValue").innerText = Math.round(currentWeights.cost * 100) + "%";
    }
    
    if (carbonSlider) {
        carbonSlider.value = currentWeights.carbon;
        carbonSlider.oninput = function(e) { updateWeight('carbon', e.target.value); };
        document.getElementById("carbonValue").innerText = Math.round(currentWeights.carbon * 100) + "%";
    }
    
    if (riskSlider) {
        riskSlider.value = currentWeights.risk;
        riskSlider.oninput = function(e) { updateWeight('risk', e.target.value); };
        document.getElementById("riskValue").innerText = Math.round(currentWeights.risk * 100) + "%";
    }
    
    const balancedBtn = document.getElementById("preset-balanced");
    const costBtn = document.getElementById("preset-cost");
    const greenBtn = document.getElementById("preset-green");
    const safeBtn = document.getElementById("preset-safe");
    
    if (balancedBtn) balancedBtn.onclick = function() { setPreset('balanced'); };
    if (costBtn) costBtn.onclick = function() { setPreset('cost'); };
    if (greenBtn) greenBtn.onclick = function() { setPreset('green'); };
    if (safeBtn) safeBtn.onclick = function() { setPreset('safe'); };
}

// ================= 計算與顯示 =================
function calculate() {
    const start = localStorage.getItem("start");
    const end = localStorage.getItem("end");
    const containers = localStorage.getItem("containers");
    const cargoType = localStorage.getItem("cargoType") || "general";

    if (!start || !end || !containers) {
        alert("請先返回輸入頁面填寫資料");
        window.location = "/input";
        return;
    }

    showLoading();
    
    fetch("/calculate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start, end, containers, cargo_type: cargoType, weights: currentWeights })
    })
    .then(res => res.json())
    .then(data => {
        currentResult = data;
        displayResults(data);
        drawComparisonChart(data);
        drawSocialCostChart(data);
        drawVSLChart(data);
        drawTimeCostChart(data);
        drawCarbonChart(data);
        hideLoading();
    })
    .catch(err => {
        console.error("Error:", err);
        hideLoading();
        alert("計算失敗：" + err.message);
    });
}

function showLoading() {
    const resultDiv = document.getElementById("result");
    if (resultDiv) {
        resultDiv.innerHTML = '<div class="card" style="text-align:center"><div class="animate-pulse">🔄 AI 分析中，請稍候...</div></div>';
    }
}

function hideLoading() {}

function displayResults(data) {
    const resultDiv = document.getElementById("result");
    if (!resultDiv) return;
    
    resultDiv.innerHTML = `
        <div class="result-card">
            <h3>📊 AI 多目標決策分析報告</h3>
            <p>🚢 起點：${data.start_name} → 🏁 終點：${data.end_name}</p>
            <p>📏 距離：<span class="result-value">${data.distance.toLocaleString()}</span> 公里</p>
            <p>📦 貨櫃數量：<span class="result-value">${data.containers.toLocaleString()}</span> TEU</p>
            <p>${data.cargo_icon || '📦'} 貨物類型：<strong>${data.cargo_type}</strong></p>
            <div style="margin-top:1rem; padding:1rem; background:rgba(255,255,255,0.2); border-radius:10px">
                🤖 <strong>AI 推薦方案：${data.best_mode}</strong><br>
                綜合評分：公路 ${data.all_scores?.road || 'N/A'} / 海運 ${data.all_scores?.sea || 'N/A'}
            </div>
        </div>
        
        <div class="card">
            <h3>💰 總體社會成本分析</h3>
            <table class="cost-table">
                <thead><tr><th>成本項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th><th>節省金額</th></tr></thead>
                <tbody>
                    <tr><td><strong>💰 運費 (NTD)</strong></td><td>${formatCurrency(data.road.freight)}</td><td>${formatCurrency(data.sea.freight)}</td>
                    <td class="${data.road.freight > data.sea.freight ? 'savings-number' : ''}">${formatCurrency(data.road.freight - data.sea.freight)}</td></tr>
                    <tr><td><strong>⏳ 時間成本 (NTD)</strong></td><td>${formatCurrency(data.road.time)}</td><td>${formatCurrency(data.sea.time)}</td>
                    <td>${formatCurrency(data.road.time - data.sea.time)}</td></tr>
                    <tr><td><strong>🏛️ 社會成本 (NTD)</strong></td><td>${formatCurrency(data.road.social)}</td><td>${formatCurrency(data.sea.social)}</td>
                    <td class="savings-number">${formatCurrency(data.road.social - data.sea.social)}</td></tr>
                    <tr><td><strong>⚠️ VSL人命風險 (NTD)</strong></td><td>${formatCurrency(data.road.vsl)}</td><td>${formatCurrency(data.sea.vsl)}</td>
                    <td class="savings-number">${formatCurrency(data.road.vsl - data.sea.vsl)}</td></tr>
                    <tr style="background: var(--light-cyan); font-weight: bold;">
                        <td><strong>📊 總社會成本 (NTD)</strong></td>
                        <td>${formatCurrency(data.road.total)}</td>
                        <td>${formatCurrency(data.sea.total)}</td>
                        <td class="savings-number">${formatCurrency(data.social_savings)}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="card" style="background: var(--light-cyan);">
            <h3>🤖 AI 決策分析</h3>
            <p>📌 貨物類型：${data.cargo_type}</p>
            <p>${data.recommendation_reason || '請查看上方圖表分析'}</p>
            <p style="margin-top:0.5rem; font-size:0.9rem">💡 時間敏感度：${Math.round(data.time_sensitivity * 100)}%</p>
        </div>
        
        <div class="card">
            <h3>📊 運輸模式優劣勢總結</h3>
            <table class="cost-table">
                <thead><tr><th>評估項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th></tr></thead>
                <tbody>
                    <tr><td>💰 運費</td><td class="劣势">較高 💸</td><td class="优势">較低 ✅</td></tr>
                    <tr><td>⏱️ 運輸時間</td><td class="优势">快 (4-6小時) ✅</td><td class="劣势">慢 (18-24小時) ⚠️</td></tr>
                    <tr><td>🏛️ 社會成本</td><td class="劣势">高 (事故/空污) ❌</td><td class="优势">低 ✅</td></tr>
                    <tr><td>⚠️ VSL人命風險</td><td class="劣势">高 (事故率高) ❌</td><td class="优势">低 ✅</td></tr>
                    <tr><td>🌱 碳排放</td><td class="劣势">高 (0.12 kg/TEU-km) ❌</td><td class="优势">低 (0.04 kg/TEU-km) ✅</td></tr>
                    <tr><td>🚪 門到門服務</td><td class="优势">可直達 ✅</td><td class="劣势">需轉運 ⚠️</td></tr>
                </tbody>
            </table>
            <p style="margin-top:1rem; font-size:0.9rem">
                💡 <strong>決策建議：</strong>
                ${data.best_mode === "海運" ? 
                    "海運在成本、環保、安全面具有優勢，適合大宗、低時效性貨物。" : 
                    "公路在時效性和靈活性上勝出，適合高價值、急迫性貨物。"}
            </p>
        </div>
    `;
}

function formatCurrency(value) {
    return `NT$ ${value.toLocaleString()}`;
}

// 成本比較圖表（運費 + 社會成本 + VSL + 時間成本）
function drawComparisonChart(data) {
    const ctx = document.getElementById("comparisonChart");
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [
                { label: '運費 (NTD)', data: [data.road.freight, data.sea.freight], backgroundColor: 'rgba(0, 119, 182, 0.7)', borderRadius: 10 },
                { label: '社會成本 (NTD)', data: [data.road.social, data.sea.social], backgroundColor: 'rgba(0, 180, 216, 0.7)', borderRadius: 10 },
                { label: 'VSL風險成本 (NTD)', data: [data.road.vsl, data.sea.vsl], backgroundColor: 'rgba(72, 202, 228, 0.7)', borderRadius: 10 },
                { label: '時間成本 (NTD)', data: [data.road.time, data.sea.time], backgroundColor: 'rgba(144, 224, 239, 0.7)', borderRadius: 10 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { position: 'top' } },
            scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } }
        }
    });
}

// 社會成本獨立圖表
function drawSocialCostChart(data) {
    const ctx = document.getElementById("socialCostChart");
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{
                label: '社會外部成本 (NTD)',
                data: [data.road.social, data.sea.social],
                backgroundColor: ['rgba(231, 76, 60, 0.7)', 'rgba(46, 204, 113, 0.7)'],
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `NT$ ${context.raw.toLocaleString()}`;
                        },
                        afterBody: function() {
                            return [
                                '包含：空氣污染、噪音、肇事成本、溫室效應',
                                '公路劣勢：事故率高、空污嚴重、噪音污染'
                            ];
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } }
        }
    });
}

// VSL 人命風險成本獨立圖表
function drawVSLChart(data) {
    const ctx = document.getElementById("vslChart");
    if (!ctx) return;
    
    const vslRatio = (data.road.vsl / data.sea.vsl).toFixed(1);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{
                label: 'VSL 人命風險成本 (NTD)',
                data: [data.road.vsl, data.sea.vsl],
                backgroundColor: ['rgba(231, 76, 60, 0.7)', 'rgba(46, 204, 113, 0.7)'],
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `NT$ ${context.raw.toLocaleString()}`;
                        },
                        afterBody: function() {
                            return [
                                'VSL統計生命價值：NT$5,000萬元',
                                '公路事故發生率：1.36e-8 (每延車公里)',
                                '海運事故發生率：1.8e-9',
                                `→ 公路人命風險成本約為海運的 ${vslRatio} 倍`
                            ];
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } }
        }
    });
}

// 時間成本獨立圖表
function drawTimeCostChart(data) {
    const ctx = document.getElementById("timeCostChart");
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{
                label: '時間成本 (NTD)',
                data: [data.road.time, data.sea.time],
                backgroundColor: ['rgba(52, 152, 219, 0.7)', 'rgba(241, 196, 15, 0.7)'],
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `NT$ ${context.raw.toLocaleString()}`;
                        },
                        afterBody: function(context) {
                            const isRoad = context[0].datasetIndex === 0;
                            if (isRoad) {
                                return [
                                    '公路優勢：運輸時間短，資金佔用成本低',
                                    '貨物價值：NT$500萬/TEU',
                                    '年利率：5%'
                                ];
                            } else {
                                return [
                                    '海運劣勢：運輸時間長，資金佔用成本高',
                                    '適合低時間敏感度貨物（如大宗原物料）',
                                    `當前貨物時間敏感度：${Math.round(data.time_sensitivity * 100)}%`
                                ];
                            }
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true, title: { display: true, text: '成本 (NTD)' } } }
        }
    });
}

// 碳排放圖表
function drawCarbonChart(data) {
    const ctx = document.getElementById("carbonChart");
    if (!ctx) return;
    
    const carbonRatio = (data.road.carbon / data.sea.carbon).toFixed(1);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['公路運輸', '海運運輸'],
            datasets: [{
                label: '碳排放量 (kg CO2e)',
                data: [data.road.carbon, data.sea.carbon],
                backgroundColor: ['rgba(231, 76, 60, 0.7)', 'rgba(46, 204, 113, 0.7)'],
                borderRadius: 10
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw.toLocaleString()} kg CO2e`;
                        },
                        afterBody: function() {
                            const saved = data.carbon_saved;
                            const pct = data.carbon_reduction_pct;
                            return [
                                `公路碳排放強度：0.12 kg/TEU-km`,
                                `海運碳排放強度：0.04 kg/TEU-km`,
                                `→ 公路碳排約為海運的 ${carbonRatio} 倍`,
                                `選擇海運可減少 ${saved.toLocaleString()} kg (${pct}%)`
                            ];
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true, title: { display: true, text: 'kg CO2e' } } }
        }
    });
}

// ================= 認證功能 =================
function generateCertificate() {
    const name = document.getElementById("name").value;
    const carbonSaved = localStorage.getItem("savedCO2") || 0;
    const carbonReductionPct = localStorage.getItem("carbonReductionPct") || 0;
    
    if (!name) { alert("請輸入公司名稱"); return; }
    
    fetch("/certificate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, carbon_saved: parseFloat(carbonSaved), carbon_reduction_pct: parseFloat(carbonReductionPct) })
    })
    .then(res => res.json())
    .then(data => {
        localStorage.setItem("cert", JSON.stringify(data));
        const certDiv = document.getElementById("certResult");
        if (certDiv) {
            certDiv.innerHTML = `
                <div class="card" style="text-align:center">
                    <h3>✅ 碳排認證已產生</h3>
                    <p><strong>公司：</strong>${data.name}</p>
                    <p><strong>編號：</strong>${data.cert_id}</p>
                    <p><strong>日期：</strong>${data.date}</p>
                    <button class="btn btn-primary" onclick="downloadCertificatePDF()">📄 下載 PDF 證書</button>
                    <button class="btn btn-outline" onclick="generateESGReport()">📊 產生 ESG 報告</button>
                </div>
            `;
        }
    })
    .catch(err => {
        console.error("Error:", err);
        alert("產生認證失敗：" + err.message);
    });
}

function downloadCertificatePDF() {
    const cert = JSON.parse(localStorage.getItem("cert"));
    if (!cert) { alert("請先產生認證"); return; }
    
    fetch("/download_pdf", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cert)
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `certificate_${cert.cert_id}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(err => {
        console.error("Error:", err);
        alert("下載失敗：" + err.message);
    });
}

function generateESGReport() {
    const cert = JSON.parse(localStorage.getItem("cert"));
    if (!cert) { alert("請先產生認證"); return; }
    
    fetch("/esg_report", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cert.name, carbon_saved: cert.carbon_saved })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.report);
    })
    .catch(err => {
        console.error("Error:", err);
        alert("產生 ESG 報告失敗");
    });
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_saved);
        localStorage.setItem("carbonReductionPct", currentResult.carbon_reduction_pct);
    }
    window.location = "/certificate_page";
}

// ================= 歷史記錄 =================
function loadHistory() {
    fetch("/get_history")
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("history-body");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (data.length === 0) { 
                tbody.innerHTML = '<tr><td colspan="10">暫無歷史記錄</td></tr>'; 
                return; 
            }
            
            data.reverse().forEach(record => {
                tbody.innerHTML += `<tr>
                    <td>${record.date}</td>
                    <td>${record.start}</td>
                    <td>${record.end}</td>
                    <td>${record.containers}</td>
                    <td>${record.cargo_type || '-'}</td>
                    <td>${record.distance} km</td>
                    <td>${record.sea_carbon?.toLocaleString() || '-'} kg</td>
                    <td>${record.best_mode}</td>
                    <td>${record.carbon_saved?.toLocaleString() || '-'} kg</td>
                    <td>${record.carbon_reduction_pct || 0}%</td>
                </tr>`;
            });
            drawHistoryChart(data);
        })
        .catch(err => console.error("Error:", err));
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
                { label: '公路碳排 (kg CO2e)', data: last7.map(h => h.road_carbon || 0), borderColor: '#e74c3c', tension: 0.4, fill: true },
                { label: '海運碳排 (kg CO2e)', data: last7.map(h => h.sea_carbon || 0), borderColor: '#0077b6', tension: 0.4, fill: true }
            ]
        },
        options: { responsive: true }
    });
}

function loadDashboard() {
    fetch("/get_history").then(r=>r.json()).then(data=>{
        if(data.length===0) {
            document.getElementById("totalReduction").innerText = "0";
            document.getElementById("avgReduction").innerText = "0%";
            document.getElementById("totalCalculations").innerText = "0";
            document.getElementById("bestModeRate").innerText = "0%";
            return;
        }
        const totalCarbon = data.reduce((s,d)=>s+(d.carbon_saved||0),0);
        const avgPct = data.reduce((s,d)=>s+(d.carbon_reduction_pct||0),0)/data.length;
        const seaCount = data.filter(d=>d.best_mode==="海運").length;
        
        document.getElementById("totalReduction").innerText = Math.round(totalCarbon).toLocaleString();
        document.getElementById("avgReduction").innerText = avgPct.toFixed(1)+"%";
        document.getElementById("totalCalculations").innerText = data.length;
        document.getElementById("bestModeRate").innerText = Math.round(seaCount/data.length*100)+"%";
        
        new Chart(document.getElementById("trendChart"),{type:'line',data:{labels:data.slice(-14).map(d=>d.date?.split(' ')[0] || ''),datasets:[{label:"減碳量 (kg)",data:data.slice(-14).map(d=>d.carbon_saved),borderColor:"#0077b6",fill:true}]}});
        new Chart(document.getElementById("modeChart"),{type:'doughnut',data:{labels:["海運推薦","公路推薦"],datasets:[{data:[seaCount,data.length-seaCount],backgroundColor:["#00b4d8","#48cae4"]}]}});
    });
}

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById("costSlider")) {
        initWeightControls();
    }
});