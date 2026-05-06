var currentResult = null;
var mapInstance = null;
var trafficLines = {};

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
        currentResult=d; show(d); drawMap(d);
        animateKPIs(d);
        document.getElementById("loading").style.display="none";
        document.getElementById("main").style.display="block";
    }).catch(function(e){
        document.getElementById("loading").innerHTML='<div class="loading-container"><div style="color:#e74c3c">'+e.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回</button></div>';
    });
}

function animateKPIs(d){
    animateValue("kpiCarbon", 0, d.carbon_saved, 1000);
    animateValue("kpiVSL", 0, d.vsl_saved, 1000);
    animateValue("kpiScore", 0, d.decision_score, 800);
    document.getElementById("kpiMode").innerText = d.decision;
}

function animateValue(id, start, end, duration){
    var el = document.getElementById(id);
    if(!el) return;
    var range = end - start;
    var step = range / (duration / 16);
    var current = start;
    var timer = setInterval(function(){
        current += step;
        if((step>0 && current>=end) || (step<0 && current<=end)){
            current = end; clearInterval(timer);
        }
        el.innerText = Math.round(current).toLocaleString();
    }, 16);
}

function show(d){
    var isSea = d.decision.indexOf("海轉")>=0;
    document.getElementById("decisionBadge").innerText = d.decision;
    document.getElementById("decisionBadge").style.background = isSea ? "#0077b6" : "#e67e22";

    document.getElementById("roadFreight").innerText = fm(d.road.freight);
    document.getElementById("seaFreight").innerText = fm(d.sea.freight);
    document.getElementById("roadCarbon").innerText = Number(d.road.carbon).toLocaleString()+" kg";
    document.getElementById("seaCarbon").innerText = Number(d.sea.carbon).toLocaleString()+" kg";
    document.getElementById("roadTotal").innerText = fm(d.road.total);
    document.getElementById("seaTotal").innerText = fm(d.sea.total);

    document.getElementById("carbonPct").innerText = d.carbon_pct+"%";
    document.getElementById("carbonCredit").innerText = fm(d.carbon_credit);
    document.getElementById("vslSaved").innerText = fm(d.vsl_saved);
    document.getElementById("accidentRisk").innerText = d.accident_risk;
    document.getElementById("bookingStatus").innerText = d.booking_status;

    var sh="";
    if(d.ships&&d.ships.length>0){
        d.ships.forEach(function(s){
            sh+='<div style="background:rgba(255,255,255,0.15);padding:0.8rem;border-radius:10px;margin:0.3rem 0;">'+
                '✅ '+s.ship+'<br>ETD '+s.etd+' → ETA '+s.eta+'（'+s.hours+'h）| 剩餘 '+s.available+' FEU</div>';
        });
    } else { sh='<p style="color:#ff6b6b;">⚠️ 暫無可用船班</p>'; }
    document.getElementById("shipList").innerHTML=sh;

    var re="";
    d.reasons.forEach(function(r){ re+='<li>'+r+'</li>'; });
    document.getElementById("reasonsList").innerHTML=re;
}

function drawMap(data){
    if(mapInstance){ mapInstance.remove(); mapInstance=null; trafficLines={}; }
    if(typeof L==='undefined'){ return; }

    mapInstance = L.map('map').setView([23.5,120.8],7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OSM'}).addTo(mapInstance);
    L.marker([data.start_lat,data.start_lon]).addTo(mapInstance).bindPopup('<b>📍 '+data.start_name+'</b>').openPopup();
    L.marker([data.end_lat,data.end_lon]).addTo(mapInstance).bindPopup('<b>🏁 '+data.end_name+'</b>');

    fetch("/api/traffic_segments")
    .then(function(r){return r.json();})
    .then(function(segs){
        segs.forEach(function(s){
            var color = s.level==="low"?"#27ae60":(s.level==="medium"?"#f39c12":"#e74c3c");
            var latlngs = s.coords.map(function(c){return [c[0],c[1]];});
            var line = L.polyline(latlngs,{color:color,weight:5,opacity:0.9,dashArray:"10,10"}).addTo(mapInstance);
            line.bindPopup('<b>'+s.name+'</b><br>'+s.speed+' km/h');
            trafficLines[s.id] = line;
        });
        // 動畫
        Object.values(trafficLines).forEach(function(line){
            animateTraffic(line);
        });
    });
}

function animateTraffic(line){
    var offset = 0;
    setInterval(function(){
        offset = (offset + 1) % 20;
        line.setStyle({dashOffset: offset});
    }, 80);
}

function goCert(){
    if(currentResult) localStorage.setItem("recordId",currentResult.record_id);
    location.href="/certificate_page";
}