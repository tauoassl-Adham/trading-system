// ════════════════════════════════════════════
//  SCYLLA v4.0 — app.js
//  Init + Nav + Theme + Lang + Clock + Events
// ════════════════════════════════════════════

function setTheme(t){
  S.theme=t;
  document.documentElement.setAttribute('data-theme',t);
  $('themeBtn').textContent=t==='dark'?'🌙':'☀️';
  localStorage.setItem('sc-theme',t);
  updateChartTheme();
}

function setLang(l){
  S.lang=l;
  const h=document.documentElement;
  h.setAttribute('data-lang',l);
  h.setAttribute('lang',l);
  h.setAttribute('dir',l==='ar'?'rtl':'ltr');
  $('langBtn').textContent=l==='ar'?'EN':'ع';
  document.querySelectorAll('.t[data-'+l+']')
    .forEach(e=>e.textContent=e.getAttribute('data-'+l));
  localStorage.setItem('sc-lang',l);
}

function setupClock(){
  setInterval(()=>{
    $('timeTxt').textContent=
      new Date().toLocaleTimeString('en-US',{hour12:S.use12h});
  },1000);
  $('timeTxt').onclick=()=>{
    S.use12h=!S.use12h;
    localStorage.setItem('sc-12h',S.use12h);
    toast(S.use12h?'12h mode':'24h mode');
  };
}

function setupTPS(){
  setInterval(()=>{$('stTPS').textContent=S.tpsCount; S.tpsCount=0;},1000);
}

function showPage(name){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  const page=$('page-'+name);
  if(page) page.classList.add('active');
  document.querySelectorAll('.nav-btn[data-page="'+name+'"]')
    .forEach(b=>b.classList.add('active'));
  if(name==='strategy') fetchSMC(S.smcSym);
  if(name==='dashboard'&&tvChart) tvChart.timeScale().scrollToRealTime();
}

function setupNav(){
  document.querySelectorAll('.nav-btn[data-page]').forEach(b=>{
    b.onclick=()=>showPage(b.dataset.page);
  });
}

function setupWatchlist(){
  document.querySelectorAll('.asset-card[data-sym]').forEach(card=>{
    card.onclick=()=>{
      document.querySelectorAll('.asset-card').forEach(c=>c.classList.remove('active'));
      card.classList.add('active');
      S.sym=card.dataset.sym;
      $('ctSym').textContent=S.sym.replace('USDT','/USDT');
      $('obSym').textContent=S.sym.replace('USDT','/USDT');
      $('stSub').textContent=S.sym.replace('USDT','/USDT');
      $('chartLoading').style.display='flex';
      connectBinance();
      loadCandles(S.sym,S.tf);
      log('Switched to '+S.sym);
    };
  });
}

function setupTF(){
  document.querySelectorAll('.tf-btn').forEach(b=>{
    b.onclick=()=>{
      document.querySelectorAll('.tf-btn').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      const tf=b.dataset.tf;
      if(tf){
        S.tf=tf;
        $('chartLoading').style.display='flex';
        connectBinance();
        loadCandles(S.sym,S.tf);
        log('Timeframe: '+tf);
      }
    };
  });
}

function setupHeaderBtns(){
  $('themeBtn').onclick=()=>setTheme(S.theme==='dark'?'light':'dark');
  $('langBtn').onclick=()=>setLang(S.lang==='ar'?'en':'ar');
}

// ── معالجة رسائل الباكند ──────────────────────
function handleBackendMessage(d){
  if(d.type==='alert'){
    handleAlert(d);
    return;
  }
  if(d.type==='smc_analysis'){
    if($('page-strategy').classList.contains('active')) renderSMC(d);
    if(d.bias&&d.bias!=='NO_TRADE'&&d.confidence>0.7){
      NewsTicker.add(
        `${d.bias==='BUY'?'🟢':'🔴'} إشارة SMC: ${d.symbol} ${d.bias} @ ${d.poi_price?.toFixed(2)} | ثقة: ${(d.confidence*100).toFixed(0)}%`
      );
    }
    return;
  }
  if(d.type==='choch_detected'){
    NewsTicker.add(`⚡ CHoCH: ${d.symbol} — ${d.choch_type||''} @ ${d.price?.toFixed(2)}`);
    return;
  }
  if(d.type==='bos_detected'){
    NewsTicker.add(`📐 BOS: ${d.symbol} @ ${d.price?.toFixed(2)}`);
    return;
  }
  if(d.type==='signal_closed'){
    const emoji=d.status?.includes('TP')?'✅':'❌';
    NewsTicker.add(`${emoji} ${d.status}: ${d.symbol} | PnL: ${d.pnl_pct?.toFixed(2)}%`);
    return;
  }
  if(d.type==='trade_signal'||d.action){
    log('Signal: '+(d.action||d.type));
    toast('Signal: '+(d.action||d.type),'var(--green)');
  }
}

// ════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════
function init(){
  setTheme(S.theme);
  setLang(S.lang);
  setupClock();
  setupTPS();
  setupNav();
  setupHeaderBtns();
  setupWatchlist();
  setupTF();
  setupZoom();
  setupMAToggle();
  setupTradePanel();
  setupStrategy();
  initNews();
  

  // تهيئة الشارت
  initChart();

  // تهيئة نظام التنبيهات
  initAlerts();

  // الاتصالات — الأخبار تأتي تلقائياً من الباكند
  connectBinance();
  connectBackend();

  // تحميل بيانات أولية
  loadCandles('BTCUSDT','5m');
  drawOB(95000);

  log('Scylla v4.0 ready — AI + SMC + Alerts + News (AR)');
}

document.addEventListener('DOMContentLoaded', init);