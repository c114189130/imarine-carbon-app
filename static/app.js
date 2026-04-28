var currentResult = null;
var mapInstance = null;
var trafficLayers = new Map();
var trafficUpdateInterval = null;

function formatCurrency(v) {
    return "NT$ " + Number(v||0).toLocaleString();
}

function calculate() {
    var start = localStorage.getItem("start");
    var end = localStorage.getItem("end");
    var containers = localStorage.getItem("containers");
    var shipDate = localStorage.getItem("shipDate") || "";

    if (!start || !end || !containers) {
        alert("請先返回輸入頁面填寫資料");
        window.location.href = "/input";
        return;
    }

    fetch("/calculate", {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({start: start, end: end, containers: containers, ship_date: shipDate})
    })
    .then(function(res){ return res.json(); })
    .then(function(data){
        if (data.error) throw new Error(data.error);
        currentResult = data;
        displayResults(data);
        initMapAndTraffic(data);
        document.getElementById("loadingOverlay").style.display = "none";
        document.getElementById("content").style.display = "block";
    })
    .catch(function(err){
        var ov = document.getElementById("loadingOverlay");
        if (ov) ov.innerHTML = '<div class="loading-container"><div style="color:#e74c3c;margin-bottom:1rem;">計算失敗：'+err.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回重新輸入</button></div>';
    });
}

function displayResults(data) {
    var isSea = data.best_mode === "海運";
    var emoji = isSea ? "🚢" : "🚛";
    var name = isSea ? "海拖（藍色公路）" : "路拖（公路運輸）";
    var color = isSea ? '#0077b6' : '#e74c3c';

    document.getElementById("recommendationContent").innerHTML =
        '<h2>🤖 AI 推薦方案</h2>' +
        '<div style="font-size:5rem;margin:1rem 0;">'+emoji+'</div>' +
        '<div style="font-size:2rem;font-weight:bold;color:'+color+';">建議採用：'+name+'</div>' +
        '<p>📏 '+data.start_name+' → '+data.end_name+' | 📦 '+Number(data.containers).toLocaleString()+' FEU</p>' +
        '<p style="font-size:1.5rem;color:#11998e;">💰 相較路拖節省 '+formatCurrency(data.cost_savings)+' 作業費</p>';

    document.getElementById("roadFreight").innerText = formatCurrency(data.road.freight);
    document.getElementById("seaFreight").innerText = formatCurrency(data.sea.freight);
    document.getElementById("roadCarbon").innerText = Number(data.road.carbon).toLocaleString() + " kg CO2e";
    document.getElementById("seaCarbon").innerText = Number(data.sea.carbon).toLocaleString() + " kg CO2e";
    document.getElementById("roadTotal").innerText = formatCurrency(data.road.total);
    document.getElementById("seaTotal").innerText = formatCurrency(data.sea.total);

    document.getElementById("nh1Speed").innerText = data.road_condition.nh1_speed + " km/h";
    document.getElementById("nh3Speed").innerText = data.road_condition.nh3_speed + " km/h";
    document.getElementById("overallSpeed").innerText = data.road_condition.avg_speed + " km/h";

    var s = data.ship_schedule || {};
    document.getElementById("shipName").innerText = s.name_zh ? s.name + " (" + s.name_zh + ")" : (s.name || "-");
    document.getElementById("shipVoyage").innerText = s.voyage || "-";
    document.getElementById("shipRoute").innerText = s.route || "-";
    document.getElementById("shipDest").innerText = s.destination || "-";
    document.getElementById("shipEtd").innerText = s.etd || "-";
    document.getElementById("shipEta").innerText = s.eta || "-";
    document.getElementById("shipHours").innerText = s.hours ? s.hours + " 小時" : "-";
    document.getElementById("shipAvailable").innerText = s.available || 0;
    document.getElementById("shipCapacity").innerText = s.capacity || "-";
    document.getElementById("shipScheduleDay").innerText = "每週" + (s.schedule_day || "-");

    if (s.name_zh && s.name_zh.indexOf("模擬") >= 0) {
        document.getElementById("virtualBadge").style.display = "inline-block";
    } else {
        document.getElementById("virtualBadge").style.display = "none";
    }

    var pct = s.capacity > 0 ? (s.available / s.capacity * 100) : 0;
    setTimeout(function(){
        var bar = document.getElementById("capacityBar");
        if (bar) {
            bar.style.width = pct + "%";
            bar.style.background = pct < 30 ? "linear-gradient(135deg,#e74c3c,#c0392b)" : (pct < 60 ? "linear-gradient(135deg,#f39c12,#e67e22)" : "linear-gradient(135deg,#27ae60,#2ecc71)");
        }
    }, 300);

    var cc = document.getElementById("carbonCard");
    if (data.carbon_improvement > 0) {
        cc.style.display = "block";
        document.getElementById("carbonSaved").innerText = Number(data.carbon_improvement).toLocaleString();
        document.getElementById("carbonPct").innerText = data.reduction_pct + "%";
        document.getElementById("carbonCompareText").innerHTML = '🚛 路拖碳排：<strong>'+Number(data.road.carbon).toLocaleString()+' kg CO2e</strong><br>🚢 海拖碳排：<strong>'+Number(data.sea.carbon).toLocaleString()+' kg CO2e</strong>';
    } else {
        cc.style.display = "none";
    }
}

async function initMapAndTraffic(data) {
    var clat = (data.start_lat + data.end_lat) / 2;
    var clon = (data.start_lon + data.end_lon) / 2;
    if (mapInstance) { mapInstance.remove(); trafficLayers.clear(); }
    if (typeof L === 'undefined') { document.getElementById("map").innerHTML = '<div style="text-align:center;padding:3rem;">地圖載入失敗</div>'; return; }

    mapInstance = L.map('map').setView([clat, clon], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {attribution: '&copy; OSM', subdomains: 'abcd'}).addTo(mapInstance);
    L.marker([data.start_lat, data.start_lon]).addTo(mapInstance).bindPopup('<b>📍 '+data.start_name+'</b>').openPopup();
    L.marker([data.end_lat, data.end_lon]).addTo(mapInstance).bindPopup('<b>🏁 '+data.end_name+'</b>');

    try {
        var resp = await fetch('/static/taiwan_freeway.geojson');
        var gj = await resp.json();
        gj.features.forEach(function(f){
            var layer = L.geoJSON(f, {style: {color:'#999',weight:5,opacity:0.8}}).addTo(mapInstance);
            layer.bindPopup('<b>'+f.properties.name+'</b><br>時速：載入中...');
            trafficLayers.set(f.properties.id, layer);
        });
    } catch(e) {}

    L.polyline([[data.start_lat,data.start_lon],[data.end_lat,data.end_lon]], {color:'#0077b6',weight:4,dashArray:'10,10',opacity:0.8}).addTo(mapInstance).bindPopup('<b>🚢 藍色公路航線</b>');

    setTimeout(function(){ loadTrafficLight(); }, 1000);
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    trafficUpdateInterval = setInterval(loadTrafficLight, 60000);
}

async function loadTrafficLight() {
    if (!mapInstance) return;
    try {
        var resp = await fetch("/api/traffic");
        var data = await resp.json();
        data.forEach(function(item){
            var layer = trafficLayers.get(item.id);
            if (layer) {
                var c = item.speed >= 60 ? "#27ae60" : (item.speed >= 35 ? "#f39c12" : "#e74c3c");
                layer.setStyle({color:c, weight:6, opacity:0.95});
            }
        });
    } catch(e) {}
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_improvement);
        localStorage.setItem("reductionPct", currentResult.reduction_pct);
        localStorage.setItem("recordId", currentResult.record_id);
    }
    window.location.href = "/certificate_page";
}