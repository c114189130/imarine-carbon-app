var currentResult = null;
function fm(v){ return "NT$ "+Number(v||0).toLocaleString(); }

function calculate(){
    var s=localStorage.getItem("start"), e=localStorage.getItem("end");
    var c=localStorage.getItem("containers"), u=localStorage.getItem("unit")||"FEU";
    var td=localStorage.getItem("targetDate")||"";
    if(!s||!e||!c){alert("請先填資料");location.href="/input";return;}

    fetch("/calculate",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({start:s,end:e,containers:c,unit:u,target_date:td})})
    .then(r=>r.json()).then(d=>{
        if(d.error) throw new Error(d.error);
        currentResult=d; show(d);
        document.getElementById("loading").style.display="none";
        document.getElementById("main").style.display="block";
    }).catch(e=>{
        document.getElementById("loading").innerHTML='<div class="loading-container"><div style="color:#e74c3c">'+e.message+'</div><button class="btn btn-primary" onclick="location.href=\'/input\'">返回</button></div>';
    });
}

function show(d){
    var isSea=d.decision.indexOf("海轉")>=0;
    document.getElementById("decisionBadge").innerText=d.decision;
    document.getElementById("decisionBadge").style.background=isSea?"#0077b6":"#e67e22";
    document.getElementById("routeInfo").innerText=d.start_name+" → "+d.end_name+" | "+d.containers+" | 目標到貨："+d.target_date;

    // 成本表
    document.getElementById("roadFreight").innerText=fm(d.road.freight);
    document.getElementById("seaFreight").innerText=fm(d.sea.freight);
    document.getElementById("roadCarbonFee").innerText=fm(d.road.carbon_fee);
    document.getElementById("seaCarbonFee").innerText=fm(d.sea.carbon_fee);
    document.getElementById("roadCarbon").innerText=Number(d.road.carbon).toLocaleString()+" kg";
    document.getElementById("seaCarbon").innerText=Number(d.sea.carbon).toLocaleString()+" kg";
    document.getElementById("roadTotal").innerText=fm(d.road.total);
    document.getElementById("seaTotal").innerText=fm(d.sea.total);

    // 時間
    document.getElementById("roadEta").innerText=(d.road_ok?"✅ ":"⚠️ ")+d.road_eta+"（"+d.road_hours+"h）";

    // 碳排改善
    document.getElementById("carbonSaved").innerText=Number(d.carbon_saved).toLocaleString();
    document.getElementById("carbonPct").innerText=d.carbon_pct;
    document.getElementById("carbonCredit").innerText=fm(d.carbon_credit);

    // 路況
    document.getElementById("congestion").innerText=d.traffic.level_text+" | 國一 "+d.traffic.nh1+"km/h | 國三 "+d.traffic.nh3+"km/h";

    // 船班
    var sh="";
    if(d.ships&&d.ships.length>0){
        d.ships.forEach(function(s,i){
            sh+='<div style="background:rgba(255,255,255,0.15);padding:0.8rem;border-radius:10px;margin:0.3rem 0;">'+
                '✅ '+s.ship+'（'+s.weekday+'）<br>ETD '+s.etd+' → ETA '+s.eta+'（'+s.hours+'h）| '+s.capacity+' FEU</div>';
        });
    } else { sh='<p>暫無可用船班</p>'; }
    document.getElementById("shipList").innerHTML=sh;

    // 決策原因
    var re="";
    d.reasons.forEach(function(r){ re+='<li>'+r+'</li>'; });
    document.getElementById("reasonsList").innerHTML=re;

    // 路線文字
    document.getElementById("routeText").innerHTML=
        '🚛 陸拖：'+d.start_name+' → '+d.end_name+'（'+d.road_km+'km，約'+d.road_hours+'h）<br>'+
        '🚢 海轉：'+d.start_name+' → '+d.end_name+'（'+d.sea_km+'km）<br>'+
        '📅 固定航班：立昌輪(二、五)、立揚輪(三、六)';
}

function goCert(){
    if(currentResult) localStorage.setItem("recordId",currentResult.record_id);
    location.href="/certificate_page";
}
// ... (前面的 calculate, show 函數保持不變)

// ========== 地圖路段更新 ==========
function updateFreewayMap() {
    fetch("/api/traffic_segments")
    .then(function(r){ return r.json(); })
    .then(function(data){
        data.forEach(function(seg){
            var el = document.getElementById("seg-"+seg.id);
            if(el){
                var color = seg.level === "low" ? "#27ae60" : (seg.level === "medium" ? "#f39c12" : "#e74c3c");
                el.style.background = color;
                el.title = seg.name + " (" + (seg.dir==="north"?"北上":"南下") + "): " + seg.speed + " km/h";
            }
        });
    });
}

// 頁面載入時產生路段 DOM
function buildSegmentUI() {
    var container = document.getElementById("freewaySegments");
    if(!container) return;
    var html = "";
    for(var hw in FREEWAY_SEGMENTS){
        html += '<h4>'+FREEWAY_SEGMENTS[hw].name+'</h4><div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:1rem;">';
        FREEWAY_SEGMENTS[hw].segments.forEach(function(seg){
            html += '<div id="seg-'+seg.id+'" style="flex:1;min-width:60px;height:30px;background:#999;border-radius:4px;cursor:pointer;" title="'+seg.name+'"></div>';
        });
        html += '</div>';
    }
    container.innerHTML = html;
    updateFreewayMap();
    setInterval(updateFreewayMap, 60000);
}

// 在 show() 函數最後呼叫 buildSegmentUI()