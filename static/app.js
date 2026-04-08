let currentResult = null;
let currentWeights = { cost: 0.4, carbon: 0.4, risk: 0.2 };

function goToInput() { window.location = "/input"; }
function goToResult() {
    const start = document.getElementById("start").value;
    const end = document.getElementById("end").value;
    const containers = document.getElementById("containers").value;
    const cargoType = document.getElementById("cargoType").value;
    if (!containers || containers <= 0) { alert("請輸入貨櫃數量（至少 1 FEU）"); return; }
    localStorage.setItem("start", start); localStorage.setItem("end", end); localStorage.setItem("containers", containers); localStorage.setItem("cargoType", cargoType);
    window.location = "/result";
}

function updateWeight(type, value) {
    let numValue = parseFloat(value);
    if (isNaN(numValue)) numValue = 0;
    currentWeights[type] = numValue;
    document.getElementById(`${type}Value`).innerText = Math.round(numValue * 100) + "%";
    const total = currentWeights.cost + currentWeights.carbon + currentWeights.risk;
    if (Math.abs(total - 1) > 0.01 && total > 0) {
        currentWeights.cost /= total; currentWeights.carbon /= total; currentWeights.risk /= total;
        const cs = document.getElementById("costSlider"); const cs2 = document.getElementById("carbonSlider"); const rs = document.getElementById("riskSlider");
        if (cs) cs.value = currentWeights.cost; if (cs2) cs2.value = currentWeights.carbon; if (rs) rs.value = currentWeights.risk;
        document.getElementById("costValue").innerText = Math.round(currentWeights.cost * 100) + "%";
        document.getElementById("carbonValue").innerText = Math.round(currentWeights.carbon * 100) + "%";
        document.getElementById("riskValue").innerText = Math.round(currentWeights.risk * 100) + "%";
    }
}

function setPreset(preset) {
    const presets = { balanced: { cost: 0.33, carbon: 0.34, risk: 0.33 }, cost: { cost: 0.7, carbon: 0.2, risk: 0.1 }, green: { cost: 0.2, carbon: 0.7, risk: 0.1 }, safe: { cost: 0.3, carbon: 0.2, risk: 0.5 } };
    const w = presets[preset];
    if (w) {
        currentWeights = w;
        const cs = document.getElementById("costSlider"); const cs2 = document.getElementById("carbonSlider"); const rs = document.getElementById("riskSlider");
        if (cs) cs.value = w.cost; if (cs2) cs2.value = w.carbon; if (rs) rs.value = w.risk;
        document.getElementById("costValue").innerText = Math.round(w.cost * 100) + "%";
        document.getElementById("carbonValue").innerText = Math.round(w.carbon * 100) + "%";
        document.getElementById("riskValue").innerText = Math.round(w.risk * 100) + "%";
    }
}

function initWeightControls() {
    const cs = document.getElementById("costSlider"); const cs2 = document.getElementById("carbonSlider"); const rs = document.getElementById("riskSlider");
    if (cs) { cs.value = currentWeights.cost; cs.oninput = e => updateWeight('cost', e.target.value); document.getElementById("costValue").innerText = Math.round(currentWeights.cost * 100) + "%"; }
    if (cs2) { cs2.value = currentWeights.carbon; cs2.oninput = e => updateWeight('carbon', e.target.value); document.getElementById("carbonValue").innerText = Math.round(currentWeights.carbon * 100) + "%"; }
    if (rs) { rs.value = currentWeights.risk; rs.oninput = e => updateWeight('risk', e.target.value); document.getElementById("riskValue").innerText = Math.round(currentWeights.risk * 100) + "%"; }
    const b = document.getElementById("preset-balanced"); const c = document.getElementById("preset-cost"); const g = document.getElementById("preset-green"); const s = document.getElementById("preset-safe");
    if (b) b.onclick = () => setPreset('balanced'); if (c) c.onclick = () => setPreset('cost'); if (g) g.onclick = () => setPreset('green'); if (s) s.onclick = () => setPreset('safe');
}

function calculate() {
    const start = localStorage.getItem("start"), end = localStorage.getItem("end"), containers = localStorage.getItem("containers"), cargoType = localStorage.getItem("cargoType") || "general";
    if (!start || !end || !containers) { alert("請先返回輸入頁面填寫資料"); window.location = "/input"; return; }
    showLoading();
    fetch("/calculate", { method: "POST", headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start, end, containers, cargo_type: cargoType, weights: currentWeights }) })
    .then(res => res.json()).then(data => { currentResult = data; displayResults(data); drawComparisonChart(data); drawSocialCostChart(data); drawVSLChart(data); drawTimeCostChart(data); drawCarbonChart(data); hideLoading(); })
    .catch(err => { console.error(err); hideLoading(); alert("計算失敗：" + err.message); });
}

function showLoading() { const rd = document.getElementById("result"); if (rd) rd.innerHTML = '<div class="card" style="text-align:center"><div class="animate-pulse">🔄 AI 分析中，請稍候...</div></div>'; }
function hideLoading() {}

function formatCurrency(v) { return `NT$ ${v.toLocaleString()}`; }

function displayResults(data) {
    const rd = document.getElementById("result");
    if (!rd) return;
    rd.innerHTML = `<div class="result-card"><h3>📊 AI 多目標決策分析報告</h3><p>🚢 起點：${data.start_name} → 🏁 終點：${data.end_name}</p><p>📏 距離：${data.distance.toLocaleString()} 公里</p><p>📦 貨櫃數量：${data.containers.toLocaleString()} FEU</p><p>${data.cargo_icon} 貨物類型：<strong>${data.cargo_type}</strong></p><div style="margin-top:0.5rem;font-size:0.9rem">🌱 碳排係數：公路 ${data.road_emission_factor} / 海運 ${data.sea_emission_factor} kg CO2e/FEU-km</div><div style="margin-top:1rem;padding:1rem;background:rgba(255,255,255,0.2);border-radius:10px">🤖 <strong>AI 推薦方案：${data.best_mode}</strong><br>綜合評分：公路 ${data.all_scores?.road || 'N/A'} / 海運 ${data.all_scores?.sea || 'N/A'}</div></div>
    <div class="card"><h3>💰 總體社會成本分析（FEU 單位）</h3><table class="cost-table"><thead><tr><th>成本項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th><th>節省金額</th></tr></thead><tbody>
    <tr><td><strong>💰 運費 (NTD)</strong></td><td>${formatCurrency(data.road.freight)}</td><td>${formatCurrency(data.sea.freight)}</td><td>${formatCurrency(data.road.freight - data.sea.freight)}</td></tr>
    <tr><td><strong>⏳ 時間成本 (NTD)</strong></td><td>${formatCurrency(data.road.time)}</td><td>${formatCurrency(data.sea.time)}</td><td>${formatCurrency(data.road.time - data.sea.time)}</td></tr>
    <tr><td><strong>🏛️ 社會成本 (NTD)</strong></td><td>${formatCurrency(data.road.social)}</td><td>${formatCurrency(data.sea.social)}</td><td class="savings-number">${formatCurrency(data.road.social - data.sea.social)}</td></tr>
    <tr><td><strong>⚠️ VSL人命風險 (NTD)</strong></td><td>${formatCurrency(data.road.vsl)}</td><td>${formatCurrency(data.sea.vsl)}</td><td class="savings-number">${formatCurrency(data.road.vsl - data.sea.vsl)}</td></tr>
    <tr style="background:var(--light-cyan);font-weight:bold"><td><strong>📊 總社會成本 (NTD)</strong></td><td>${formatCurrency(data.road.total)}</td><td>${formatCurrency(data.sea.total)}</td><td class="savings-number">${formatCurrency(data.social_savings)}</td></tr>
    </tbody></table></div>
    <div class="card" style="background:var(--light-cyan)"><h3>🤖 AI 決策分析</h3><p>📌 貨物類型：${data.cargo_type}</p><p>${data.recommendation_reason}</p><p style="margin-top:0.5rem;font-size:0.9rem">💡 時間敏感度：${Math.round(data.time_sensitivity * 100)}%</p></div>
    <div class="card"><h3>📊 運輸模式優劣勢總結</h3><table class="cost-table"><thead><tr><th>評估項目</th><th>🚛 公路運輸</th><th>🚢 海運運輸</th></tr></thead><tbody>
    <tr><td>💰 運費</td><td class="劣势">較高 💸</td><td class="优势">較低 ✅</td></tr>
    <tr><td>⏱️ 運輸時間</td><td class="优势">快 (4-6小時) ✅</td><td class="劣势">慢 (18-24小時) ⚠️</td></tr>
    <tr><td>🏛️ 社會成本</td><td class="劣势">高 (事故/空污) ❌</td><td class="优势">低 ✅</td></tr>
    <tr><td>⚠️ VSL人命風險</td><td class="劣势">高 (事故率高) ❌</td><td class="优势">低 ✅</td></tr>
    <tr><td>🌱 碳排放</td><td class="劣势">高 ❌</td><td class="优势">低 ✅</td></tr>
    <tr><td>🚪 門到門服務</td><td class="优势">可直達 ✅</td><td class="劣势">需轉運 ⚠️</td></tr>
    </tbody></table><p style="margin-top:1rem">💡 <strong>決策建議：</strong>${data.best_mode === "海運" ? "海運在成本、環保、安全面具有優勢，適合大宗、低時效性貨物。" : "公路在時效性和靈活性上勝出，適合高價值、急迫性貨物。"}</p></div>`;
    
    if (data.road_status) {
        const rs = document.getElementById("roadStatus"); const rsp = document.getElementById("roadSpeed");
        if (rs) { rs.innerHTML = data.road_status.level_text; rs.style.color = data.road_status.level === "high" ? "#e74c3c" : data.road_status.level === "medium" ? "#f39c12" : "#27ae60"; }
        if (rsp) rsp.innerHTML = `平均時速 ${data.road_status.avg_speed} km/h | 延遲倍數 ${data.road_status.delay_factor}x`;
    }
    if (data.ship_status) {
        const ss = document.getElementById("shipStatus"); const sc = document.getElementById("shipCapacity");
        if (ss) ss.innerHTML = data.ship_status.status;
        if (sc) sc.innerHTML = `艙位容量 ${data.ship_status.available_capacity?.toLocaleString()} FEU | ${data.ship_status.next_ship_in_hours} 小時後到港`;
    }
    if (data.dispatch) {
        const de = document.getElementById("dispatchResult");
        if (de) {
            const sp = data.dispatch.transfer_ratio || (data.dispatch.to_sea / (data.dispatch.to_sea + data.dispatch.to_road) * 100);
            const rp = 100 - sp;
            let ch = "";
            if (data.dispatch.carbon_benefit) ch = `<div style="margin-top:1rem;padding:0.8rem;background:rgba(255,255,255,0.2);border-radius:10px">🌱 <strong>碳排效益：</strong>轉移 ${data.dispatch.to_sea} FEU 可減少 <strong>${data.dispatch.carbon_benefit.saved.toLocaleString()} kg CO2e</strong> (${data.dispatch.carbon_benefit.saved_pct}%)</div>`;
            de.innerHTML = `<div style="display:flex;gap:2rem;flex-wrap:wrap"><div style="flex:1"><p>🧠 <strong>AI 多因子評分</strong></p><div class="score-card"><div class="score-number score-sea" id="scoreSea">0</div><div>🚢 海運分數</div></div><div class="score-card" style="margin-top:0.5rem"><div class="score-number score-road" id="scoreRoad">0</div><div>🚛 公路分數</div></div></div><div style="flex:2"><p>📦 <strong>AI 貨櫃分配結果</strong></p><div style="display:flex;gap:1rem;margin-bottom:1rem"><div style="flex:1;text-align:center"><span style="font-size:2rem">🚢</span><br><strong>${data.dispatch.to_sea}</strong> FEU<br><span style="font-size:0.85rem">海運</span></div><div style="flex:1;text-align:center"><span style="font-size:2rem">🚛</span><br><strong>${data.dispatch.to_road}</strong> FEU<br><span style="font-size:0.85rem">公路</span></div></div><div class="ratio-bar-container"><div class="ratio-bar-sea" id="ratioBarSea" style="width:${sp}%"><span>🚢 ${Math.round(sp)}%</span></div></div><div class="ratio-bar-container"><div class="ratio-bar-road" id="ratioBarRoad" style="width:${rp}%"><span>🚛 ${Math.round(rp)}%</span></div></div><p style="margin-top:1rem">💡 <strong>決策原因</strong></p><p>${data.dispatch.reason}</p>${ch}</div></div>`;
            setTimeout(() => { const seaE = document.getElementById("scoreSea"); const roadE = document.getElementById("scoreRoad"); if (seaE) animateValue(seaE, 0, data.dispatch.score_sea || 5, 600); if (roadE) animateValue(roadE, 0, data.dispatch.score_road || 5, 600); const sb = document.getElementById("ratioBarSea"); if (sb) sb.classList.add('progress-bar-animate'); }, 100);
        }
    }
}

function animateValue(el, start, end, duration) { if (!el) return; const range = end - start; const inc = range / (duration / 16); let current = start; const timer = setInterval(() => { current += inc; if ((inc > 0 && current >= end) || (inc < 0 && current <= end)) { current = end; clearInterval(timer); } el.textContent = Math.round(current); }, 16); }

function drawComparisonChart(d) { const ctx = document.getElementById("comparisonChart"); if(!ctx) return; new Chart(ctx,{type:'bar',data:{labels:['公路運輸','海運運輸'],datasets:[{label:'運費 (NTD)',data:[d.road.freight,d.sea.freight],backgroundColor:'rgba(0,119,182,0.7)'},{label:'社會成本 (NTD)',data:[d.road.social,d.sea.social],backgroundColor:'rgba(0,180,216,0.7)'},{label:'VSL風險成本 (NTD)',data:[d.road.vsl,d.sea.vsl],backgroundColor:'rgba(72,202,228,0.7)'},{label:'時間成本 (NTD)',data:[d.road.time,d.sea.time],backgroundColor:'rgba(144,224,239,0.7)'}]},options:{responsive:true,scales:{y:{beginAtZero:true}}}}); }
function drawSocialCostChart(d) { const ctx = document.getElementById("socialCostChart"); if(!ctx) return; new Chart(ctx,{type:'bar',data:{labels:['公路運輸','海運運輸'],datasets:[{label:'社會外部成本 (NTD)',data:[d.road.social,d.sea.social],backgroundColor:['rgba(231,76,60,0.7)','rgba(46,204,113,0.7)']}]},options:{responsive:true,plugins:{tooltip:{callbacks:{afterBody:()=>['包含：空氣污染、噪音、肇事成本','公路劣勢：事故率高、空污嚴重']}}},scales:{y:{beginAtZero:true}}}}); }
function drawVSLChart(d) { const ctx = document.getElementById("vslChart"); if(!ctx) return; new Chart(ctx,{type:'bar',data:{labels:['公路運輸','海運運輸'],datasets:[{label:'VSL 人命風險成本 (NTD)',data:[d.road.vsl,d.sea.vsl],backgroundColor:['rgba(231,76,60,0.7)','rgba(46,204,113,0.7)']}]},options:{responsive:true,plugins:{tooltip:{callbacks:{afterBody:()=>['VSL：NT$5,000萬元','公路事故率 1.36e-8','海運事故率 1.8e-9']}}},scales:{y:{beginAtZero:true}}}}); }
function drawTimeCostChart(d) { const ctx = document.getElementById("timeCostChart"); if(!ctx) return; new Chart(ctx,{type:'bar',data:{labels:['公路運輸','海運運輸'],datasets:[{label:'時間成本 (NTD)',data:[d.road.time,d.sea.time],backgroundColor:['rgba(52,152,219,0.7)','rgba(241,196,15,0.7)']}]},options:{responsive:true,plugins:{tooltip:{callbacks:{afterBody:(c)=>c[0].datasetIndex===0?['公路優勢：運輸時間短']:['海運劣勢：運輸時間長']}}},scales:{y:{beginAtZero:true}}}}); }
function drawCarbonChart(d) { const ctx = document.getElementById("carbonChart"); if(!ctx) return; new Chart(ctx,{type:'bar',data:{labels:['公路運輸','海運運輸'],datasets:[{label:'碳排放量 (kg CO2e)',data:[d.road.carbon,d.sea.carbon],backgroundColor:['rgba(231,76,60,0.7)','rgba(46,204,113,0.7)']}]},options:{responsive:true,plugins:{tooltip:{callbacks:{afterBody:()=>[`公路係數：${d.road_emission_factor} kg/FEU-km`,`海運係數：${d.sea_emission_factor} kg/FEU-km`,`可減少 ${d.carbon_saved.toLocaleString()} kg (${d.carbon_reduction_pct}%)`]}}},scales:{y:{beginAtZero:true}}}}); }

function generateCertificate() { const name = document.getElementById("name").value; if(!name){alert("請輸入公司名稱");return;} fetch("/certificate",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({name,carbon_saved:localStorage.getItem("savedCO2")||0,carbon_reduction_pct:localStorage.getItem("carbonReductionPct")||0})}).then(r=>r.json()).then(d=>{localStorage.setItem("cert",JSON.stringify(d));document.getElementById("certResult").innerHTML=`<div class="card"><h3>✅ 認證已產生</h3><p>公司：${d.name}</p><p>編號：${d.cert_id}</p><p>日期：${d.date}</p><button class="btn btn-primary" onclick="downloadCertificatePDF()">📄 下載 PDF</button><button class="btn btn-outline" onclick="generateESGReport()">📊 ESG報告</button></div>`;}); }
function downloadCertificatePDF(){const c=JSON.parse(localStorage.getItem("cert"));if(!c){alert("請先產生認證");return;}fetch("/download_pdf",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify(c)}).then(r=>r.blob()).then(b=>{const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=`certificate_${c.cert_id}.pdf`;a.click();URL.revokeObjectURL(u);});}
function generateESGReport(){const c=JSON.parse(localStorage.getItem("cert"));if(!c){alert("請先產生認證");return;}fetch("/esg_report",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({name:c.name,carbon_saved:c.carbon_saved})}).then(r=>r.json()).then(d=>alert(d.report));}
function goToCertificate(){if(currentResult){localStorage.setItem("savedCO2",currentResult.carbon_saved);localStorage.setItem("carbonReductionPct",currentResult.carbon_reduction_pct);}window.location="/certificate_page";}
function loadHistory(){fetch("/get_history").then(r=>r.json()).then(d=>{const tb=document.getElementById("history-body");if(!tb)return;tb.innerHTML="";if(d.length===0){tb.innerHTML='<tr><td colspan="11">暫無歷史記錄</td></tr>';return;}d.reverse().forEach(r=>{tb.innerHTML+=`<tr><td>${r.date}</td><td>${r.start}</td><td>${r.end}</td><td>${r.containers}</td><td>${r.unit||'FEU'}</td><td>${r.cargo_type||'-'}</td><td>${r.distance} km</td><td>${r.sea_carbon?.toLocaleString()||'-'} kg</td><td>${r.best_mode}</td><td>${r.carbon_saved?.toLocaleString()||'-'} kg</td><td>${r.carbon_reduction_pct||0}%</td></tr>`;});drawHistoryChart(d);});}
function drawHistoryChart(h){const ctx=document.getElementById("historyChart");if(!ctx)return;const last7=h.slice(-7);new Chart(ctx,{type:'line',data:{labels:last7.map(x=>x.date?.split(' ')[0]),datasets:[{label:'公路碳排',data:last7.map(x=>x.road_carbon||0),borderColor:'#e74c3c',fill:true},{label:'海運碳排',data:last7.map(x=>x.sea_carbon||0),borderColor:'#0077b6',fill:true}]}});}
function loadDashboard(){fetch("/get_history").then(r=>r.json()).then(d=>{if(d.length===0){document.getElementById("totalReduction").innerText="0";document.getElementById("avgReduction").innerText="0%";document.getElementById("totalCalculations").innerText="0";document.getElementById("bestModeRate").innerText="0%";return;}const tc=d.reduce((s,x)=>s+(x.carbon_saved||0),0);const ap=d.reduce((s,x)=>s+(x.carbon_reduction_pct||0),0)/d.length;const sc=d.filter(x=>x.best_mode==="海運").length;document.getElementById("totalReduction").innerText=Math.round(tc).toLocaleString();document.getElementById("avgReduction").innerText=ap.toFixed(1)+"%";document.getElementById("totalCalculations").innerText=d.length;document.getElementById("bestModeRate").innerText=Math.round(sc/d.length*100)+"%";new Chart(document.getElementById("trendChart"),{type:'line',data:{labels:d.slice(-14).map(x=>x.date?.split(' ')[0]),datasets:[{label:"減碳量 (kg)",data:d.slice(-14).map(x=>x.carbon_saved),borderColor:"#0077b6",fill:true}]}});new Chart(document.getElementById("modeChart"),{type:'doughnut',data:{labels:["海運推薦","公路推薦"],datasets:[{data:[sc,d.length-sc],backgroundColor:["#00b4d8","#48cae4"]}]}});});}
document.addEventListener('DOMContentLoaded',function(){if(document.getElementById("costSlider"))initWeightControls();});