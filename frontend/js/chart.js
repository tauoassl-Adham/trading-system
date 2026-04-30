// ════════════════════════════════════════════
//  SCYLLA v4.0 — chart.js
//  TradingView Lightweight Charts
//  + Volume + MA 20/50/100/200 + RSI
// ════════════════════════════════════════════

// ── Series references ────────────────────────
let tvChart     = null;
let candleSeries = null;
let volSeries   = null;
let rsiChart    = null;
let rsiSeries   = null;

// MA series map
let maSeries = {20:null, 50:null, 100:null, 200:null};

// ── MA config ────────────────────────────────
const MA_COLORS  = {20:'#00d4ff', 50:'#f5a623', 100:'#9b59b6', 200:'#e74c3c'};
const MA_PERIODS = [20, 50, 100, 200];

// ── TradingView ألوان من CSS variables ───────
function getTVColors(){
  const dark = S.theme === 'dark';
  return {
    bg:         dark ? '#050c18'              : '#ffffff',
    border:     dark ? '#162338'              : '#ccd8e8',
    text:       dark ? '#8ab4d8'              : '#3a5a7a',
    grid:       dark ? 'rgba(22,35,56,.8)'    : 'rgba(200,215,230,.5)',
    up:         dark ? '#00f07a'              : '#00904a',
    down:       dark ? '#ff2d55'              : '#cc001e',
    wick_up:    dark ? '#00f07a'              : '#00904a',
    wick_down:  dark ? '#ff2d55'              : '#cc001e',
    vol_up:     dark ? 'rgba(0,240,122,.35)'  : 'rgba(0,144,74,.3)',
    vol_down:   dark ? 'rgba(255,45,85,.35)'  : 'rgba(204,0,30,.3)',
    crosshair:  dark ? 'rgba(0,212,255,.6)'   : 'rgba(0,119,204,.5)',
    price_line: dark ? 'rgba(0,212,255,.8)'   : 'rgba(0,119,204,.8)',
  };
}

// ── إنشاء الشارت الرئيسي ─────────────────────
function initChart(){
  const container = $('tvChart');
  if(!container) return;

  const C = getTVColors();

  tvChart = LightweightCharts.createChart(container, {
    autoSize: true,
    layout:{
      background: {type:'solid', color:C.bg},
      textColor:  C.text,
      fontSize:   13,
      fontFamily: "'Share Tech Mono', monospace",
    },
    grid:{
      vertLines: {color:C.grid, style:1},
      horzLines: {color:C.grid, style:1},
    },
    crosshair:{
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {color:C.crosshair, width:1, style:2, labelBackgroundColor:'#00d4ff'},
      horzLine: {color:C.crosshair, width:1, style:2, labelBackgroundColor:'#00d4ff'},
    },
    rightPriceScale:{
      borderColor: C.border,
      textColor:   C.text,
      scaleMargins: {top:0.08, bottom:0.22},
    },
    timeScale:{
      borderColor:     C.border,
      textColor:       C.text,
      timeVisible:     true,
      secondsVisible:  false,
      barSpacing:      8,
    },
    handleScroll: {mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true},
    handleScale:  {mouseWheel:true, pinch:true, axisPressedMouseMove:true},
  });

  // Candlestick
  candleSeries = tvChart.addCandlestickSeries({
    upColor:        C.up,
    downColor:      C.down,
    borderUpColor:  C.up,
    borderDownColor:C.down,
    wickUpColor:    C.wick_up,
    wickDownColor:  C.wick_down,
    priceLineColor: C.price_line,
    priceLineWidth: 1,
    priceLineStyle: 2,
    lastValueVisible: true,
  });

  // Volume
  volSeries = tvChart.addHistogramSeries({
    priceFormat:  {type:'volume'},
    priceScaleId: 'volume',
    scaleMargins: {top:0.82, bottom:0},
  });
  tvChart.priceScale('volume').applyOptions({
    scaleMargins: {top:0.82, bottom:0},
  });

  // MA Lines (20/50/100/200)
  MA_PERIODS.forEach(p => {
    maSeries[p] = tvChart.addLineSeries({
      color:                 MA_COLORS[p],
      lineWidth:             1.5,
      priceLineVisible:      false,
      lastValueVisible:      true,
      crosshairMarkerVisible:false,
      title:                 `MA${p}`,
      visible:               S.maVisible[p],
    });
  });

  // RSI Chart (panel منفصل)
  initRSI();

  log('Chart initialized — MA20/50/100/200 + Volume + RSI');
}

// ── RSI Panel ────────────────────────────────
function initRSI(){
  const container = $('rsiChart');
  if(!container) return;
  const C = getTVColors();

  rsiChart = LightweightCharts.createChart(container, {
    autoSize: true,
    layout:{
      background: {type:'solid', color:C.bg},
      textColor:  C.text,
      fontSize:   11,
      fontFamily: "'Share Tech Mono', monospace",
    },
    grid:{
      vertLines: {color:C.grid},
      horzLines: {color:C.grid},
    },
    rightPriceScale:{
      borderColor: C.border,
      textColor:   C.text,
      scaleMargins:{top:0.1, bottom:0.1},
    },
    timeScale:{
      borderColor: C.border,
      visible:     false,   // نخفي محور الوقت في RSI
    },
    crosshair:{mode: LightweightCharts.CrosshairMode.Normal},
    handleScroll: {mouseWheel:true, pressedMouseMove:true},
    handleScale:  {mouseWheel:true, pinch:true},
  });

  // خط RSI
  rsiSeries = rsiChart.addLineSeries({
    color:            '#e74c3c',
    lineWidth:        1.5,
    priceLineVisible: false,
    lastValueVisible: true,
  });

  // خطا 70 و 30
  const ob70 = rsiChart.addLineSeries({color:'rgba(255,45,85,.3)', lineWidth:1, priceLineVisible:false, lastValueVisible:false});
  const ob30 = rsiChart.addLineSeries({color:'rgba(0,240,122,.3)', lineWidth:1, priceLineVisible:false, lastValueVisible:false});

  // نضع placeholder data لخطوط 70/30 — ستُحدَّث عند تحميل البيانات
  window._rsi70 = ob70;
  window._rsi30 = ob30;
}

// ── حساب RSI ─────────────────────────────────
function calcRSI(candles, period=14){
  if(candles.length < period+1) return [];
  const result = [];
  let gains=0, losses=0;

  for(let i=1; i<=period; i++){
    const d = candles[i].close - candles[i-1].close;
    if(d>0) gains+=d; else losses-=d;
  }
  let avgG = gains/period, avgL = losses/period;

  for(let i=period; i<candles.length; i++){
    if(i > period){
      const d = candles[i].close - candles[i-1].close;
      avgG = (avgG*(period-1) + (d>0?d:0)) / period;
      avgL = (avgL*(period-1) + (d<0?-d:0)) / period;
    }
    const rsi = avgL===0 ? 100 : 100-(100/(1+avgG/avgL));
    result.push({time:candles[i].time, value:parseFloat(rsi.toFixed(2))});
  }
  return result;
}

// ── حساب وضبط Moving Averages ────────────────
function calcAndSetMA(candles){
  MA_PERIODS.forEach(period => {
    if(!maSeries[period]) return;
    if(!S.maVisible[period]){
      maSeries[period].setData([]);
      return;
    }
    const data = [];
    for(let i=period-1; i<candles.length; i++){
      let sum = 0;
      for(let j=i-period+1; j<=i; j++) sum += candles[j].close;
      data.push({time:candles[i].time, value:sum/period});
    }
    maSeries[period].setData(data);
  });
}

// ── تحميل البيانات التاريخية ──────────────────
function setChartData(rawCandles){
  if(!candleSeries || !volSeries) return;

  const candles = rawCandles.map(c=>({
    time:  c.t,
    open:  c.o,
    high:  c.h,
    low:   c.l,
    close: c.c,
  }));
  const volumes = rawCandles.map(c=>({
    time:  c.t,
    value: c.v||0,
    color: c.c>=c.o ? getTVColors().vol_up : getTVColors().vol_down,
  }));

  candleSeries.setData(candles);
  volSeries.setData(volumes);
  calcAndSetMA(candles);

  // RSI
  if(rsiSeries){
    const rsiData = calcRSI(candles);
    if(rsiData.length){
      rsiSeries.setData(rsiData);
      const last = rsiData[rsiData.length-1];
      if(last){
        const el = $('rsiLabel');
        if(el) el.textContent = `RSI(14): ${last.value.toFixed(1)}`;
      }
      // خطوط 70/30
      if(window._rsi70 && window._rsi30){
        const l70 = rsiData.map(d=>({time:d.time, value:70}));
        const l30 = rsiData.map(d=>({time:d.time, value:30}));
        window._rsi70.setData(l70);
        window._rsi30.setData(l30);
      }
      // مزامنة timeScale مع الشارت الرئيسي
      if(rsiChart && tvChart){
        tvChart.timeScale().subscribeVisibleLogicalRangeChange(range=>{
          if(range) rsiChart.timeScale().setVisibleLogicalRange(range);
        });
      }
    }
  }

  $('chartLoading').style.display = 'none';
  tvChart.timeScale().scrollToRealTime();
  log(`Chart: ${candles.length} candles | MA20/50/100/200 | RSI`);
}

// ── تحديث الشمعة الحية (kline) ───────────────
// ← نقطة ربط WebSocket
function updateLiveCandle(k){
  if(!candleSeries) return;

  const candle = {
    time:  Math.floor(k.t/1000),
    open:  +k.o,
    high:  +k.h,
    low:   +k.l,
    close: +k.c,
  };
  const vol = {
    time:  Math.floor(k.t/1000),
    value: +k.v||0,
    color: +k.c>=+k.o ? getTVColors().vol_up : getTVColors().vol_down,
  };

  candleSeries.update(candle);
  volSeries.update(vol);
}

// ── تحديث ألوان الشارت عند تغيير الثيم ───────
function updateChartTheme(){
  if(!tvChart) return;
  const C = getTVColors();

  tvChart.applyOptions({
    layout:    {background:{type:'solid',color:C.bg}, textColor:C.text},
    grid:      {vertLines:{color:C.grid}, horzLines:{color:C.grid}},
    crosshair: {
      vertLine:{color:C.crosshair, labelBackgroundColor:'#00d4ff'},
      horzLine:{color:C.crosshair, labelBackgroundColor:'#00d4ff'},
    },
    rightPriceScale: {borderColor:C.border, textColor:C.text},
    timeScale:       {borderColor:C.border, textColor:C.text},
  });

  if(candleSeries){
    candleSeries.applyOptions({
      upColor:        C.up,
      downColor:      C.down,
      borderUpColor:  C.up,
      borderDownColor:C.down,
      wickUpColor:    C.wick_up,
      wickDownColor:  C.wick_down,
    });
  }

  if(rsiChart){
    rsiChart.applyOptions({
      layout: {background:{type:'solid',color:C.bg}, textColor:C.text},
      grid:   {vertLines:{color:C.grid}, horzLines:{color:C.grid}},
    });
  }
}

// ── Zoom buttons ──────────────────────────────
function setupZoom(){
  $('zIn').onclick  = ()=>{
    if(tvChart){
      const ts = tvChart.timeScale();
      ts.applyOptions({barSpacing: Math.min(50, ts.options().barSpacing*1.3)});
    }
  };
  $('zOut').onclick = ()=>{
    if(tvChart){
      const ts = tvChart.timeScale();
      ts.applyOptions({barSpacing: Math.max(2, ts.options().barSpacing*0.7)});
    }
  };
  $('zRst').onclick = ()=>{
    if(tvChart){
      tvChart.timeScale().applyOptions({barSpacing:8});
      tvChart.timeScale().scrollToRealTime();
    }
  };
}

// ── MA Toggle ─────────────────────────────────
function setupMAToggle(){
  document.querySelectorAll('.ma-item[data-ma]').forEach(item=>{
    item.onclick = ()=>{
      const p = +item.dataset.ma;
      S.maVisible[p] = !S.maVisible[p];
      item.classList.toggle('off', !S.maVisible[p]);
      if(maSeries[p]) maSeries[p].setData([]);
      // أعد الحساب من الباكند
      refetchMA();
    };
  });
}

async function refetchMA(){
  try{
    const r = await fetch(`${API}/api/candles/${S.sym}/${S.tf}?limit=500`);
    if(r.ok){
      const d = await r.json();
      const candles = (d.candles||[]).map(c=>({time:c.t, open:c.o, high:c.h, low:c.l, close:c.c}));
      calcAndSetMA(candles);
    }
  }catch(e){}
}