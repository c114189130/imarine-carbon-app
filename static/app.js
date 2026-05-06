var currentResult=null,mapInstance=null,trafficLines={};
function fm(v){return"NT$ "+Number(v||0).toLocaleString();}
function calculate(){
    var s=localStorage.getItem("start"),e=localStorage.getItem("end"),c=localStorage.getItem("containers"),u=localStorage.getItem("unit")||"FEU",td=localStorage.getItem("targetDate")||"",ct=localStorage.getItem("cargoType")||"normal";
    if(!s||!e||!c){alert("請先填資料");location.href="/input";return;}
    fetch("/calculate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({start:s,end:e,containers:c,unit:u,target_date:td,cargo_type:ct})})
    .then(r=>r.json()).then(d=>{if(d.error)throw Error(d.error);currentResult=d;show(d);drawMap(d);animKPIs(d);document.getElementById("loading").style.display="none";document.getElementById("main").style.display="block";}).catch(e=>{document.getElementById("loading").innerHTML='<div class="loading-container"><div style="color:#e74c3c">'+e.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回</button></div>';});
}
function animKPIs(d){
    var items=[{id:"kpiCarbon",v:d.carbon_saved},{id:"kpiVSL",v:d.vsl_saved},{id:"kpiSDG",v:d.sdg_score},{id:"kpiConfidence",v:d.confidence}];
    items.forEach(function(item){animVal(item.id,0,item.v,1200);});
    document.getElementById("kpiDecision").innerText=d.decision;
    document.getElementById("kpiPredicted").innerText=d.traffic.text+" ("+Math.round(d.traffic.predicted_prob*100)+"%)";
}
function animVal(id,s,e,dur){var el=document.getElementById(id);if(!el)return;var rng=e-s,stp=rng/(dur/16),cur=s,tmr=setInterval(function(){cur+=stp;if((stp>0&&cur>=e)||(stp<0&&cur<=e)){cur=e;clearInterval(tmr);}el.innerText=Math.round(cur).toLocaleString();if(id==="kpiSDG")el.innerText=cur.toFixed(1);},16);}
function show(d){
    document.getElementById("decisionBadge").innerText=d.decision;
    document.getElementById("decisionBadge").style.background=d.decision.indexOf("海轉")>=0?"#0077b6":"#e67e22";
    document.getElementById("roadFreight").innerText=fm(d.road.freight);
    document.getElementById("seaFreight").innerText=fm(d.sea.freight);
    document.getElementById("roadCarbon").innerText=Number(d.road.carbon).toLocaleString()+" kg";
    document.getElementById("seaCarbon").innerText=Number(d.sea.carbon).toLocaleString()+" kg";
    document.getElementById("roadTotal").innerText=fm(d.road.total);
    document.getElementById("seaTotal").innerText=fm(d.sea.total);
    document.getElementById("carbonSaved").innerText=Number(d.carbon_saved).toLocaleString();
    document.getElementById("carbonPct").innerText=d.carbon_pct+"%";
    document.getElementById("carbonCredit").innerText=fm(d.carbon_credit);
    document.getElementById("vslSaved").innerText=fm(d.vsl_saved);
    document.getElementById("accidentRisk").innerText=d.accident_risk;
    document.getElementById("sdgScore").innerText=d.sdg_score;
    document.getElementById("bookingAvail").innerText=d.booking_available+" FEU";
    document.getElementById("roadEta").innerText=d.road_eta+"h";
    document.getElementById("seaEta").innerText=d.sea_eta+"h";
    var sh="";if(d.ships&&d.ships.length>0){d.ships.forEach(function(s){sh+='<div style="background:rgba(255,255,255,0.15);padding:0.8rem;border-radius:10px;margin:0.3rem 0;">✅ '+s.ship+'<br>ETD '+s.etd+' → ETA '+s.eta+'（'+s.hours+'h）| 剩餘 '+s.available+' FEU</div>';});}else{sh='<p style="color:#ff6b6b;">⚠️ 暫無可用船班</p>';}
    document.getElementById("shipList").innerHTML=sh;
    var re="";d.reasons.forEach(function(r){re+='<li>'+r+'</li>';});document.getElementById("reasonsList").innerHTML=re;
    document.getElementById("scoreSea").style.width=(d.scores.sea)+"%";
    document.getElementById("scoreRoad").style.width=(d.scores.road)+"%";
    document.getElementById("scoreSeaText").innerText="海運 "+d.scores.sea;
    document.getElementById("scoreRoadText").innerText="公路 "+d.scores.road;
}
function drawMap(data){
    if(mapInstance){mapInstance.remove();mapInstance=null;trafficLines={};}
    if(typeof L==='undefined')return;
    mapInstance=L.map('map').setView([23.5,120.8],7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OSM'}).addTo(mapInstance);
    L.marker([data.start_lat,data.start_lon]).addTo(mapInstance).bindPopup('<b>📍 '+data.start_name+'</b>').openPopup();
    L.marker([data.end_lat,data.end_lon]).addTo(mapInstance).bindPopup('<b>🏁 '+data.end_name+'</b>');
    fetch("/api/traffic_segments").then(r=>r.json()).then(segs=>{segs.forEach(s=>{var color=s.level==="low"?"#27ae60":(s.level==="medium"?"#f39c12":"#e74c3c");var latlngs=s.coords.map(c=>[c[0],c[1]]);var line=L.polyline(latlngs,{color:color,weight:5,opacity:0.9,dashArray:"10,10"}).addTo(mapInstance);line.bindPopup('<b>'+s.name+'</b><br>'+s.speed+' km/h');trafficLines[s.id]=line;});Object.values(trafficLines).forEach(line=>{var offset=0;setInterval(function(){offset=(offset+1)%20;line.setStyle({dashOffset:offset});},80);});});
}
function goCert(){if(currentResult)localStorage.setItem("recordId",currentResult.record_id);location.href="/certificate_page";}