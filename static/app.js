let currentResult = null;
let mapInstance = null;
let trafficLayers = new Map();
let trafficUpdateInterval = null;

function formatCurrency(v) {
    const value = Number(v ?? 0);
    return "NT$ " + value.toLocaleString();
}

function updateLoadingStep(step) {
    var steps = ['step1', 'step2', 'step3', 'step4', 'step5'];
    var texts = ['分析路線距離...', '串接即時交通資料...', '查詢長榮海運船班...', '計算碳排效益...', '產出最佳方案...'];
    for (var i = 0; i < steps.length; i++) {
        var el = document.getElementById(steps[i]);
        if (el) {
            if (i < step) {
                el.classList.add('completed');
                el.innerHTML = el.innerHTML.replace('⏳', '✅');
            } else if (i === step) {
                el.classList.add('active');
            }
        }
    }
    var loadingText = document.getElementById('loadingText');
    if (loadingText && step < texts.length) {
        loadingText.innerText = texts[step];
    }
}

function calculate() {
    var start = localStorage.getItem("start");
    var end = localStorage.getItem("end");
    var containers = localStorage.getItem("containers");
    var shipDate = localStorage.getItem("shipDate") || "";

    console.log("calculate() called", { start, end, containers, shipDate });
    
    if (!start || !end || !containers) {
        alert("請先返回輸入頁面填寫資料");
        window.location.href = "/input";
        return;
    }
    
    updateLoadingStep(0);
    
    fetch("/calculate", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            start: start, 
            end: end, 
            containers: containers, 
            ship_date: shipDate 
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        console.log("API response:", data);
        if (data.error) {
            throw new Error(data.error);
        }
        currentResult = data;
        displayResults(data);
        initMapAndTraffic(data);
        document.getElementById("loadingOverlay").style.display = "none";
        document.getElementById("content").style.display = "block";
    })
    .catch(function(err) {
        console.error("計算失敗:", err);
        var overlay = document.getElementById("loadingOverlay");
        if (overlay) {
            overlay.innerHTML = '<div class="loading-container"><div style="color:#e74c3c; margin-bottom:1rem;">計算失敗：' + err.message + '</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回重新輸入</button></div>';
        }
    });
}

function displayResults(data) {
    var isSea = data.best_mode === "海運";
    var modeEmoji = isSea ? "🚢" : "🚛";
    var modeName = isSea ? "海拖（藍色公路）" : "路拖（公路運輸）";
    
    var recContent = document.getElementById("recommendationContent");
    recContent.innerHTML = '<h2 style="font-size: 2rem; margin-bottom: 1rem;">🤖 AI 推薦方案</h2>' +
        '<div style="font-size: 5rem; margin: 1rem 0;">' + modeEmoji + '</div>' +
        '<div style="font-size: 2.5rem; font-weight: bold; color: ' + (isSea ? '#0077b6' : '#e74c3c') + '; margin: 1rem 0;">建議採用：' + modeName + '</div>' +
        '<p style="font-size: 1.1rem; color: #555; margin: 1rem 0;">📏 ' + data.start_name + ' → ' + data.end_name + ' | 📦 ' + Number(data.containers).toLocaleString() + ' FEU<br>📅 出貨日期：' + (data.ship_date || "未指定") + '</p>' +
        '<p style="font-size: 1.5rem; font-weight: bold; color: #11998e;">💰 相較路拖節省 <span style="font-size: 2rem;">' + formatCurrency(data.cost_savings) + '</span> 作業費</p>';

    document.getElementById("roadFreight").innerText = formatCurrency(data.road.freight);
    document.getElementById("seaFreight").innerText = formatCurrency(data.sea.freight);
    document.getElementById("roadCarbon").innerText = Number(data.road.carbon).toLocaleString() + " kg CO2e";
    document.getElementById("seaCarbon").innerText = Number(data.sea.carbon).toLocaleString() + " kg CO2e";
    document.getElementById("roadTotal").innerText = formatCurrency(data.road.total);
    document.getElementById("seaTotal").innerText = formatCurrency(data.sea.total);

    document.getElementById("nh1Speed").innerText = data.road_condition.nh1_speed + " km/h";
    document.getElementById("nh3Speed").innerText = data.road_condition.nh3_speed + " km/h";
    document.getElementById("overallSpeed").innerText = data.road_condition.avg_speed + " km/h";

    ['nh1Speed', 'nh3Speed', 'overallSpeed'].forEach(function(id) {
        var el = document.getElementById(id);
        var v = parseFloat(el.innerText);
        if (v >= 60) el.style.color = '#27ae60';
        else if (v >= 35) el.style.color = '#f39c12';
        else el.style.color = '#e74c3c';
    });

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
    document.getElementById("shipScheduleDay").innerText = s.schedule_day || "-";

    if (s.is_virtual) {
        document.getElementById("virtualBadge").style.display = "inline-block";
    } else {
        document.getElementById("virtualBadge").style.display = "none";
    }

    var capPct = s.capacity > 0 ? (s.available / s.capacity * 100) : 0;
    setTimeout(function() {
        var bar = document.getElementById("capacityBar");
        if (bar) {
            bar.style.width = capPct + "%";
            if (capPct < 30) bar.style.background = "linear-gradient(135deg, #e74c3c, #c0392b)";
            else if (capPct < 60) bar.style.background = "linear-gradient(135deg, #f39c12, #e67e22)";
            else bar.style.background = "linear-gradient(135deg, #27ae60, #2ecc71)";
        }
    }, 300);

    var carbonCard = document.getElementById("carbonCard");
    if (data.carbon_improvement > 0) {
        carbonCard.style.display = "block";
        document.getElementById("carbonSaved").innerText = Number(data.carbon_improvement).toLocaleString();
        document.getElementById("carbonPct").innerText = data.reduction_pct + "%";
        document.getElementById("carbonCompareText").innerHTML = '🚛 路拖碳排：<strong>' + Number(data.road.carbon).toLocaleString() + ' kg CO2e</strong><br>🚢 海拖碳排：<strong>' + Number(data.sea.carbon).toLocaleString() + ' kg CO2e</strong>';
    } else {
        carbonCard.style.display = "none";
    }
}

async function initMapAndTraffic(data) {
    var centerLat = (data.start_lat + data.end_lat) / 2;
    var centerLon = (data.start_lon + data.end_lon) / 2;
    
    if (mapInstance) {
        mapInstance.remove();
        trafficLayers.clear();
    }
    
    if (typeof L === 'undefined') {
        document.getElementById("map").innerHTML = '<div style="text-align:center; padding:3rem;">地圖載入失敗</div>';
        return;
    }
    
    mapInstance = L.map('map').setView([centerLat, centerLon], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OSM',
        subdomains: 'abcd'
    }).addTo(mapInstance);

    L.marker([data.start_lat, data.start_lon]).addTo(mapInstance)
        .bindPopup('<b>📍 起點：' + data.start_name + '</b>').openPopup();
    L.marker([data.end_lat, data.end_lon]).addTo(mapInstance)
        .bindPopup('<b>🏁 終點：' + data.end_name + '</b>');

    try {
        var response = await fetch('/static/taiwan_freeway.geojson');
        var geojson = await response.json();
        
        geojson.features.forEach(function(feature) {
            var layer = L.geoJSON(feature, {
                style: { color: '#999', weight: 5, opacity: 0.8 }
            }).addTo(mapInstance);
            layer.bindPopup('<b>' + feature.properties.name + '</b><br>時速：載入中...');
            trafficLayers.set(feature.properties.id, layer);
        });
    } catch(e) {
        console.error("載入路網失敗:", e);
    }
    
    L.polyline(
        [[data.start_lat, data.start_lon], [data.end_lat, data.end_lon]],
        { color: '#0077b6', weight: 4, dashArray: '10, 10', opacity: 0.8 }
    ).addTo(mapInstance).bindPopup('<b>🚢 藍色公路航線</b>');

    setTimeout(function() { loadTrafficLight(); }, 1000);
    if (trafficUpdateInterval) clearInterval(trafficUpdateInterval);
    trafficUpdateInterval = setInterval(loadTrafficLight, 60000);
}

async function loadTrafficLight() {
    if (!mapInstance) return;
    try {
        var response = await fetch("/api/traffic");
        var speedData = await response.json();
        speedData.forEach(function(item) {
            var layer = trafficLayers.get(item.id);
            if (layer) {
                var color = item.speed >= 60 ? "#27ae60" : (item.speed >= 35 ? "#f39c12" : "#e74c3c");
                layer.setStyle({ color: color, weight: 6, opacity: 0.95 });
            }
        });
    } catch(error) {
        console.error("載入即時路況失敗:", error);
    }
}

function goToCertificate() {
    if (currentResult) {
        localStorage.setItem("savedCO2", currentResult.carbon_improvement);
        localStorage.setItem("reductionPct", currentResult.reduction_pct);
        localStorage.setItem("recordId", currentResult.record_id);
    }
    window.location.href = "/certificate_page";
}