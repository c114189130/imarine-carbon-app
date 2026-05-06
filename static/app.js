var currentResult = null;
var mapInstance = null;
var segmentLayers = {};

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
        currentResult=d; show(d); initMap(d);
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
        d.ships.forEach(function(s,i){
            sh+='<div style="background:rgba(255,255,255,0.15);padding:0.8rem;border-radius:10px;margin:0.3rem 0;">'+
                '✅ '+s.ship+'（'+s.weekday+'）<br>ETD '+s.etd+' → ETA '+s.eta+'（'+s.hours+'h）| 剩餘 '+s.available+' / '+s.capacity+' FEU</div>';
        });
    } else { sh='<p>暫無可用船班</p>'; }
    document.getElementById("shipList").innerHTML=sh;

    var re="";
    d.reasons.forEach(function(r){ re+='<li>'+r+'</li>'; });
    document.getElementById("reasonsList").innerHTML=re;
}

function initMap(d){
    if(mapInstance){mapInstance.remove();}
    mapInstance = L.map('map').setView([23.5,120.8],7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OSM'}).addTo(mapInstance);

    // 起終點標記
    L.marker([d.start_lat,d.start_lon]).addTo(mapInstance).bindPopup('<b>📍 '+d.start_name+'</b>').openPopup();
    L.marker([d.end_lat,d.end_lon]).addTo(mapInstance).bindPopup('<b>🏁 '+d.end_name+'</b>');

    // 載入路段
    fetch("/api/traffic_segments")
    .then(function(r){return r.json();})
    .then(function(segments){
        segments.forEach(function(seg){
            var color = seg.level==="low"?"#27ae60":(seg.level==="medium"?"#f39c12":"#e74c3c");
            var latlngs = seg.coords.map(function(c){return [c[0],c[1]];});
            var layer = L.polyline(latlngs,{color:color,weight:5,opacity:0.9}).addTo(mapInstance);
            layer.bindPopup('<b>'+seg.name+'</b><br>'+seg.speed+' km/h');
        });
    });
}

function goCert(){
    if(currentResult) localStorage.setItem("recordId",currentResult.record_id);
    location.href="/certificate_page";
}