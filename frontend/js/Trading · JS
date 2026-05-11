// ════════════════════════════════════════════
//  SCYLLA v4.0 — trading.js
//  نظام أوامر كامل:
//  Market/Limit/Stop Orders + Auto SL/TP
//  + Slippage Simulation + P&L Tracking
//
//  المسار: frontend/js/trading.js
//  يُضاف قبل app.js في dashboard.html
// ════════════════════════════════════════════
'use strict';

// ══════════════════════════════════════════
//  TRADING STATE
// ══════════════════════════════════════════
const T = {
  // رأس المال الوهمي
  capital:       10000,
  initialCapital: 10000,
  reserved:       0,      // محجوز في أوامر معلقة

  // الأوامر
  orders:    [],          // pending + active
  positions: [],          // مراكز مفتوحة
  history:   [],          // صفقات مغلقة

  // إعدادات Slippage
  slippage: {
    market: 0.05,   // 0.05% للأوامر السوقية
    limit:  0.00,   // لا slippage للأوامر المحددة
    stop:   0.08,   // 0.08% لأوامر الإيقاف
  },

  // إحصائيات P&L
  stats: {
    totalTrades:  0,
    wins:         0,
    losses:       0,
    totalPnL:     0,
    totalFees:    0,
    maxDrawdown:  0,
    peakCapital:  10000,
  },

  // تكاليف التداول
  feeRate:   0.001,   // 0.1% per side (Binance Taker)
  makerFee:  0.0008,  // 0.08% Maker

  // إعداد SL/TP تلقائي
  autoSL:  2.0,   // % افتراضي
  autoTP:  4.0,   // % افتراضي (RR 1:2)

  // منع التداول الزائد
  maxOpenPositions: 3,
  maxRiskPerTrade:  0.02,   // 2% من الرأس المال
};

// أنواع الأوامر
const ORDER_TYPES  = { MARKET:'MARKET', LIMIT:'LIMIT', STOP:'STOP', STOP_LIMIT:'STOP_LIMIT' };
const ORDER_SIDES  = { BUY:'BUY', SELL:'SELL' };
const ORDER_STATUS = {
  PENDING:   'PENDING',    // ينتظر السعر
  OPEN:      'OPEN',       // مفتوح (مركز نشط)
  CLOSED:    'CLOSED',     // مغلق (TP/SL/يدوي)
  CANCELLED: 'CANCELLED',  // ملغى
  REJECTED:  'REJECTED',   // مرفوض (رأس مال غير كافٍ)
};

// ══════════════════════════════════════════
//  ORDER ID GENERATOR
// ══════════════════════════════════════════
let _orderId = 1000;
function nextOrderId(){
  return `ORD-${Date.now()}-${++_orderId}`;
}

// ══════════════════════════════════════════
//  SLIPPAGE SIMULATOR
//  يحاكي السحب السعري في السوق الحقيقي
// ══════════════════════════════════════════
function applySlippage(price, side, orderType){
  const pct = T.slippage[orderType.toLowerCase()] || 0;
  if(pct === 0) return price;
  const noise  = (Math.random() * pct * 2 - pct) / 100;
  const impact = side === ORDER_SIDES.BUY ? pct/100 : -pct/100;
  return price * (1 + impact + noise);
}

// ══════════════════════════════════════════
//  FEE CALCULATOR
// ══════════════════════════════════════════
function calcFee(notional, isMaker=false){
  return notional * (isMaker ? T.makerFee : T.feeRate);
}

// ══════════════════════════════════════════
//  RISK VALIDATOR
//  يرفض الأمر إذا تجاوز الحد المسموح
// ══════════════════════════════════════════
function validateRisk(qty, price, slPct){
  const notional   = qty * price;
  const maxNotional = T.capital * 10;   // حد الـ leverage (x10 max)
  const riskAmt    = notional * (slPct / 100);
  const maxRisk    = T.capital * T.maxRiskPerTrade;

  if(notional > (T.capital + T.reserved)){
    return { ok:false, reason:'رأس المال غير كافٍ' };
  }
  if(T.positions.filter(p=>p.status===ORDER_STATUS.OPEN).length >= T.maxOpenPositions){
    return { ok:false, reason:`الحد الأقصى ${T.maxOpenPositions} مراكز مفتوحة` };
  }
  if(riskAmt > maxRisk){
    return {
      ok:false,
      reason:`الخطر ${riskAmt.toFixed(2)}$ يتجاوز الحد ${maxRisk.toFixed(2)}$ (${(T.maxRiskPerTrade*100).toFixed(0)}%)`
    };
  }
  return { ok:true };
}

// ══════════════════════════════════════════
//  PLACE ORDER — نقطة الدخول الرئيسية
// ══════════════════════════════════════════
function placeOrder({
  symbol   = S.sym,
  type     = ORDER_TYPES.MARKET,
  side     = ORDER_SIDES.BUY,
  qty      = 0,          // بالوحدات (BTC, ETH...)
  usdtQty  = 0,          // أو بالـ USDT
  price    = null,       // مطلوب لـ LIMIT/STOP_LIMIT
  stopPrice = null,      // مطلوب لـ STOP/STOP_LIMIT
  slPct    = T.autoSL,   // % Stop Loss
  tpPct    = T.autoTP,   // % Take Profit
  slPrice  = null,       // سعر SL مباشر (يُلغي slPct)
  tpPrice  = null,       // سعر TP مباشر (يُلغي tpPct)
  note     = '',
}){
  const currentPrice = S.prices[symbol] || 0;
  if(!currentPrice){
    tradingLog('❌ لا يوجد سعر حي. تأكد من الاتصال بـ Binance.', 'error');
    return null;
  }

  // حساب الكمية
  let finalQty = qty;
  if(!finalQty && usdtQty){
    const refPrice = (type === ORDER_TYPES.LIMIT && price) ? price : currentPrice;
    finalQty = usdtQty / refPrice;
  }
  if(finalQty <= 0){
    tradingLog('❌ الكمية يجب أن تكون أكبر من صفر', 'error');
    return null;
  }

  const refPrice = (type === ORDER_TYPES.LIMIT && price) ? price : currentPrice;

  // حساب SL/TP
  const sl = slPrice !== null
    ? slPrice
    : side === ORDER_SIDES.BUY
      ? refPrice * (1 - slPct/100)
      : refPrice * (1 + slPct/100);

  const tp = tpPrice !== null
    ? tpPrice
    : side === ORDER_SIDES.BUY
      ? refPrice * (1 + tpPct/100)
      : refPrice * (1 - tpPct/100);

  // التحقق من الخطر
  const validation = validateRisk(finalQty, refPrice, slPct);
  if(!validation.ok){
    tradingLog(`❌ رُفض الأمر: ${validation.reason}`, 'error');
    const order = buildOrderObject({
      symbol, type, side, qty:finalQty, price: refPrice,
      stopPrice, sl, tp, note,
      status: ORDER_STATUS.REJECTED,
      rejectReason: validation.reason,
    });
    T.history.unshift(order);
    refreshTradingUI();
    return order;
  }

  const order = buildOrderObject({
    symbol, type, side, qty:finalQty, price: refPrice,
    stopPrice, sl, tp, note,
    status: type === ORDER_TYPES.MARKET ? ORDER_STATUS.OPEN : ORDER_STATUS.PENDING,
  });

  // تنفيذ فوري للأوامر السوقية
  if(type === ORDER_TYPES.MARKET){
    executeOrder(order, currentPrice);
  } else {
    // أوامر معلقة — تُنفَّذ عند وصول السعر
    T.orders.push(order);
    T.reserved += order.notional;
    tradingLog(`📋 أمر معلق: ${type} ${side} ${finalQty.toFixed(6)} ${symbol} @ ${fmt(refPrice)}`, 'pending');
  }

  saveTrading();
  refreshTradingUI();
  return order;
}

// ══════════════════════════════════════════
//  BUILD ORDER OBJECT
// ══════════════════════════════════════════
function buildOrderObject({ symbol, type, side, qty, price, stopPrice, sl, tp, note, status, rejectReason='' }){
  const notional = qty * price;
  return {
    id:          nextOrderId(),
    symbol,
    type,
    side,
    qty:         parseFloat(qty.toFixed(8)),
    price:       parseFloat(price.toFixed(2)),
    stopPrice:   stopPrice ? parseFloat(stopPrice.toFixed(2)) : null,
    sl:          parseFloat(sl.toFixed(2)),
    tp:          parseFloat(tp.toFixed(2)),
    notional:    parseFloat(notional.toFixed(2)),
    status,
    rejectReason,
    note,
    createdAt:   Date.now(),
    filledAt:    null,
    closedAt:    null,
    fillPrice:   null,
    closePrice:  null,
    fee:         0,
    pnl:         0,
    pnlPct:      0,
    partialFills: [],
  };
}

// ══════════════════════════════════════════
//  EXECUTE ORDER (fill)
// ══════════════════════════════════════════
function executeOrder(order, marketPrice){
  const fillPrice   = applySlippage(marketPrice, order.side, order.type);
  const notional    = order.qty * fillPrice;
  const fee         = calcFee(notional, order.type === ORDER_TYPES.LIMIT);

  order.fillPrice   = parseFloat(fillPrice.toFixed(2));
  order.notional    = parseFloat(notional.toFixed(2));
  order.fee         = parseFloat(fee.toFixed(4));
  order.filledAt    = Date.now();
  order.status      = ORDER_STATUS.OPEN;

  // خصم من رأس المال
  const cost = notional + fee;
  if(cost > T.capital){
    order.status      = ORDER_STATUS.REJECTED;
    order.rejectReason = 'رأس المال غير كافٍ عند التنفيذ';
    T.history.unshift(order);
    tradingLog(`❌ رُفض عند التنفيذ: ${order.rejectReason}`, 'error');
    return;
  }

  T.capital   -= cost;
  T.stats.totalFees += fee;

  // إزالة من الأوامر المعلقة وإضافة للمراكز
  T.orders = T.orders.filter(o => o.id !== order.id);
  T.reserved = Math.max(0, T.reserved - order.notional);
  T.positions.push(order);

  // تسجيل الـ partial fill
  order.partialFills.push({ price:fillPrice, qty:order.qty, time:Date.now() });

  const slip = ((fillPrice - order.price) / order.price * 100).toFixed(3);
  tradingLog(
    `✅ نُفِّذ: ${order.type} ${order.side} ${order.qty.toFixed(6)} ${order.symbol}` +
    ` @ ${fmt(fillPrice)} | Slip: ${slip}% | Fee: $${fee.toFixed(4)}`,
    'success'
  );

  // إشعار toast + صوت
  if(typeof handleAlert === 'function'){
    handleAlert({
      alert_type: 'signal_entry',
      title: `${order.side === 'BUY' ? '🟢' : '🔴'} ${order.type} ${order.side}`,
      message: `${order.qty.toFixed(6)} ${order.symbol} @ $${fmt(fillPrice)}`,
      symbol: order.symbol,
      sound: 'entry',
    });
  }
}

// ══════════════════════════════════════════
//  CLOSE POSITION
// ══════════════════════════════════════════
function closePosition(positionId, reason='MANUAL', closeAtPrice=null){
  const pos = T.positions.find(p => p.id === positionId);
  if(!pos || pos.status !== ORDER_STATUS.OPEN) return;

  const closePrice = closeAtPrice || S.prices[pos.symbol] || pos.fillPrice;
  const exitFee    = calcFee(pos.qty * closePrice);

  // P&L
  const pnlRaw = pos.side === ORDER_SIDES.BUY
    ? (closePrice - pos.fillPrice) * pos.qty
    : (pos.fillPrice - closePrice) * pos.qty;
  const pnl    = pnlRaw - exitFee - pos.fee;
  const pnlPct = (pnl / pos.notional) * 100;

  pos.closePrice = parseFloat(closePrice.toFixed(2));
  pos.closedAt   = Date.now();
  pos.status     = ORDER_STATUS.CLOSED;
  pos.pnl        = parseFloat(pnl.toFixed(4));
  pos.pnlPct     = parseFloat(pnlPct.toFixed(3));
  pos.closeReason = reason;
  pos.fee        += exitFee;

  // إعادة المبلغ للرأس المال
  T.capital += pos.qty * closePrice - exitFee;

  // تحديث الإحصائيات
  T.stats.totalTrades++;
  T.stats.totalPnL += pnl;
  T.stats.totalFees += exitFee;
  if(pnl >= 0) T.stats.wins++; else T.stats.losses++;

  // Drawdown
  if(T.capital > T.stats.peakCapital) T.stats.peakCapital = T.capital;
  const dd = (T.stats.peakCapital - T.capital) / T.stats.peakCapital * 100;
  if(dd > T.stats.maxDrawdown) T.stats.maxDrawdown = dd;

  // نقل للتاريخ
  T.positions = T.positions.filter(p => p.id !== positionId);
  T.history.unshift(pos);
  if(T.history.length > 200) T.history.pop();

  const emoji = reason.includes('TP') ? '🎯' : reason.includes('SL') ? '🛑' : '🔒';
  tradingLog(
    `${emoji} مُغلق: ${pos.symbol} ${reason} | P&L: ${pnl>=0?'+':''}$${pnl.toFixed(2)} (${pnlPct>=0?'+':''}${pnlPct.toFixed(2)}%)`,
    pnl >= 0 ? 'success' : 'error'
  );

  if(typeof handleAlert === 'function'){
    handleAlert({
      alert_type: pnl >= 0 ? 'signal_exit' : 'signal_exit',
      title: `${emoji} ${reason}: ${pos.symbol}`,
      message: `P&L: ${pnl>=0?'+':''}$${pnl.toFixed(2)} (${pnlPct>=0?'+':''}${pnlPct.toFixed(2)}%)`,
      symbol: pos.symbol,
      sound: pnl >= 0 ? 'exit' : 'warning',
    });
  }

  saveTrading();
  refreshTradingUI();
}

// ══════════════════════════════════════════
//  CANCEL ORDER
// ══════════════════════════════════════════
function cancelOrder(orderId){
  const order = T.orders.find(o => o.id === orderId);
  if(!order) return;
  order.status   = ORDER_STATUS.CANCELLED;
  order.closedAt = Date.now();
  T.reserved     = Math.max(0, T.reserved - order.notional);
  T.orders = T.orders.filter(o => o.id !== orderId);
  T.history.unshift(order);
  tradingLog(`❌ ملغى: ${order.id}`, 'warning');
  saveTrading();
  refreshTradingUI();
}

// ══════════════════════════════════════════
//  PRICE MONITOR — يفحص SL/TP والأوامر المعلقة
//  يُستدعى من onTick() في market.js
// ══════════════════════════════════════════
function onPriceUpdate(symbol, price){
  // فحص المراكز المفتوحة
  T.positions.filter(p => p.symbol === symbol && p.status === ORDER_STATUS.OPEN)
    .forEach(pos => {
      // Take Profit
      if(pos.side === ORDER_SIDES.BUY  && price >= pos.tp) closePosition(pos.id, 'TP1', pos.tp);
      if(pos.side === ORDER_SIDES.SELL && price <= pos.tp) closePosition(pos.id, 'TP1', pos.tp);
      // Stop Loss
      if(pos.side === ORDER_SIDES.BUY  && price <= pos.sl) closePosition(pos.id, 'SL', pos.sl);
      if(pos.side === ORDER_SIDES.SELL && price >= pos.sl) closePosition(pos.id, 'SL', pos.sl);
    });

  // فحص الأوامر المعلقة
  T.orders.filter(o => o.symbol === symbol && o.status === ORDER_STATUS.PENDING)
    .forEach(order => {
      let shouldExecute = false;
      if(order.type === ORDER_TYPES.LIMIT){
        // BUY LIMIT: ينفذ عند انخفاض السعر للسعر المحدد
        if(order.side === ORDER_SIDES.BUY  && price <= order.price) shouldExecute = true;
        // SELL LIMIT: ينفذ عند ارتفاع السعر للسعر المحدد
        if(order.side === ORDER_SIDES.SELL && price >= order.price) shouldExecute = true;
      }
      if(order.type === ORDER_TYPES.STOP || order.type === ORDER_TYPES.STOP_LIMIT){
        const trigger = order.stopPrice || order.price;
        if(order.side === ORDER_SIDES.BUY  && price >= trigger) shouldExecute = true;
        if(order.side === ORDER_SIDES.SELL && price <= trigger) shouldExecute = true;
      }
      if(shouldExecute) executeOrder(order, price);
    });
}

// ══════════════════════════════════════════
//  UNREALIZED P&L (live)
// ══════════════════════════════════════════
function getUnrealizedPnL(){
  let total = 0;
  T.positions.filter(p => p.status === ORDER_STATUS.OPEN).forEach(pos => {
    const price = S.prices[pos.symbol] || pos.fillPrice;
    const raw   = pos.side === ORDER_SIDES.BUY
      ? (price - pos.fillPrice) * pos.qty
      : (pos.fillPrice - price) * pos.qty;
    total += raw;
  });
  return total;
}

function getPositionUnrealizedPnL(pos){
  const price = S.prices[pos.symbol] || pos.fillPrice;
  const raw   = pos.side === ORDER_SIDES.BUY
    ? (price - pos.fillPrice) * pos.qty
    : (pos.fillPrice - price) * pos.qty;
  const fee2 = calcFee(pos.qty * price);
  return raw - fee2;
}

// ══════════════════════════════════════════
//  QUICK SHORTCUTS
// ══════════════════════════════════════════
function quickBuy(usdtAmt){ placeOrder({ side:ORDER_SIDES.BUY,  type:ORDER_TYPES.MARKET, usdtQty:usdtAmt }); }
function quickSell(usdtAmt){ placeOrder({ side:ORDER_SIDES.SELL, type:ORDER_TYPES.MARKET, usdtQty:usdtAmt }); }
function closeAll(){
  [...T.positions].filter(p=>p.status===ORDER_STATUS.OPEN).forEach(p=>closePosition(p.id,'MANUAL'));
}
function cancelAll(){
  [...T.orders].forEach(o=>cancelOrder(o.id));
}

// ══════════════════════════════════════════
//  TRADING LOG (داخلي)
// ══════════════════════════════════════════
const _tradingLogs = [];
function tradingLog(msg, level='info'){
  const entry = { msg, level, time: Date.now() };
  _tradingLogs.unshift(entry);
  if(_tradingLogs.length > 100) _tradingLogs.pop();
  log(msg);   // يُرسل أيضاً للـ system log
  refreshTradingLog();
}

// ══════════════════════════════════════════
//  PERSISTENCE
// ══════════════════════════════════════════
function saveTrading(){
  try{
    localStorage.setItem('sc-trading', JSON.stringify({
      capital:   T.capital,
      reserved:  T.reserved,
      orders:    T.orders,
      positions: T.positions,
      history:   T.history.slice(0, 100),
      stats:     T.stats,
    }));
  }catch(e){}
}

function loadTrading(){
  try{
    const raw = localStorage.getItem('sc-trading');
    if(!raw) return;
    const d = JSON.parse(raw);
    if(d.capital   !== undefined) T.capital   = d.capital;
    if(d.reserved  !== undefined) T.reserved  = d.reserved;
    if(d.orders    !== undefined) T.orders    = d.orders;
    if(d.positions !== undefined) T.positions = d.positions;
    if(d.history   !== undefined) T.history   = d.history;
    if(d.stats     !== undefined) Object.assign(T.stats, d.stats);
  }catch(e){}
}

function resetTrading(){
  if(!confirm('هل تريد إعادة تعيين كامل نظام التداول الوهمي؟')) return;
  T.capital        = T.initialCapital;
  T.reserved       = 0;
  T.orders         = [];
  T.positions      = [];
  T.history        = [];
  T.stats.totalTrades  = 0;
  T.stats.wins         = 0;
  T.stats.losses       = 0;
  T.stats.totalPnL     = 0;
  T.stats.totalFees    = 0;
  T.stats.maxDrawdown  = 0;
  T.stats.peakCapital  = T.initialCapital;
  saveTrading();
  refreshTradingUI();
  tradingLog('🔄 تمت إعادة تعيين نظام التداول. رأس المال: $10,000', 'warning');
}

// ══════════════════════════════════════════
//  UI — بناء لوحة التداول الكاملة
// ══════════════════════════════════════════
function buildTradingPanel(){
  const container = $('tradingPanel');
  if(!container) return;

  container.innerHTML = `
    <div class="tp-header">
      <span class="tp-title">PAPER TRADING</span>
      <div class="tp-capital-row">
        <span class="tp-cap-lbl">EQUITY</span>
        <span class="tp-cap-val" id="tpEquity">$${T.capital.toFixed(2)}</span>
        <span class="tp-cap-pnl ${T.stats.totalPnL>=0?'g':'r'}" id="tpTotalPnL">
          ${T.stats.totalPnL>=0?'+':''}$${T.stats.totalPnL.toFixed(2)}
        </span>
      </div>
    </div>

    <!-- TABS -->
    <div class="tp-tabs">
      <button class="tp-tab active" data-tab="order" onclick="switchTradingTab('order')">ORDER</button>
      <button class="tp-tab" data-tab="positions" onclick="switchTradingTab('positions')">
        POS <span class="tp-badge" id="posBadge">${T.positions.filter(p=>p.status==='OPEN').length}</span>
      </button>
      <button class="tp-tab" data-tab="pending" onclick="switchTradingTab('pending')">
        PENDING <span class="tp-badge" id="pendBadge">${T.orders.length}</span>
      </button>
      <button class="tp-tab" data-tab="history" onclick="switchTradingTab('history')">HISTORY</button>
      <button class="tp-tab" data-tab="stats" onclick="switchTradingTab('stats')">STATS</button>
    </div>

    <!-- TAB CONTENT -->
    <div class="tp-body">

      <!-- ORDER ENTRY TAB -->
      <div class="tp-page active" id="tab-order">
        <div class="tp-side-row">
          <button class="tp-side-btn buy active" id="tpBuyBtn" onclick="setTradingSide('BUY')">BUY</button>
          <button class="tp-side-btn sell" id="tpSellBtn" onclick="setTradingSide('SELL')">SELL</button>
        </div>
        <div class="tp-type-row">
          <button class="tp-type-btn active" id="tpMarket" onclick="setOrderType('MARKET')">MARKET</button>
          <button class="tp-type-btn" id="tpLimit" onclick="setOrderType('LIMIT')">LIMIT</button>
          <button class="tp-type-btn" id="tpStop" onclick="setOrderType('STOP')">STOP</button>
          <button class="tp-type-btn" id="tpStopLimit" onclick="setOrderType('STOP_LIMIT')">S.LIMIT</button>
        </div>

        <!-- السعر المحدد (للـ LIMIT/STOP_LIMIT) -->
        <div class="tp-field-grp" id="tpLimitPriceRow" style="display:none">
          <label class="tp-field-lbl">LIMIT PRICE</label>
          <div class="tp-input-wrap">
            <input type="number" class="tp-field" id="tpLimitPrice" placeholder="0.00" step="0.01">
            <span class="tp-field-unit">USDT</span>
          </div>
        </div>

        <!-- سعر الإيقاف (للـ STOP/STOP_LIMIT) -->
        <div class="tp-field-grp" id="tpStopPriceRow" style="display:none">
          <label class="tp-field-lbl">STOP PRICE</label>
          <div class="tp-input-wrap">
            <input type="number" class="tp-field" id="tpStopPrice" placeholder="0.00" step="0.01">
            <span class="tp-field-unit">USDT</span>
          </div>
        </div>

        <!-- الكمية -->
        <div class="tp-field-grp">
          <label class="tp-field-lbl">AMOUNT (USDT)</label>
          <div class="tp-input-wrap">
            <input type="number" class="tp-field" id="tpAmount" placeholder="100" value="100" step="10"
                   oninput="updateOrderPreview()">
            <span class="tp-field-unit">USDT</span>
          </div>
        </div>

        <!-- أزرار % سريعة -->
        <div class="tp-pct-row">
          <button class="tp-pct-btn" onclick="setPctAmount(10)">10%</button>
          <button class="tp-pct-btn" onclick="setPctAmount(25)">25%</button>
          <button class="tp-pct-btn" onclick="setPctAmount(50)">50%</button>
          <button class="tp-pct-btn" onclick="setPctAmount(100)">MAX</button>
        </div>

        <!-- SL/TP -->
        <div class="tp-sltp-row">
          <div class="tp-field-grp">
            <label class="tp-field-lbl">STOP LOSS %</label>
            <div class="tp-input-wrap">
              <input type="number" class="tp-field" id="tpSLPct" value="${T.autoSL}" step="0.1" min="0.1" max="20"
                     oninput="updateOrderPreview()">
              <span class="tp-field-unit">%</span>
            </div>
          </div>
          <div class="tp-field-grp">
            <label class="tp-field-lbl">TAKE PROFIT %</label>
            <div class="tp-input-wrap">
              <input type="number" class="tp-field" id="tpTPPct" value="${T.autoTP}" step="0.1" min="0.1" max="100"
                     oninput="updateOrderPreview()">
              <span class="tp-field-unit">%</span>
            </div>
          </div>
        </div>

        <!-- معاينة الأمر -->
        <div class="tp-preview" id="orderPreview">
          <div class="tp-prev-row"><span>Entry Price</span><span id="prevEntry">--</span></div>
          <div class="tp-prev-row"><span>Stop Loss</span><span id="prevSL" style="color:var(--red)">--</span></div>
          <div class="tp-prev-row"><span>Take Profit</span><span id="prevTP" style="color:var(--green)">--</span></div>
          <div class="tp-prev-row"><span>Risk/Reward</span><span id="prevRR" style="color:var(--accent)">--</span></div>
          <div class="tp-prev-row"><span>Est. Fee</span><span id="prevFee" style="color:var(--text-dim)">--</span></div>
          <div class="tp-prev-row"><span>Max Loss</span><span id="prevMaxLoss" style="color:var(--red)">--</span></div>
        </div>

        <!-- زر التنفيذ -->
        <button class="tp-exec-btn buy" id="tpExecBtn" onclick="executeTradingOrder()">
          <span id="tpExecLabel">EXECUTE BUY MARKET</span>
        </button>

        <!-- أزرار طارئة -->
        <div class="tp-emergency-row">
          <button class="tp-emg-btn" onclick="closeAll()" title="إغلاق كل المراكز">🛑 CLOSE ALL</button>
          <button class="tp-emg-btn" onclick="cancelAll()" title="إلغاء كل الأوامر">❌ CANCEL ALL</button>
          <button class="tp-emg-btn danger" onclick="resetTrading()" title="إعادة تعيين">♻️ RESET</button>
        </div>
      </div>

      <!-- POSITIONS TAB -->
      <div class="tp-page" id="tab-positions">
        <div class="tp-pos-summary" id="posSummary"></div>
        <div class="tp-list" id="positionsList"></div>
      </div>

      <!-- PENDING TAB -->
      <div class="tp-page" id="tab-pending">
        <div class="tp-list" id="pendingList"></div>
      </div>

      <!-- HISTORY TAB -->
      <div class="tp-page" id="tab-history">
        <div class="tp-list" id="historyList"></div>
      </div>

      <!-- STATS TAB -->
      <div class="tp-page" id="tab-stats">
        <div class="tp-stats-grid" id="statsGrid"></div>
      </div>

    </div>
  `;

  // inject CSS
  injectTradingCSS();
  refreshTradingUI();
  updateOrderPreview();
}

// ══════════════════════════════════════════
//  UI STATE
// ══════════════════════════════════════════
let _activeSide    = ORDER_SIDES.BUY;
let _activeType    = ORDER_TYPES.MARKET;
let _activeTab     = 'order';

function setTradingSide(side){
  _activeSide = side;
  document.querySelectorAll('.tp-side-btn').forEach(b=>{
    b.classList.toggle('active', b.classList.contains(side.toLowerCase()));
  });
  const execBtn = $('tpExecBtn');
  if(execBtn){
    execBtn.className = `tp-exec-btn ${side.toLowerCase()}`;
  }
  updateOrderPreview();
}

function setOrderType(type){
  _activeType = type;
  document.querySelectorAll('.tp-type-btn').forEach(b=>b.classList.remove('active'));
  const btn = $(`tp${type.replace('_','')}`);
  if(btn) btn.classList.add('active');

  const limitRow = $('tpLimitPriceRow');
  const stopRow  = $('tpStopPriceRow');
  if(limitRow) limitRow.style.display = (type==='LIMIT'||type==='STOP_LIMIT') ? '' : 'none';
  if(stopRow)  stopRow.style.display  = (type==='STOP' ||type==='STOP_LIMIT') ? '' : 'none';
  updateOrderPreview();
}

function setPctAmount(pct){
  const avail = T.capital - T.reserved;
  const amt   = pct===100 ? avail : avail * (pct/100);
  const inp   = $('tpAmount');
  if(inp){ inp.value = Math.max(1, amt).toFixed(2); updateOrderPreview(); }
}

function switchTradingTab(tab){
  _activeTab = tab;
  document.querySelectorAll('.tp-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
  document.querySelectorAll('.tp-page').forEach(p=>p.classList.toggle('active',p.id===`tab-${tab}`));
  refreshTradingUI();
}

function updateOrderPreview(){
  const price   = S.prices[S.sym] || 0;
  const amount  = parseFloat($('tpAmount')?.value || 100);
  const slPct   = parseFloat($('tpSLPct')?.value  || T.autoSL);
  const tpPct   = parseFloat($('tpTPPct')?.value  || T.autoTP);

  if(!price) return;
  const qty     = amount / price;
  const slPrice = _activeSide==='BUY' ? price*(1-slPct/100) : price*(1+slPct/100);
  const tpPrice = _activeSide==='BUY' ? price*(1+tpPct/100) : price*(1-tpPct/100);
  const rr      = (tpPct/slPct).toFixed(2);
  const fee     = calcFee(amount);
  const maxLoss = amount * (slPct/100) + fee*2;

  const set = (id, val) => { const el=$(id); if(el) el.textContent=val; };
  set('prevEntry',  `$${fmt(price)}`);
  set('prevSL',     `$${fmt(slPrice)} (-${slPct.toFixed(1)}%)`);
  set('prevTP',     `$${fmt(tpPrice)} (+${tpPct.toFixed(1)}%)`);
  set('prevRR',     `1:${rr}`);
  set('prevFee',    `$${fee.toFixed(4)}`);
  set('prevMaxLoss',`$${maxLoss.toFixed(2)}`);

  const lb = $('tpExecLabel');
  if(lb) lb.textContent = `EXECUTE ${_activeSide} ${_activeType}`;
}

function executeTradingOrder(){
  const amount  = parseFloat($('tpAmount')?.value || 100);
  const slPct   = parseFloat($('tpSLPct')?.value  || T.autoSL);
  const tpPct   = parseFloat($('tpTPPct')?.value  || T.autoTP);
  const limP    = parseFloat($('tpLimitPrice')?.value || 0);
  const stopP   = parseFloat($('tpStopPrice')?.value  || 0);

  placeOrder({
    type:      _activeType,
    side:      _activeSide,
    usdtQty:   amount,
    price:     (limP > 0 && _activeType !== ORDER_TYPES.MARKET) ? limP : null,
    stopPrice: stopP > 0 ? stopP : null,
    slPct,
    tpPct,
  });
}

// ══════════════════════════════════════════
//  REFRESH UI
// ══════════════════════════════════════════
function refreshTradingUI(){
  // الرأس المال
  const unrealPnL = getUnrealizedPnL();
  const equity    = T.capital + unrealPnL;
  const el = (id) => $(id);

  const eqEl = el('tpEquity');
  if(eqEl) eqEl.textContent = `$${equity.toFixed(2)}`;
  const pnlEl = el('tpTotalPnL');
  if(pnlEl){
    const total = T.stats.totalPnL + unrealPnL;
    pnlEl.textContent = `${total>=0?'+':''}$${total.toFixed(2)}`;
    pnlEl.className   = `tp-cap-pnl ${total>=0?'g':'r'}`;
  }

  // الـ badges
  const pb = el('posBadge');
  const ppb = el('pendBadge');
  if(pb)  pb.textContent  = T.positions.filter(p=>p.status==='OPEN').length;
  if(ppb) ppb.textContent = T.orders.length;

  // حسب الـ tab النشط
  if(_activeTab === 'positions') renderPositions();
  if(_activeTab === 'pending')   renderPending();
  if(_activeTab === 'history')   renderHistory();
  if(_activeTab === 'stats')     renderStats();
  updateOrderPreview();
}

// ── Positions ──
function renderPositions(){
  const cont = $('positionsList');
  const summ = $('posSummary');
  if(!cont) return;

  const open = T.positions.filter(p=>p.status==='OPEN');
  if(!open.length){
    cont.innerHTML = '<div class="tp-empty">لا توجد مراكز مفتوحة</div>';
    if(summ) summ.innerHTML = '';
    return;
  }

  const totalPnL = open.reduce((a,p)=>a+getPositionUnrealizedPnL(p), 0);
  if(summ) summ.innerHTML = `
    <div class="tp-pos-sum-row">
      <span>Unrealized P&L</span>
      <span class="${totalPnL>=0?'g':'r'}">${totalPnL>=0?'+':''}$${totalPnL.toFixed(2)}</span>
    </div>`;

  cont.innerHTML = open.map(pos=>{
    const price   = S.prices[pos.symbol] || pos.fillPrice;
    const pnl     = getPositionUnrealizedPnL(pos);
    const pnlPct  = (pnl / pos.notional) * 100;
    const slDist  = Math.abs((pos.fillPrice - pos.sl)/pos.fillPrice*100).toFixed(2);
    const tpDist  = Math.abs((pos.tp - pos.fillPrice)/pos.fillPrice*100).toFixed(2);
    return `
    <div class="tp-pos-card ${pos.side.toLowerCase()}">
      <div class="tp-pos-top">
        <span class="tp-pos-sym">${pos.symbol}</span>
        <span class="tp-pos-side ${pos.side.toLowerCase()}">${pos.side}</span>
        <span class="tp-pos-pnl ${pnl>=0?'g':'r'}">${pnl>=0?'+':''}$${pnl.toFixed(2)} (${pnlPct>=0?'+':''}${pnlPct.toFixed(2)}%)</span>
      </div>
      <div class="tp-pos-details">
        <div class="tp-pos-det-row"><span>Entry</span><span>$${fmt(pos.fillPrice)}</span></div>
        <div class="tp-pos-det-row"><span>Current</span><span>$${fmt(price)}</span></div>
        <div class="tp-pos-det-row"><span>Qty</span><span>${pos.qty.toFixed(6)}</span></div>
        <div class="tp-pos-det-row"><span>SL</span><span style="color:var(--red)">$${fmt(pos.sl)} (-${slDist}%)</span></div>
        <div class="tp-pos-det-row"><span>TP</span><span style="color:var(--green)">$${fmt(pos.tp)} (+${tpDist}%)</span></div>
        <div class="tp-pos-det-row"><span>Fee</span><span>$${pos.fee.toFixed(4)}</span></div>
      </div>
      <div class="tp-pos-actions">
        <button class="tp-pos-btn close" onclick="closePosition('${pos.id}','MANUAL')">إغلاق</button>
        <button class="tp-pos-btn sl" onclick="closePosition('${pos.id}','SL',${pos.sl})">SL</button>
        <button class="tp-pos-btn tp" onclick="closePosition('${pos.id}','TP1',${pos.tp})">TP</button>
      </div>
    </div>`;
  }).join('');
}

// ── Pending Orders ──
function renderPending(){
  const cont = $('pendingList');
  if(!cont) return;
  if(!T.orders.length){
    cont.innerHTML = '<div class="tp-empty">لا توجد أوامر معلقة</div>';
    return;
  }
  cont.innerHTML = T.orders.map(o=>`
    <div class="tp-order-card ${o.side.toLowerCase()}">
      <div class="tp-order-top">
        <span class="tp-pos-sym">${o.symbol}</span>
        <span class="tp-order-type">${o.type}</span>
        <span class="tp-pos-side ${o.side.toLowerCase()}">${o.side}</span>
      </div>
      <div class="tp-pos-details">
        <div class="tp-pos-det-row"><span>Price</span><span>$${fmt(o.price)}</span></div>
        <div class="tp-pos-det-row"><span>Qty</span><span>${o.qty.toFixed(6)}</span></div>
        <div class="tp-pos-det-row"><span>Notional</span><span>$${o.notional.toFixed(2)}</span></div>
        <div class="tp-pos-det-row"><span>SL / TP</span>
          <span><span style="color:var(--red)">$${fmt(o.sl)}</span> / <span style="color:var(--green)">$${fmt(o.tp)}</span></span>
        </div>
        <div class="tp-pos-det-row"><span>Time</span><span>${new Date(o.createdAt).toLocaleTimeString()}</span></div>
      </div>
      <button class="tp-pos-btn close" onclick="cancelOrder('${o.id}')">إلغاء</button>
    </div>
  `).join('');
}

// ── History ──
function renderHistory(){
  const cont = $('historyList');
  if(!cont) return;
  const trades = T.history.filter(h => h.status === ORDER_STATUS.CLOSED).slice(0,50);
  if(!trades.length){
    cont.innerHTML = '<div class="tp-empty">لا يوجد تاريخ صفقات</div>';
    return;
  }
  cont.innerHTML = trades.map(h=>{
    const pnlCls = h.pnl>=0 ? 'g' : 'r';
    const emoji  = h.closeReason?.includes('TP')?'🎯':h.closeReason?.includes('SL')?'🛑':'🔒';
    return `
    <div class="tp-hist-row">
      <div style="display:flex;gap:6px;align-items:center">
        <span>${emoji}</span>
        <span class="tp-pos-sym" style="font-size:11px">${h.symbol}</span>
        <span class="tp-pos-side ${h.side.toLowerCase()}" style="font-size:10px">${h.side}</span>
        <span style="font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim)">${h.closeReason||''}</span>
      </div>
      <div style="text-align:right">
        <div class="tp-pos-pnl ${pnlCls}" style="font-size:12px">${h.pnl>=0?'+':''}$${h.pnl.toFixed(2)}</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim)">
          ${new Date(h.closedAt||h.filledAt||h.createdAt).toLocaleTimeString()}
        </div>
      </div>
    </div>`;
  }).join('');
}

// ── Stats ──
function renderStats(){
  const cont = $('statsGrid');
  if(!cont) return;
  const wr = T.stats.totalTrades > 0
    ? (T.stats.wins / T.stats.totalTrades * 100).toFixed(1)
    : '0.0';
  const roi = ((T.capital - T.initialCapital + T.stats.totalPnL) / T.initialCapital * 100).toFixed(2);
  const cells = [
    { lbl:'TOTAL TRADES', val:T.stats.totalTrades, cls:'' },
    { lbl:'WIN RATE',     val:`${wr}%`,             cls: parseFloat(wr)>=50?'g':'r' },
    { lbl:'TOTAL P&L',    val:`${T.stats.totalPnL>=0?'+':''}$${T.stats.totalPnL.toFixed(2)}`, cls:T.stats.totalPnL>=0?'g':'r' },
    { lbl:'ROI',          val:`${roi}%`,             cls: parseFloat(roi)>=0?'g':'r' },
    { lbl:'WINS',         val:T.stats.wins,           cls:'g' },
    { lbl:'LOSSES',       val:T.stats.losses,         cls:'r' },
    { lbl:'TOTAL FEES',   val:`$${T.stats.totalFees.toFixed(2)}`, cls:'r' },
    { lbl:'MAX DRAWDOWN', val:`${T.stats.maxDrawdown.toFixed(2)}%`, cls:'r' },
    { lbl:'CAPITAL',      val:`$${T.capital.toFixed(2)}`, cls:'a' },
    { lbl:'UNREALIZED',   val:`${getUnrealizedPnL()>=0?'+':''}$${getUnrealizedPnL().toFixed(2)}`, cls:getUnrealizedPnL()>=0?'g':'r' },
    { lbl:'RESERVED',     val:`$${T.reserved.toFixed(2)}`, cls:'' },
    { lbl:'FREE MARGIN',  val:`$${(T.capital-T.reserved).toFixed(2)}`, cls:'a' },
  ];
  cont.innerHTML = cells.map(c=>`
    <div class="tp-stat-cell">
      <div class="tp-stat-lbl">${c.lbl}</div>
      <div class="tp-stat-val ${c.cls}">${c.val}</div>
    </div>`).join('');
}

// ── Trading Log Refresh ──
function refreshTradingLog(){
  const cont = $('tradingLog');
  if(!cont) return;
  cont.innerHTML = _tradingLogs.slice(0, 20).map(e=>`
    <div class="tlog-row ${e.level}">
      <span class="tlog-time">${new Date(e.time).toLocaleTimeString()}</span>
      <span class="tlog-msg">${e.msg}</span>
    </div>`).join('');
}

// ══════════════════════════════════════════
//  CSS INJECTION
// ══════════════════════════════════════════
function injectTradingCSS(){
  if(document.getElementById('tradingCSS')) return;
  const style = document.createElement('style');
  style.id = 'tradingCSS';
  style.textContent = `
    /* ── Trading Panel Wrapper ── */
    .tp-header{padding:10px 12px;border-bottom:1px solid var(--border);background:var(--bg-card);}
    .tp-title{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--accent);letter-spacing:2px;display:block;margin-bottom:6px;}
    .tp-capital-row{display:flex;align-items:baseline;gap:8px;}
    .tp-cap-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);}
    .tp-cap-val{font-family:'Share Tech Mono',monospace;font-size:16px;color:var(--text-primary);font-weight:700;}
    .tp-cap-pnl{font-family:'Share Tech Mono',monospace;font-size:11px;}

    /* ── Tabs ── */
    .tp-tabs{display:flex;border-bottom:1px solid var(--border);background:var(--bg-card);overflow-x:auto;}
    .tp-tabs::-webkit-scrollbar{height:0;}
    .tp-tab{padding:6px 10px;border:none;background:transparent;color:var(--text-dim);
      font-family:'Share Tech Mono',monospace;font-size:10px;cursor:pointer;white-space:nowrap;
      border-bottom:2px solid transparent;transition:all .15s;}
    .tp-tab.active{color:var(--accent);border-bottom-color:var(--accent);}
    .tp-badge{background:var(--red);color:#fff;border-radius:8px;padding:0 5px;
      font-size:9px;margin-left:3px;display:inline-block;}

    /* ── Body ── */
    .tp-body{flex:1;overflow-y:auto;min-height:0;}
    .tp-body::-webkit-scrollbar{width:2px;}
    .tp-body::-webkit-scrollbar-thumb{background:var(--border-glow);}
    .tp-page{display:none;padding:10px;flex-direction:column;gap:7px;}
    .tp-page.active{display:flex;}

    /* ── Side / Type ── */
    .tp-side-row,.tp-type-row{display:grid;gap:4px;}
    .tp-side-row{grid-template-columns:1fr 1fr;}
    .tp-type-row{grid-template-columns:1fr 1fr 1fr 1fr;}
    .tp-side-btn,.tp-type-btn{padding:6px 4px;border:1px solid var(--border);
      background:transparent;font-family:'Share Tech Mono',monospace;font-size:10px;
      cursor:pointer;border-radius:3px;color:var(--text-dim);transition:all .15s;}
    .tp-side-btn.buy.active{border-color:var(--green);color:var(--green);background:rgba(0,240,122,.08);}
    .tp-side-btn.sell.active{border-color:var(--red);color:var(--red);background:rgba(255,45,85,.08);}
    .tp-type-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(0,180,255,.08);}

    /* ── Fields ── */
    .tp-field-grp{display:flex;flex-direction:column;gap:3px;}
    .tp-field-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);letter-spacing:1px;}
    .tp-input-wrap{display:flex;align-items:center;border:1px solid var(--border);border-radius:3px;overflow:hidden;}
    .tp-field{flex:1;background:var(--bg-card);color:var(--text-primary);border:none;
      font-family:'Share Tech Mono',monospace;font-size:12px;padding:5px 8px;outline:none;}
    .tp-field:focus{border-color:var(--accent);}
    .tp-field-unit{padding:4px 7px;background:var(--bg-card2);color:var(--text-dim);
      font-family:'Share Tech Mono',monospace;font-size:10px;border-left:1px solid var(--border);}

    /* ── % Buttons ── */
    .tp-pct-row{display:grid;grid-template-columns:repeat(4,1fr);gap:3px;}
    .tp-pct-btn{padding:4px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      cursor:pointer;border-radius:2px;transition:all .15s;}
    .tp-pct-btn:hover{border-color:var(--accent);color:var(--accent);}

    /* ── SL/TP row ── */
    .tp-sltp-row{display:grid;grid-template-columns:1fr 1fr;gap:6px;}

    /* ── Preview ── */
    .tp-preview{background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:8px;display:flex;flex-direction:column;gap:4px;}
    .tp-prev-row{display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:11px;}
    .tp-prev-row span:first-child{color:var(--text-dim);}
    .tp-prev-row span:last-child{color:var(--text-secondary);}

    /* ── Execute ── */
    .tp-exec-btn{padding:9px;border:none;border-radius:4px;font-family:'Share Tech Mono',monospace;
      font-size:12px;font-weight:700;cursor:pointer;letter-spacing:1px;transition:transform .15s;}
    .tp-exec-btn.buy{background:linear-gradient(135deg,#00c853,#00f07a);color:#000;}
    .tp-exec-btn.sell{background:linear-gradient(135deg,#cc0020,#ff2d55);color:#fff;}
    .tp-exec-btn:hover{transform:translateY(-1px);}

    /* ── Emergency ── */
    .tp-emergency-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:3px;}
    .tp-emg-btn{padding:5px 3px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:9px;color:var(--text-dim);
      cursor:pointer;border-radius:2px;transition:all .15s;}
    .tp-emg-btn:hover{border-color:var(--yellow);color:var(--yellow);}
    .tp-emg-btn.danger:hover{border-color:var(--red);color:var(--red);}

    /* ── Positions / Orders ── */
    .tp-empty{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--text-dim);
      text-align:center;padding:20px 0;}
    .tp-list{display:flex;flex-direction:column;gap:6px;}
    .tp-pos-card,.tp-order-card{background:var(--bg-card);border:1px solid var(--border);border-radius:4px;
      padding:8px;display:flex;flex-direction:column;gap:5px;}
    .tp-pos-card.buy{border-left:2px solid var(--green);}
    .tp-pos-card.sell{border-left:2px solid var(--red);}
    .tp-order-card.buy{border-left:2px solid rgba(0,240,122,.5);}
    .tp-order-card.sell{border-left:2px solid rgba(255,45,85,.5);}
    .tp-pos-top,.tp-order-top{display:flex;align-items:center;gap:6px;}
    .tp-pos-sym{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-primary);font-weight:700;}
    .tp-pos-side{font-family:'Share Tech Mono',monospace;font-size:10px;padding:1px 6px;border-radius:2px;}
    .tp-pos-side.buy{color:var(--green);background:rgba(0,240,122,.1);}
    .tp-pos-side.sell{color:var(--red);background:rgba(255,45,85,.1);}
    .tp-pos-pnl{font-family:'Share Tech Mono',monospace;font-size:12px;margin-left:auto;}
    .tp-order-type{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--accent);
      background:rgba(0,180,255,.08);border:1px solid rgba(0,180,255,.2);padding:1px 5px;border-radius:2px;}
    .tp-pos-details{display:flex;flex-direction:column;gap:2px;}
    .tp-pos-det-row{display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:10px;}
    .tp-pos-det-row span:first-child{color:var(--text-dim);}
    .tp-pos-det-row span:last-child{color:var(--text-secondary);}
    .tp-pos-actions{display:flex;gap:4px;margin-top:2px;}
    .tp-pos-btn{flex:1;padding:4px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;cursor:pointer;border-radius:2px;transition:all .15s;}
    .tp-pos-btn.close:hover{border-color:var(--yellow);color:var(--yellow);}
    .tp-pos-btn.sl:hover{border-color:var(--red);color:var(--red);}
    .tp-pos-btn.tp:hover{border-color:var(--green);color:var(--green);}
    .tp-pos-sum-row{display:flex;justify-content:space-between;
      font-family:'Share Tech Mono',monospace;font-size:12px;
      padding:6px 8px;background:var(--bg-card);border-radius:3px;margin-bottom:6px;
      border:1px solid var(--border);}

    /* ── History ── */
    .tp-hist-row{display:flex;justify-content:space-between;align-items:center;
      padding:6px 8px;background:var(--bg-card);border-radius:3px;
      border:1px solid var(--border);}

    /* ── Stats Grid ── */
    .tp-stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border);}
    .tp-stat-cell{background:var(--bg-panel);padding:10px;display:flex;flex-direction:column;gap:3px;}
    .tp-stat-lbl{font-family:'Share Tech Mono',monospace;font-size:9px;color:var(--text-dim);letter-spacing:1.5px;}
    .tp-stat-val{font-family:'Share Tech Mono',monospace;font-size:14px;color:var(--text-primary);}

    /* ── Trading Log ── */
    .tlog-row{display:flex;gap:8px;font-family:'Share Tech Mono',monospace;font-size:10px;
      padding:2px 0;border-bottom:1px solid var(--border);}
    .tlog-time{color:var(--text-dim);flex-shrink:0;}
    .tlog-msg{color:var(--text-secondary);}
    .tlog-row.success .tlog-msg{color:var(--green);}
    .tlog-row.error .tlog-msg{color:var(--red);}
    .tlog-row.warning .tlog-msg{color:var(--yellow);}
    .tlog-row.pending .tlog-msg{color:var(--accent);}

    /* ── g/r/a helpers ── */
    .g{color:var(--green)!important;} .r{color:var(--red)!important;} .a{color:var(--accent)!important;}
  `;
  document.head.appendChild(style);
}

// ══════════════════════════════════════════
//  INIT TRADING
// ══════════════════════════════════════════
function initTrading(){
  loadTrading();
  buildTradingPanel();

  // تحديث P&L كل ثانية
  setInterval(()=>{
    if(_activeTab === 'positions') renderPositions();
    refreshTradingUI();
  }, 1000);

  log('Trading system initialized — Market/Limit/Stop + Auto SL/TP + Slippage + P&L');
}

// ── تصدير onPriceUpdate لـ market.js ──
// في market.js → onTick() أضف:
// if(typeof onPriceUpdate==='function') onPriceUpdate(sym, price);