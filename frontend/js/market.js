// ════════════════════════════════════════════
//  SCYLLA v4.0 — market.js
//  Binance WS + Backend WS + Tick + Kline
//  + Sparkline + loadCandles + News
// ════════════════════════════════════════════

let binWS = null;
let beWS  = null;

// ════════════════════════════════════════════
//  CANDLES
// ════════════════════════════════════════════
async function loadCandles(sym, tf){
  $('chartLoading').style.display = 'flex';
  let candles = [];
  try{
    const r = await fetch(`${API}/api/candles/${sym}/${tf}?limit=500`);
    if(r.ok){ const d=await r.json(); candles=d.candles||[]; }
  }catch(e){}
  if(candles.length===0){
    try{
      const r = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${sym}&interval=${tf}&limit=501`);
      const raw = await r.json();
      candles = raw.map(k=>({t:Math.floor(k[0]/1000),o:+k[1],h:+k[2],l:+k[3],c:+k[4],v:+k[5]}));
      log(`Binance direct: ${candles.length}`);
    }catch(e){ log('Candles failed: '+e.message); }
  }
  if(candles.length>0) candles=candles.slice(0,-1);
  setChartData(candles);
  await load24h(sym);
}

async function load24h(sym){
  try{
    let pct=0, openP=0;
    try{
      const r=await fetch(`${API}/api/ticker/24h/${sym}`);
      if(r.ok){ const d=await r.json(); pct=d.change_pct; openP=d.open; }
    }catch(e){}
    if(!openP){
      const r=await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${sym}`);
      const d=await r.json(); pct=+d.priceChangePercent; openP=+d.openPrice;
    }
    if(openP){
      S.open24[sym]=openP;
      const cls=pct>=0?'up':'down';
      const str=(pct>=0?'+':'')+pct.toFixed(2)+'%';
      const key=sym.replace('USDT','');
      const wc=$('w'+key+'c'), hc=$('h'+key+'c');
      if(wc){wc.textContent=str; wc.className='asset-chg '+cls;}
      if(hc){hc.textContent=str; hc.className='ticker-chg '+cls;}
      if(sym===S.sym){
        $('stChg').textContent=str;
        $('stChg').className='stat-val '+(pct>=0?'g':'r');
        $('ctChg').textContent=str;
        $('ctChg').className='ct-chg '+cls;
      }
    }
  }catch(e){}
}

// ════════════════════════════════════════════
//  NEWS — جلب من الباكند
// ════════════════════════════════════════════
async function fetchNews(){
  try{
    const r = await fetch(`${API}/api/news?limit=20`);
    if(!r.ok) return;
    const d = await r.json();
    processNewsItems(d.news || []);
  }catch(e){
    log('News fetch failed: '+e.message);
  }
}

function processNewsItems(items){
  if(!items.length) return;
  items.forEach(item=>{
    // أولوية للعربية — إذا ما وجدت نعرض الإنجليزي مؤقتاً
    const titleAr = item.headline_ar;
    const titleEn = item.headline || '';
    const title   = (titleAr && titleAr !== titleEn) ? titleAr : titleEn;
    const emoji   = item.is_important ? '🔴' : '📰';
    if(title) NewsTicker.add(`${emoji} ${title}`);

    if(item.is_important && typeof handleAlert==='function'){
      handleAlert({
        alert_type: 'news_high_impact',
        title:      '📰 خبر مهم',
        message:    titleAr || titleEn,
        sound:      'news',
      });
    }
  });
  log(`News: ${items.length} articles`);
}
// ════════════════════════════════════════════
//  TICK
// ════════════════════════════════════════════
function onTick(sym, price, ts){
  const prev=S.prices[sym]||price;
  S.prev[sym]=prev; S.prices[sym]=price;
  if(!S.open24[sym]) S.open24[sym]=price;
  S.tpsCount++;
  S.spark[sym].push(price);
  if(S.spark[sym].length>80) S.spark[sym].shift();
  drawSpark(sym);
  const key=sym.replace('USDT','');
  const wp=$('w'+key), hp=$('h'+key);
  const pos=price>=S.open24[sym];
  if(wp){wp.textContent=fmt(price); wp.className='asset-p '+(pos?'up':'down');}
  if(hp){
    hp.textContent=fmt(price);
    const dir=price>prev?'up':'down';
    hp.className='ticker-price '+dir;
    hp.classList.add('flash-'+dir);
    setTimeout(()=>hp.classList.remove('flash-up','flash-down'),400);
  }
  if(sym===S.sym){
    $('ctPrice').textContent=fmt(price);
    $('stPrice').textContent=fmt(price);
    $('tradePrice').placeholder=price.toFixed(2);
    const lat=Math.max(0,Date.now()-ts);
    $('stLat').textContent=lat+' ms';
    $('stLat').className='stat-val '+(lat<300?'g':'r');
    if(Math.random()<0.05) drawOB(price);
  }
  addFeed(sym, price, price>=prev);
}

// ════════════════════════════════════════════
//  KLINE
// ════════════════════════════════════════════
function onKline(k){
  if(k.s!==S.sym||k.i!==S.tf) return;
  updateLiveCandle(k);
  const b=$('kBadge');
  if(b){b.style.borderColor='var(--green)'; b.style.color='var(--green)';}
  if(k.x) log(`Closed: ${k.s} ${k.i} C:${(+k.c).toFixed(2)}`);
}

// ════════════════════════════════════════════
//  SPARKLINE
// ════════════════════════════════════════════
function drawSpark(sym){
  const key=sym.replace('USDT','');
  const c=$('sp'+key); if(!c)return;
  const ctx=c.getContext('2d'), data=S.spark[sym];
  if(data.length<2)return;
  const w=c.parentElement.offsetWidth||200, h=20;
  c.width=w; c.height=h; ctx.clearRect(0,0,w,h);
  const mn=Math.min(...data), mx=Math.max(...data), rng=mx-mn||1;
  const isUp=data[data.length-1]>=data[0];
  const color=isUp?'#00f07a':'#ff2d55';
  ctx.beginPath();
  data.forEach((v,i)=>{
    const x=(i/(data.length-1))*w, y=h-((v-mn)/rng)*(h-3)-1;
    i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  });
  ctx.strokeStyle=color; ctx.lineWidth=1.5; ctx.stroke();
  ctx.lineTo(w,h); ctx.lineTo(0,h); ctx.closePath();
  const g=ctx.createLinearGradient(0,0,0,h);
  g.addColorStop(0,isUp?'rgba(0,240,122,.14)':'rgba(255,45,85,.14)');
  g.addColorStop(1,'transparent');
  ctx.fillStyle=g; ctx.fill();
}

// ════════════════════════════════════════════
//  BINANCE WEBSOCKET
// ════════════════════════════════════════════
function connectBinance(){
  if(binWS){binWS.onclose=null; try{binWS.close();}catch(e){}}
  const s=S.sym.toLowerCase();
  const url=`wss://stream.binance.com:9443/stream?streams=`
           +`btcusdt@trade/ethusdt@trade/bnbusdt@trade/${s}@kline_${S.tf}`;
  binWS=new WebSocket(url);
  binWS.onopen=()=>{S.bOk=true; updateStatus(); log('Binance WS connected');};
  binWS.onmessage=e=>{
    try{
      const raw=JSON.parse(e.data), d=raw.data||raw;
      if(d.e==='trade') onTick(d.s,+d.p,d.T);
      if(d.e==='kline') onKline(d.k);
    }catch(err){}
  };
  binWS.onclose=()=>{S.bOk=false; updateStatus(); setTimeout(connectBinance,3000);};
  binWS.onerror=()=>{};
}

// ════════════════════════════════════════════
//  BACKEND WEBSOCKET
// ════════════════════════════════════════════
function connectBackend(){
  try{
    beWS=new WebSocket(WS_URL);
    beWS.onopen=()=>{
      S.beOk=true; updateStatus(); log('Backend connected');
      // طلب الأخبار فور الاتصال
      beWS.send(JSON.stringify({action:'get_news'}));
    };
    beWS.onmessage=e=>{
      try{
        const d=JSON.parse(e.data);
        // أخبار من الباكند
        if(d.type==='news_update'){
          processNewsUpdate(d.items||[]);   // ← news.js
          return;
        }
        // باقي الرسائل
        if(typeof handleBackendMessage==='function') handleBackendMessage(d);
      }catch(err){}
    };
    beWS.onclose=()=>{S.beOk=false; updateStatus(); setTimeout(connectBackend,5000);};
    beWS.onerror=()=>{};
  }catch(e){}
}

function updateStatus(){
  const ok=S.bOk||S.beOk;
  $('statusDot').className='status-dot '+(ok?'on':'');
  $('statusTxt').textContent=ok?'LIVE':'CONNECTING';
}