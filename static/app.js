var currentResult = null;
var mapInstance = null;

function fm(v){ return "NT$ "+Number(v||0).toLocaleString(); }

function calculate(){
    var s=localStorage.getItem("start"), e=localStorage.getItem("end");
    var c=localStorage.getItem("containers"), u=localStorage.getItem("unit")||"FEU";
    var td=localStorage.getItem("targetDate")||"";
    if(!s||!e||!c){alert("請先填資料");location.href="/input";return;}

    fetch("/calculate",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({start:s,end:e,containers:c,unit:u,target_date:td})})
    .then(function(r){return r.json();})
    .then(function(d){
        if(d.error) throw new Error(d.error);
        currentResult=d;
        show(d);
        // ✅ 關鍵：displayResults 之後一定要呼叫 drawMap
        drawMap(d);
        document.getElementById("loading").style.display="none";
        document.getElementById("main").style.display="block";
    }).catch(function(e){
        document.getElementById("loading").innerHTML='<div class="loading-container"><div style="color:#e74c3c">'+e.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回</button></div>';
    });
}

function show(d){
    var isSea=d.decision.indexOf("海轉")>=0;
    document.getElementById("decisionBadge").innerText=d.decision;
    document.getElementById("decisionBadge").style.background=isSea?"#0077b6":"#e67e22";
    document.getElementById("routeInfo").innerText=d.start_name+" → "+d.end_name+" | "+d.containers+" | 目標到貨："+d.target_date;

    document.getElementById("roadFreight").innerText=fm(d.road.freight);
    document.getElementById("seaFreight").innerText=fm(d.sea.freight);
    document.getElementById("roadCarbonFee").innerText=fm(d.road.carbon_fee);
    document.getElementById("seaCarbonFee").innerText=fm(d.sea.carbon_fee);
    document.getElementById("roadCarbon").innerText=Number(d.road.carbon).toLocaleString()+" kg";
    document.getElementById("seaCarbon").innerText=Number(d.sea.carbon).toLocaleString()+" kg";
    document.getElementById("roadTotal").innerText=fm(d.road.total);
    document.getElementById("seaTotal").innerText=fm(d.sea.total);

    document.getElementById("carbonSaved").innerText=Number(d.carbon_saved).toLocaleString();
    document.getElementById("carbonPct").innerText=d.carbon_pct;
    document.getElementById("carbonCredit").innerText=fm(d.carbon_credit);

    var sh="";
    if(d.ships&&d.ships.length>0){
        d.ships.forEach(function(s){
            sh+='<div style="background:rgba(255,255,255,0.15);padding:0.8rem;border-radius:10px;margin:0.3rem 0;">'+
                '✅ '+s.ship+'（'+s.weekday+'）<br>ETD '+s.etd+' → ETA '+s.eta+'（'+s.hours+'h）| 剩餘 '+s.available+' / '+s.capacity+' FEU</div>';
        });
    } else { sh='<p>暫無可用船班</p>'; }
    document.getElementById("shipList").innerHTML=sh;

    var re="";
    d.reasons.forEach(function(r){ re+='<li>'+r+'</li>'; });
    document.getElementById("reasonsList").innerHTML=re;
}

// ✅ 保證能跑的地圖函數
function drawMap(data){
    // 清除舊地圖
    if(mapInstance){ mapInstance.remove(); mapInstance=null; }

    // 檢查 Leaflet 是否載入
    if(typeof L === 'undefined'){
        console.error("Leaflet 未載入");
        return;
    }

    // 檢查資料
    if(!data.start_lat || !data.end_lat){
        console.error("缺少經緯度資料");
        return;
    }

    // 建立地圖
    mapInstance = L.map('map').setView([23.5, 120.8], 7);

    // 底圖
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OSM contributors'
    }).addTo(mapInstance);

    // 起點終點標記
    L.marker([data.start_lat, data.start_lon]).addTo(mapInstance)
        .bindPopup('<b>📍 起點：'+data.start_name+'</b>').openPopup();
    L.marker([data.end_lat, data.end_lon]).addTo(mapInstance)
        .bindPopup('<b>🏁 終點：'+data.end_name+'</b>');

    // 繪製路段（從 API 取得）
    fetch("/api/traffic_segments")
    .then(function(r){return r.json();})
    .then(function(segments){
        segments.forEach(function(seg){
            var color = seg.level==="low"?"#27ae60":(seg.level==="medium"?"#f39c12":"#e74c3c");
            var latlngs = seg.coords.map(function(c){return [c[0],c[1]];});
            L.polyline(latlngs,{color:color,weight:5,opacity:0.9}).addTo(mapInstance)
                .bindPopup('<b>'+seg.name+'</b><br>'+seg.speed+' km/h');
        });
    }).catch(function(e){
        console.error("路段載入失敗:",e);
    });
}

function goCert(){
    if(currentResult) localStorage.setItem("recordId",currentResult.record_id);
    location.href="/certificate_page";
}