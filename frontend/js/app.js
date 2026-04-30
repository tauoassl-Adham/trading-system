// ════════════════════════════════════════════
//  SCYLLA v4.0 — app.js
//  Init + Nav + Theme + Lang + Clock + Events
// ════════════════════════════════════════════

// ════════════════════════════════════════════
//  THEME
// ════════════════════════════════════════════
function setTheme(t){
  S.theme = t;
  document.documentElement.setAttribute('data-theme', t);
  $('themeBtn').textContent = t==='dark' ? '🌙' : '☀️';
  localStorage.setItem('sc-theme', t);
  updateChartTheme();
}

// ════════════════════════════════════════════
//  LANGUAGE
// ════════════════════════════════════════════
function setLang(l){
  S.lang = l;
  const h = document.documentElement;
  h.setAttribute('data-lang', l);
  h.setAttribute('lang', l);
  h.setAttribute('dir', l==='ar' ? 'rtl' : 'ltr');
  $('langBtn').textContent = l==='ar' ? 'EN' : 'ع';
  document.querySelectorAll('.t[data-'+l+']')
    .forEach(e=>e.textContent=e.getAttribute('data-'+l));
  localStorage.setItem('sc-lang', l);
}

// ════════════════════════════════════════════
//  CLOCK — 12/24h toggle بضغطة على الوقت
// ════════════════════════════════════════════
function setupClock(){
  setInterval(()=>{
    $('timeTxt').textContent =
      new Date().toLocaleTimeString('en-US', {hour12: S.use12h});
  }, 1000);

  // ضغطة على الوقت تبدّل بين 12/24
  $('timeTxt').onclick = ()=>{
    S.use12h = !S.use12h;
    localStorage.setItem('sc-12h', S.use12h);
    toast(S.use12h ? '12h mode' : '24h mode');
  };
}

// ════════════════════════════════════════════
//  TPS counter
// ════════════════════════════════════════════
function setupTPS(){
  setInterval(()=>{
    $('stTPS').textContent = S.tpsCount;
    S.tpsCount = 0;
  }, 1000);
}

// ════════════════════════════════════════════
//  PAGE NAVIGATION
// ════════════════════════════════════════════
function showPage(name){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));

  const page = $('page-'+name);
  if(page) page.classList.add('active');

  document.querySelectorAll('.nav-btn[data-page="'+name+'"]')
    .forEach(b=>b.classList.add('active'));

  if(name === 'strategy') fetchSMC(S.smcSym);
  if(name === 'dashboard' && tvChart) tvChart.timeScale().scrollToRealTime();
}

function setupNav(){
  document.querySelectorAll('.nav-btn[data-page]').forEach(b=>{
    b.onclick = ()=> showPage(b.dataset.page);
  });
}

// ════════════════════════════════════════════
//  WATCHLIST — تبديل الأصل
// ════════════════════════════════════════════
function setupWatchlist(){
  document.querySelectorAll('.asset-card[data-sym]').forEach(card=>{
    card.onclick = ()=>{
      document.querySelectorAll('.asset-card').forEach(c=>c.classList.remove('active'));
      card.classList.add('active');

      S.sym = card.dataset.sym;
      $('ctSym').textContent  = S.sym.replace('USDT','/USDT');
      $('obSym').textContent  = S.sym.replace('USDT','/USDT');
      $('stSub').textContent  = S.sym.replace('USDT','/USDT');
      $('chartLoading').style.display = 'flex';

      connectBinance();
      loadCandles(S.sym, S.tf);
      log('Switched to '+S.sym);
    };
  });
}

// ════════════════════════════════════════════
//  TIMEFRAME BUTTONS
// ════════════════════════════════════════════
function setupTF(){
  document.querySelectorAll('.tf-btn').forEach(b=>{
    b.onclick = ()=>{
      document.querySelectorAll('.tf-btn').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      const tf = b.dataset.tf;
      if(tf){
        S.tf = tf;
        $('chartLoading').style.display = 'flex';
        connectBinance();
        loadCandles(S.sym, S.tf);
        log('Timeframe: '+tf);
      }
    };
  });
}

// ════════════════════════════════════════════
//  HEADER BUTTONS
// ════════════════════════════════════════════
function setupHeaderBtns(){
  $('themeBtn').onclick = ()=> setTheme(S.theme==='dark' ? 'light' : 'dark');
  $('langBtn').onclick  = ()=> setLang(S.lang==='ar' ? 'en' : 'ar');
}

// ════════════════════════════════════════════
//  INIT — نقطة البداية
// ════════════════════════════════════════════
function init(){
  // تطبيق الإعدادات المحفوظة
  setTheme(S.theme);
  setLang(S.lang);

  // إعداد العناصر
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

  // تهيئة الشارت
  initChart();

  // اتصالات
  connectBinance();
  connectBackend();

  // تحميل بيانات أولية
  loadCandles('BTCUSDT', '5m');
  drawOB(95000);

  log('Scylla v4.0 ready — MA20/50/100/200 | Volume | RSI');
}

// ── تشغيل بعد اكتمال الـ DOM ─────────────────
document.addEventListener('DOMContentLoaded', init);