// ════════════════════════════════════════════
//  SCYLLA v4.0 — ui.js
//  OrderBook (Simulated + Live) + Live Feed
//  + Trade Panel + Sparklines + Depth Chart
//
//  المسار: frontend/js/ui.js
// ════════════════════════════════════════════
'use strict';

// ══════════════════════════════════════════
//  ORDER BOOK STATE
// ══════════════════════════════════════════
const OB = {
  asks: [],        // [{price, size, total}]
  bids: [],        // [{price, size, total}]
  levels: 12,      // عدد مستويات السعر لكل جهة
  spread: 0,
  midPrice: 0,
  maxTotal: 0,     // لحساب نسبة الشريط
  lastUpdate: 0,
  animFrame: null,

  // إعدادات العرض
  precision: 2,    // منازل عشرية للسعر
  grouping: 1,     // تجميع الأسعار (1=none, 10=round to 10, etc.)
};

// ══════════════════════════════════════════
//  SIMULATED ORDER BOOK ENGINE
//  يولّد بيانات واقعية بناءً على السعر الحي
// ══════════════════════════════════════════
function generateOrderBook(midPrice, sym){
  if(!midPrice || midPrice <= 0) return;

  // spread واقعي حسب الرمز
  const spreadPct = sym === 'BTCUSDT' ? 0.01 : sym === 'ETHUSDT' ? 0.012 : 0.015;
  const spread    = midPrice * spreadPct / 100;
  const step      = midPrice < 100 ? 0.01 : midPrice < 1000 ? 0.1 : 1;

  // توليد asks (بائعون — فوق السعر)
  OB.asks = [];
  let askAccum = 0;
  for(let i = 1; i <= OB.levels; i++){
    const price = midPrice + spread/2 + step * i * (1 + Math.random() * 0.3);
    const size  = randomSize(sym, price, 'ask', i);
    askAccum   += size * price;
    OB.asks.push({
      price: parseFloat(price.toFixed(OB.precision)),
      size:  parseFloat(size.toFixed(4)),
      total: parseFloat(askAccum.toFixed(2)),
    });
  }

  // توليد bids (مشترون — تحت السعر)
  OB.bids = [];
  let bidAccum = 0;
  for(let i = 1; i <= OB.levels; i++){
    const price = midPrice - spread/2 - step * i * (1 + Math.random() * 0.3);
    const size  = randomSize(sym, price, 'bid', i);
    bidAccum   += size * price;
    OB.bids.push({
      price: parseFloat(price.toFixed(OB.precision)),
      size:  parseFloat(size.toFixed(4)),
      total: parseFloat(bidAccum.toFixed(2)),
    });
  }

  OB.spread   = parseFloat((OB.asks[0].price - OB.bids[0].price).toFixed(OB.precision));
  OB.midPrice = midPrice;
  OB.maxTotal = Math.max(
    OB.asks[OB.asks.length - 1]?.total || 0,
    OB.bids[OB.bids.length - 1]?.total || 0
  );
  OB.lastUpdate = Date.now();
}

function randomSize(sym, price, side, level){
  // حجم واقعي — BTC أصغر، BNB أكبر
  const base = sym === 'BTCUSDT' ? 0.05 : sym === 'ETHUSDT' ? 0.4 : 2.0;
  const decay = Math.exp(-level * 0.15);   // أحجام أصغر بعيداً عن السعر
  const noise = 0.5 + Math.random() * 1.5;
  // أحياناً wall كبير
  const wall  = Math.random() < 0.08 ? 8 + Math.random() * 12 : 1;
  return base * decay * noise * wall;
}

// ══════════════════════════════════════════
//  DRAW ORDER BOOK
// ══════════════════════════════════════════
function drawOB(midPrice){
  const sym = S.sym;
  generateOrderBook(midPrice || S.prices[sym] || 0, sym);
  renderOrderBook();
}

function renderOrderBook(){
  const askEl = $('askRows');
  const bidEl = $('bidRows');
  const sprEl = $('obSpread');
  if(!askEl || !bidEl) return;

  // Asks (معكوسة — الأقرب للسعر في الأسفل)
  const asksHTML = [...OB.asks].reverse().map(row => buildOBRow(row, 'ask')).join('');
  // Bids (الأقرب للسعر في الأعلى)
  const bidsHTML = OB.bids.map(row => buildOBRow(row, 'bid')).join('');

  askEl.innerHTML = asksHTML;
  bidEl.innerHTML = bidsHTML;

  if(sprEl){
    const spreadPct = OB.midPrice > 0
      ? (OB.spread / OB.midPrice * 100).toFixed(4)
      : '0.0000';
    sprEl.innerHTML =
      `<span style="color:var(--text-dim)">SPREAD</span> ` +
      `<span style="color:var(--yellow)">${fmt(OB.spread)}</span> ` +
      `<span style="color:var(--text-dim);font-size:10px">(${spreadPct}%)</span>`;
  }

  // Depth summary bar
  renderDepthBar();
}

function buildOBRow(row, side){
  const fillPct = OB.maxTotal > 0
    ? Math.min(100, (row.total / OB.maxTotal) * 100).toFixed(1)
    : 0;
  const sizeStr  = row.size >= 1
    ? row.size.toFixed(3)
    : row.size.toFixed(4);
  const totalStr = row.total >= 1000
    ? (row.total/1000).toFixed(1) + 'K'
    : row.total.toFixed(1);

  return `
    <div class="ob-row ob-${side}">
      <div class="ob-fill" style="width:${fillPct}%"></div>
      <span class="ob-price-${side}">${fmt(row.price)}</span>
      <span class="ob-size">${sizeStr}</span>
      <span class="ob-total">${totalStr}</span>
    </div>`;
}

// ── Depth Summary Bar (بائع vs مشتري) ──
function renderDepthBar(){
  const el = $('obDepthBar');
  if(!el) return;

  const totalAsk = OB.asks.reduce((a,r)=>a+r.size*r.price,0);
  const totalBid = OB.bids.reduce((a,r)=>a+r.size*r.price,0);
  const combined = totalAsk + totalBid;
  if(!combined) return;

  const bidPct = (totalBid / combined * 100).toFixed(1);
  const askPct = (totalAsk / combined * 100).toFixed(1);

  el.innerHTML = `
    <div class="ob-depth-label">
      <span style="color:var(--green)">▲ ${bidPct}%</span>
      <span style="font-size:10px;color:var(--text-dim)">DEPTH</span>
      <span style="color:var(--red)">▼ ${askPct}%</span>
    </div>
    <div class="ob-depth-track">
      <div class="ob-depth-bid" style="width:${bidPct}%"></div>
      <div class="ob-depth-ask" style="width:${askPct}%"></div>
    </div>`;
}

// ══════════════════════════════════════════
//  LIVE FEED
// ══════════════════════════════════════════
const FEED = {
  maxItems: 80,
  paused:   false,
  buffer:   [],
  flushInterval: null,
};

function addFeed(sym, price, isBuy){
  if(FEED.paused) return;

  const size = (Math.random() * 2 + 0.01).toFixed(4);
  const time = new Date().toLocaleTimeString('en-US',{hour12:S.use12h, hour:'2-digit', minute:'2-digit', second:'2-digit'});
  const side = isBuy ? 'buy' : 'sell';

  FEED.buffer.push({ sym, price, size, time, side });
  if(FEED.buffer.length > 10) FEED.buffer.shift();   // لا تتراكم
}

function flushFeed(){
  if(!FEED.buffer.length) return;
  const body = $('feedBody');
  if(!body) return;

  const frag = document.createDocumentFragment();
  FEED.buffer.forEach(item => {
    const div = document.createElement('div');
    div.className = `feed-item ${item.side}`;
    div.innerHTML =
      `<span class="fsym">${item.sym.replace('USDT','')}</span>` +
      `<span class="fp-${item.side}">${fmt(item.price)}</span>` +
      `<span class="ob-size">${item.size}</span>` +
      `<span class="ft">${item.time}</span>`;
    frag.appendChild(div);
  });
  FEED.buffer = [];

  body.insertBefore(frag, body.firstChild);

  // حذف الزائد
  while(body.children.length > FEED.maxItems){
    body.removeChild(body.lastChild);
  }

  // تحديث العداد
  S.feedCount += FEED.buffer.length;
  const cnt = $('feedCnt');
  if(cnt) cnt.textContent = `${body.children.length} TICKS`;
}

// ══════════════════════════════════════════
//  TRADE PANEL SETUP
// ══════════════════════════════════════════
function setupTradePanel(){
  const buyTab  = $('buyTab');
  const sellTab = $('sellTab');
  const execBtn = $('execBtn');
  const qtyInp  = $('tradeQty');
  const prcInp  = $('tradePrice');

  if(buyTab) buyTab.onclick = () => {
    S.mode = 'buy';
    buyTab.classList.add('active');
    sellTab?.classList.remove('active');
    if(execBtn){
      execBtn.className = 'exec-btn buy';
      execBtn.querySelector('.t')?.setAttribute('data-ar','تنفيذ شراء');
      execBtn.querySelector('.t')?.setAttribute('data-en','Execute BUY');
      if(S.lang==='ar') execBtn.querySelector('.t').textContent='تنفيذ شراء';
      else execBtn.querySelector('.t').textContent='Execute BUY';
    }
  };

  if(sellTab) sellTab.onclick = () => {
    S.mode = 'sell';
    sellTab.classList.add('active');
    buyTab?.classList.remove('active');
    if(execBtn){
      execBtn.className = 'exec-btn sell';
      execBtn.querySelector('.t')?.setAttribute('data-ar','تنفيذ بيع');
      execBtn.querySelector('.t')?.setAttribute('data-en','Execute SELL');
      if(S.lang==='ar') execBtn.querySelector('.t').textContent='تنفيذ بيع';
      else execBtn.querySelector('.t').textContent='Execute SELL';
    }
  };

  if(execBtn) execBtn.onclick = () => {
    const qty  = parseFloat(qtyInp?.value || 100);
    const price = parseFloat(prcInp?.value || S.prices[S.sym] || 0);
    if(!qty || qty <= 0){ toast('أدخل كمية صحيحة','var(--red)'); return; }

    // تفويض لـ trading.js إذا موجود
    if(typeof placeOrder === 'function'){
      placeOrder({
        side:    S.mode.toUpperCase(),
        type:    price > 0 ? 'LIMIT' : 'MARKET',
        usdtQty: qty,
        price:   price > 0 ? price : null,
      });
    } else {
      // fallback بسيط
      const emoji = S.mode === 'buy' ? '🟢' : '🔴';
      toast(`${emoji} ${S.mode.toUpperCase()} ${qty} USDT @ ${fmt(price||S.prices[S.sym])}`, 'var(--accent)');
      log(`${S.mode.toUpperCase()}: ${qty} USDT @ ${fmt(price||S.prices[S.sym])}`);
    }
  };

  // تحديث السعر التلقائي عند تغيير الرمز
  setInterval(() => {
    if(prcInp && !document.activeElement === prcInp){
      prcInp.placeholder = S.prices[S.sym] ? S.prices[S.sym].toFixed(2) : 'Market';
    }
  }, 2000);
}

// ══════════════════════════════════════════
//  SPARKLINES
// ══════════════════════════════════════════
function drawSpark(sym){
  const key  = sym.replace('USDT','');
  const c    = $('sp' + key);
  if(!c) return;

  const ctx  = c.getContext('2d');
  const data = S.spark[sym];
  if(!data || data.length < 2) return;

  const w = c.parentElement.offsetWidth || 200;
  const h = 20;
  c.width  = w;
  c.height = h;
  ctx.clearRect(0, 0, w, h);

  const mn  = Math.min(...data);
  const mx  = Math.max(...data);
  const rng = mx - mn || 1;
  const isUp = data[data.length - 1] >= data[0];
  const col  = isUp ? '#00f07a' : '#ff2d55';

  // Draw line
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - mn) / rng) * (h - 3) - 1;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = col;
  ctx.lineWidth   = 1.5;
  ctx.stroke();

  // Fill gradient
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, isUp ? 'rgba(0,240,122,.18)' : 'rgba(255,45,85,.18)');
  g.addColorStop(1, 'transparent');
  ctx.fillStyle = g;
  ctx.fill();
}

// ══════════════════════════════════════════
//  OB GROUPING CONTROL
// ══════════════════════════════════════════
function setOBGrouping(val){
  OB.grouping = val;
  drawOB(S.prices[S.sym]);
}

function setOBLevels(n){
  OB.levels = Math.min(20, Math.max(5, n));
  drawOB(S.prices[S.sym]);
}

// ══════════════════════════════════════════
//  INJECT UI CSS ADDITIONS
// ══════════════════════════════════════════
function injectUICSS(){
  if(document.getElementById('uiExtCSS')) return;
  const style = document.createElement('style');
  style.id = 'uiExtCSS';
  style.textContent = `
    /* ── OB Depth Bar ── */
    #obDepthBar{
      padding:5px 7px;
      border-top:1px solid var(--border);
      border-bottom:1px solid var(--border);
      flex-shrink:0;
    }
    .ob-depth-label{
      display:flex;justify-content:space-between;align-items:center;
      font-family:'Share Tech Mono',monospace;font-size:10px;margin-bottom:3px;
    }
    .ob-depth-track{
      height:4px;border-radius:2px;overflow:hidden;
      background:var(--bg-card2);display:flex;
    }
    .ob-depth-bid{height:100%;background:var(--green);border-radius:2px 0 0 2px;transition:width .4s;}
    .ob-depth-ask{height:100%;background:var(--red);  border-radius:0 2px 2px 0;transition:width .4s;}

    /* ── OB Header extra controls ── */
    .ob-controls{
      display:flex;align-items:center;gap:6px;
      padding:4px 7px;border-bottom:1px solid var(--border);
      background:var(--bg-card);flex-shrink:0;
    }
    .ob-ctrl-btn{
      padding:2px 7px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      cursor:pointer;border-radius:2px;transition:all .15s;
    }
    .ob-ctrl-btn:hover{border-color:var(--accent);color:var(--accent);}
    .ob-ctrl-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(0,180,255,.08);}
    .ob-ctrl-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);}

    /* ── Feed Controls ── */
    .feed-controls{
      display:flex;align-items:center;gap:4px;
      padding:4px 7px;border-bottom:1px solid var(--border);
      background:var(--bg-card);flex-shrink:0;
    }
    .feed-ctrl-btn{
      padding:2px 6px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:9px;color:var(--text-dim);
      cursor:pointer;border-radius:2px;transition:all .15s;
    }
    .feed-ctrl-btn:hover{border-color:var(--border-glow);color:var(--text-secondary);}
    .feed-ctrl-btn.active{border-color:var(--yellow);color:var(--yellow);}

    /* ── ob-row hover ── */
    .ob-row{
      cursor:crosshair;
      transition:background .1s;
    }
    .ob-row:hover{background:rgba(255,255,255,.03);}

    /* ── Feed item size col ── */
    .feed-item .ob-size{
      color:var(--text-dim);
      font-size:var(--fs-xs);
      text-align:center;
    }

    /* ── Depth tooltip on hover ── */
    .ob-row:hover .ob-total{
      color:var(--accent);
    }
  `;
  document.head.appendChild(style);
}

// ══════════════════════════════════════════
//  INJECT EXTRA HTML INTO EXISTING PANELS
// ══════════════════════════════════════════
function enhanceOrderBookPanel(){
  const obBody = document.querySelector('.ob-body');
  if(!obBody || $('obDepthBar')) return;

  // أضف controls فوق الـ header
  const ctrl = document.createElement('div');
  ctrl.className = 'ob-controls';
  ctrl.innerHTML = `
    <span class="ob-ctrl-lbl">LEVELS</span>
    <button class="ob-ctrl-btn" onclick="setOBLevels(8)">8</button>
    <button class="ob-ctrl-btn active" onclick="setOBLevels(12)">12</button>
    <button class="ob-ctrl-btn" onclick="setOBLevels(16)">16</button>
    <span style="flex:1"></span>
    <span class="ob-ctrl-lbl">GROUP</span>
    <button class="ob-ctrl-btn active" onclick="setOBGrouping(1)">0.1</button>
    <button class="ob-ctrl-btn" onclick="setOBGrouping(10)">1</button>
    <button class="ob-ctrl-btn" onclick="setOBGrouping(100)">10</button>
  `;
  obBody.insertBefore(ctrl, obBody.querySelector('.ob-hdr'));

  // أضف depth bar بين asks و bids
  const spread = $('obSpread');
  if(spread){
    const bar = document.createElement('div');
    bar.id = 'obDepthBar';
    obBody.insertBefore(bar, spread);
  }
}

function enhanceFeedPanel(){
  const feedPanel = document.querySelector('.live-feed');
  if(!feedPanel || $('feedControls')) return;

  const ph = feedPanel.querySelector('.ph');
  if(!ph) return;

  const ctrl = document.createElement('div');
  ctrl.id        = 'feedControls';
  ctrl.className = 'feed-controls';
  ctrl.innerHTML = `
    <button class="feed-ctrl-btn ${!FEED.paused?'active':''}" id="feedPauseBtn"
      onclick="toggleFeedPause()">
      ${FEED.paused ? '▶ RESUME' : '⏸ PAUSE'}
    </button>
    <button class="feed-ctrl-btn" onclick="clearFeed()">🗑 CLEAR</button>
    <span style="flex:1"></span>
    <span style="font-family:'Share Tech Mono',monospace;font-size:9px;color:var(--text-dim)" id="feedBuyPct">B:--% S:--%</span>
  `;
  ph.after(ctrl);
}

function toggleFeedPause(){
  FEED.paused = !FEED.paused;
  const btn = $('feedPauseBtn');
  if(btn){
    btn.textContent = FEED.paused ? '▶ RESUME' : '⏸ PAUSE';
    btn.classList.toggle('active', !FEED.paused);
  }
}

function clearFeed(){
  const body = $('feedBody');
  if(body) body.innerHTML = '';
  S.feedCount = 0;
  const cnt = $('feedCnt');
  if(cnt) cnt.textContent = '0 TICKS';
}

// ── تحديث نسبة شراء/بيع ──
function updateFeedStats(){
  const body = $('feedBody');
  const el   = $('feedBuyPct');
  if(!body || !el) return;

  const rows  = body.querySelectorAll('.feed-item');
  const total = rows.length;
  if(!total) return;

  let buys = 0;
  rows.forEach(r => { if(r.classList.contains('buy')) buys++; });
  const buyPct  = (buys / total * 100).toFixed(0);
  const sellPct = (100 - buyPct);
  el.innerHTML =
    `<span style="color:var(--green)">B:${buyPct}%</span> ` +
    `<span style="color:var(--red)">S:${sellPct}%</span>`;
}

// ══════════════════════════════════════════
//  STRATEGY PAGE SETUP
// ══════════════════════════════════════════
function setupStrategy(){
  // أزرار رمز SMC
  document.querySelectorAll('.smc-sym-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.smc-sym-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      S.smcSym = btn.dataset.ssym;
      fetchSMC(S.smcSym);
    };
  });

  // زر التحليل
  const analyzeBtn = $('smcAnalyzeBtn');
  if(analyzeBtn) analyzeBtn.onclick = () => fetchSMC(S.smcSym, true);
}

// ══════════════════════════════════════════
//  SMC FETCH + RENDER
// ══════════════════════════════════════════
async function fetchSMC(sym, force=false){
  const btn = $('smcAnalyzeBtn');
  if(btn){ btn.disabled=true; btn.textContent='⏳ ANALYZING...'; }

  try{
    const r = await fetch(`${API}/api/smc/${sym}/analyze`);
    if(r.ok){
      const d = await r.json();
      renderSMC({ ...d, symbol:sym });
    } else {
      renderSMCPlaceholder(sym);
    }
  }catch(e){
    renderSMCPlaceholder(sym);
  }

  if(btn){ btn.disabled=false; btn.textContent='⟳ ANALYZE'; }
}

function renderSMCPlaceholder(sym){
  const bias = $('smcBias');
  if(bias){ bias.textContent='NO DATA'; bias.className='smc-bias notrade'; }
  const reason = $('smcReason');
  if(reason) reason.textContent = `تعذر الاتصال بالخادم للحصول على تحليل ${sym}`;
}

function renderSMC(d){
  if(!d) return;

  const bias        = (d.bias || 'NO_TRADE').toUpperCase();
  const confidence  = parseFloat(d.confidence || 0);
  const confPct     = (confidence * 100).toFixed(0);
  const biasClass   = bias==='BUY'?'buy': bias==='SELL'?'sell':'notrade';

  // Verdict card
  const verdict = $('smcVerdict');
  if(verdict){
    verdict.className = `smc-card smc-verdict ${biasClass}`;
  }
  const biasEl = $('smcBias');
  if(biasEl){ biasEl.textContent = bias; biasEl.className = `smc-bias ${biasClass}`; }

  const confLbl = $('smcConfLbl');
  if(confLbl) confLbl.textContent = `Confidence: ${confPct}%`;
  const confBar = $('smcConfBar');
  if(confBar){ confBar.style.width = confPct+'%'; confBar.className = `conf-bar ${biasClass}`; }

  const reason = $('smcReason');
  if(reason) reason.textContent = d.reason || d.analysis || 'لا يوجد تفسير متاح';

  // Market Structure
  const tfs = d.timeframe_trends || {};
  ['1d','4h','1h'].forEach(tf => {
    const el = $(('tr'+tf).replace('1d','tr1d').replace('4h','tr4h').replace('1h','tr1h'));
    const val = $('tr'+tf);
    if(val){
      const trend = (tfs[tf] || tfs[tf.toUpperCase()] || 'NEUTRAL').toUpperCase();
      val.textContent = trend;
      val.className   = `tf-trend ${trend}`;
    }
  });

  // Alignment
  const aligned = d.aligned || d.trend_aligned || false;
  const alignBadge = $('alignBadge');
  const alignDot   = $('alignDot');
  const alignTxt   = $('alignTxt');
  if(alignBadge) alignBadge.className = `align-badge ${aligned?'yes':'no'}`;
  if(alignDot)   alignDot.className   = `align-dot ${aligned?'yes':'no'}`;
  if(alignTxt){
    alignTxt.textContent = aligned ? 'ALIGNED ✓' : 'NOT ALIGNED';
    alignTxt.className   = `align-txt ${aligned?'yes':'no'}`;
  }

  // Order Block
  const ob = d.order_block || d.ob || {};
  const setEl = (id,val,cls='')=>{
    const el=$(id);
    if(el){ el.textContent=val||'--'; if(cls) el.className=`ob-v ${cls}`; }
  };
  setEl('obType',  ob.type || d.ob_type,   (ob.type||'').toLowerCase());
  setEl('obHigh',  ob.high ? fmt(ob.high) : '--');
  setEl('obLow',   ob.low  ? fmt(ob.low)  : '--');
  setEl('obPOI',   d.poi_price ? fmt(d.poi_price) : '--', 'accent');

  const fvgEl = $('obFVGTag');
  if(fvgEl){
    const hasFVG = d.fvg || d.has_fvg;
    fvgEl.innerHTML = hasFVG
      ? `<span class="smc-tag fvg">✓ FVG PRESENT</span>`
      : `<span class="smc-tag nofvg">NO FVG</span>`;
  }

  // Risk Management
  const risk = d.risk || d.risk_management || {};
  setEl('rSL',  risk.sl  || d.stop_loss ? fmt(risk.sl||d.stop_loss)  : '--');
  setEl('rTP1', risk.tp1 || d.tp1       ? fmt(risk.tp1||d.tp1)       : '--');
  setEl('rTP2', risk.tp2 || d.tp2       ? fmt(risk.tp2||d.tp2)       : '--');
  setEl('rTP3', risk.tp3 || d.tp3       ? fmt(risk.tp3||d.tp3)       : '--');

  // Entry Scenarios
  const entries = d.entries || d.entry_scenarios || {};
  const setEntry = (id, val) => {
    const el=$(id); if(el && val) el.textContent=val;
  };
  setEntry('ePE', entries.primary      || entries.pe);
  setEntry('eAE', entries.alternative  || entries.ae);
  setEntry('eCE', entries.conservative || entries.ce);

  log(`SMC: ${d.symbol} → ${bias} (${confPct}%)`);
}

// ══════════════════════════════════════════
//  INIT UI
// ══════════════════════════════════════════
function initUI(){
  injectUICSS();
  enhanceOrderBookPanel();
  enhanceFeedPanel();

  // Flush feed كل 250ms
  FEED.flushInterval = setInterval(flushFeed, 250);

  // تحديث feed stats كل ثانيتين
  setInterval(updateFeedStats, 2000);

  // OB يتحدث عند تغيير السعر (يُستدعى من onTick في market.js)
  // if(Math.random()<0.05) drawOB(price);  ← موجود في market.js

  log('UI initialized — OrderBook + Feed + Depth + Controls');
}

// ── استدعاء initUI من init() في app.js ──
// أضف في init():  initUI();