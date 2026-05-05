var currentResult = null;
var mapInstance = null;
var trafficLayers = new Map();

function formatCurrency(v){ return "NT$ " + Number(v||0).toLocaleString(); }

function calculate(){
    var start = localStorage.getItem("start");
    var end = localStorage.getItem("end");
    var containers = localStorage.getItem("containers");
    var unit = localStorage.getItem("containerUnit") || "FEU";
    var shipDate = localStorage.getItem("shipDate") || "";

    if(!start||!end||!containers){
        alert("請先返回輸入頁面填寫資料");
        window.location.href="/input";
        return;
    }

    fetch("/calculate",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({start:start,end:end,containers:containers,container_unit:unit,ship_date:shipDate})
    })
    .then(function(r){return r.json();})
    .then(function(d){
        if(d.error) throw new Error(d.error);
        currentResult = d;
        showResults(d);
        initMap(d);
        document.getElementById("loadingOverlay").style.display="none";
        document.getElementById("content").style.display="block";
    })
    .catch(function(e){
        document.getElementById("loadingOverlay").innerHTML = '<div class="loading-container"><div style="color:#e74c3c">錯誤：'+e.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回</button></div>';
    });
}

function showResults(d){
    var isSea = d.best_mode.indexOf("海轉")>=0;

    // === 推薦結果 ===
    document.getElementById("bestBadge").innerHTML = isSea ? "🚢 建議海轉（藍色公路）" : "🚛 建議陸拖（公路運輸）";
    document.getElementById("bestBadge").style.background = isSea ? "#0077b6" : "#e67e22";
    document.getElementById("routeInfo").innerText = d.start_name+" → "+d.end_name+" | "+d.container_display+" | 公路"+d.road_km+"km / 海運"+d.sea_km+"km";

    // === 成本比較表 ===
    document.getElementById("roadFreight").innerText = formatCurrency(d.road.freight);
    document.getElementById("seaFreight").innerText = formatCurrency(d.sea.freight);
    document.getElementById("roadCarbon").innerText = Number(d.road.carbon).toLocaleString()+" kg";
    document.getElementById("seaCarbon").innerText = Number(d.sea.carbon).toLocaleString()+" kg";
    document.getElementById("roadTotal").innerText = formatCurrency(d.road.total);
    document.getElementById("seaTotal").innerText = formatCurrency(d.sea.total);
    document.getElementById("roadTime").innerText = d.road.time_hours+" 小時";

    // === 碳排節省 ===
    document.getElementById("carbonSaved").innerText = Number(d.carbon_improvement).toLocaleString();
    document.getElementById("carbonPct").innerText = d.reduction_pct;
    document.getElementById("carbonCredit").innerText = formatCurrency(d.carbon_credit_value);

    // === 路況 ===
    document.getElementById("nh1Speed").innerText = d.traffic.nh1_speed+" km/h";
    document.getElementById("nh3Speed").innerText = d.traffic.nh3_speed+" km/h";
    document.getElementById("congestionText").innerText = d.traffic.congestion_text;

    // === 船班列表 ===
    var shipHtml = "";
    d.ship_schedules.forEach(function(s,i){
        shipHtml += '<div style="background:rgba(255,255,255,0.15);border-radius:12px;padding:1rem;margin:0.5rem 0;">'+
            '<strong>航次 '+(i+1)+'：'+s.ship_name+'</strong> ('+s.voyage+')<br>'+
            '🚀 ETD：'+s.etd+' → ⚓ ETA：'+s.eta+'（'+s.hours+'h）<br>'+
            '📦 剩餘艙位：'+s.available_feu+' / '+s.capacity_feu+' FEU（'+s.capacity_teu+' TEU）<br>'+
            '📅 固定航班：每週'+s.schedule_day+
            '</div>';
    });
    document.getElementById("shipList").innerHTML = shipHtml || '<p>暫無可用船班</p>';
}

async function initMap(d){
    var clat = (d.start_lat+d.end_lat)/2;
    var clon = (d.start_lon+d.end_lon)/2;
    if(mapInstance){mapInstance.remove();trafficLayers.clear();}
    if(typeof L==='undefined'){return;}

    mapInstance = L.map('map').setView([clat,clon],7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OSM'}).addTo(mapInstance);
    L.marker([d.start_lat,d.start_lon]).addTo(mapInstance).bindPopup('<b>📍 '+d.start_name+'</b>').openPopup();
    L.marker([d.end_lat,d.end_lon]).addTo(mapInstance).bindPopup('<b>🏁 '+d.end_name+'</b>');

    // 公路路線（橘色）
    L.polyline([[d.start_lat,d.start_lon],[d.end_lat,d.end_lon]],{color:'#e67e22',weight:4}).addTo(mapInstance).bindPopup('🚛 公路路線 ('+d.road_km+'km)');
    // 海運路線（藍色虛線）
    L.polyline([[d.start_lat,d.start_lon],[d.end_lat,d.end_lon]],{color:'#0077b6',weight:4,dashArray:'10,10',opacity:0.8}).addTo(mapInstance).bindPopup('🚢 藍色公路 ('+d.sea_km+'km)');

    try{
        var resp = await fetch('/static/taiwan_freeway.geojson');
        var gj = await resp.json();
        gj.features.forEach(function(f){
            var layer = L.geoJSON(f,{style:{color:'#999',weight:5,opacity:0.8}}).addTo(mapInstance);
            trafficLayers.set(f.properties.id,layer);
        });
    }catch(e){}

    setTimeout(loadTraffic,1000);
}

async function loadTraffic(){
    if(!mapInstance) return;
    try{
        var resp = await fetch("/api/traffic");
        var data = await resp.json();
        data.forEach(function(item){
            var layer = trafficLayers.get(item.id);
            if(layer){
                var c = item.speed>=60?"#27ae60":(item.speed>=35?"#f39c12":"#e74c3c");
                layer.setStyle({color:c,weight:6,opacity:0.95});
            }
        });
    }catch(e){}
}

function goToCertificate(){
    if(currentResult){
        localStorage.setItem("recordId",currentResult.record_id);
        localStorage.setItem("savedCO2",currentResult.carbon_improvement);
    }
    window.location.href="/certificate_page";
}