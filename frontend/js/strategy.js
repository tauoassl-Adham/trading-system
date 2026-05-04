// ════════════════════════════════════════════
//  SCYLLA v4.0 — strategy.js
//  SMC Strategy Page — Fetch + Render
// ════════════════════════════════════════════

// ── Fetch SMC analysis from backend ──────────
async function fetchSMC(sym){
  $('smcBias').textContent  = 'ANALYZING...';
  $('smcReason').textContent = 'جاري تحليل الهيكل...';
  try{
    const r = await fetch(`${API}/api/smc/${sym}/analyze`);
    const d = await r.json();
    renderSMC(d);
  }catch(e){
    $('smcBias').textContent  = 'OFFLINE';
    $('smcReason').textContent = 'الباكند غير متصل';
  }
}

// ── Render SMC results ────────────────────────
function renderSMC(d){
  if(!d || d.status==='insufficient_data'){
    $('smcBias').textContent  = 'NO DATA';
    $('smcReason').textContent = 'بيانات غير كافية — الباكند يجمع الشموع...';
    return;
  }

  const bias    = d.bias || 'NO_TRADE';
  const bc      = bias==='BUY' ? 'buy' : bias==='SELL' ? 'sell' : 'notrade';
  const conf    = d.confidence || 0;

  // Verdict card
  const card = $('smcVerdict');
  card.className = 'smc-card smc-verdict '+bc;

  const biasEl = $('smcBias');
  biasEl.textContent = bias==='NO_TRADE' ? 'NO TRADE' : bias;
  biasEl.className   = 'smc-bias '+bc;

  $('smcConfLbl').textContent  = `Confidence: ${(conf*100).toFixed(0)}%`;
  $('smcConfBar').style.width  = (conf*100)+'%';
  $('smcConfBar').className    = 'conf-bar '+bc;
  $('smcReason').textContent   = d.reason || '--';

  // Timeframe trends
  ['1d','4h','1h'].forEach(tf=>{
    const el    = $('tr'+tf);
    const trend = d['trend_'+tf] || 'NEUTRAL';
    el.textContent = trend;
    el.className   = 'tf-trend '+trend;
  });

  // Alignment badge
  const al = d.aligned;
  $('alignBadge').className = 'align-badge '+(al?'yes':'no');
  $('alignDot').className   = 'align-dot '+(al?'yes':'no');
  $('alignTxt').textContent = al ? 'ALIGNED ✓' : 'NOT ALIGNED ✗';
  $('alignTxt').className   = 'align-txt '+(al?'yes':'no');

  // Order Block
  if(d.ob){
    $('obType').textContent = d.ob.type.toUpperCase();
    $('obType').className   = 'ob-v '+d.ob.type;
    $('obHigh').textContent = d.ob.high.toFixed(2);
    $('obLow').textContent  = d.ob.low.toFixed(2);
    $('obPOI').textContent  = d.poi_price ? d.poi_price.toFixed(2) : '--';
    $('obFVGTag').innerHTML = d.ob.fvg_aligned
      ? '<span class="smc-tag fvg">FVG ALIGNED ✓</span>'
      : '<span class="smc-tag nofvg">NO FVG</span>';
  } else {
    ['obType','obHigh','obLow','obPOI'].forEach(id=>$(id).textContent='--');
    $('obFVGTag').innerHTML = '<span class="smc-tag nofvg">NO OB</span>';
  }

  // Risk levels
  const fp = p => p ? p.toFixed(2) : '--';
  $('rSL').textContent  = fp(d.sl);
  $('rTP1').textContent = fp(d.tp1);
  $('rTP2').textContent = fp(d.tp2);
  $('rTP3').textContent = fp(d.tp3);

  // Entry scenarios
  if(bias !== 'NO_TRADE' && d.poi_price){
    $('ePE').textContent = `دخول @ ${d.poi_price.toFixed(2)} — OB ${d.ob?.fvg_aligned?'+ FVG':'فقط'}`;
    $('eAE').textContent = `انتظر CHoCH على 1H بعد لمس 4H POI @ ${d.poi_price.toFixed(2)}`;
    $('eCE').textContent = `انتظر sweep أعمق أو إغلاق هيكلي فوق SL @ ${d.sl?d.sl.toFixed(2):'--'}`;
  } else {
    $('ePE').textContent = 'لا يوجد setup — الشروط غير مكتملة';
    $('eAE').textContent = 'انتظر توافق الـ timeframes على اتجاه واحد';
    $('eCE').textContent = 'راقب السوق حتى يتشكل هيكل واضح';
  }

  log(`SMC ${d.symbol||''}: ${bias} ${(conf*100).toFixed(0)}%`);
}

// ── Strategy page events ──────────────────────
function setupStrategy(){

  // Symbol selector
  document.querySelectorAll('.smc-sym-btn').forEach(b=>{
    b.onclick = ()=>{
      document.querySelectorAll('.smc-sym-btn').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      S.smcSym = b.dataset.ssym;
      fetchSMC(S.smcSym);
    };
  });

  // Manual refresh
  $('smcAnalyzeBtn').onclick = ()=> fetchSMC(S.smcSym);

  // Auto refresh كل 5 دقائق إذا الصفحة مفتوحة
  setInterval(()=>{
    if($('page-strategy').classList.contains('active'))
      fetchSMC(S.smcSym);
  }, 5*60*1000);
}