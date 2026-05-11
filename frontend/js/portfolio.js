// ════════════════════════════════════════════
//  SCYLLA v4.0 — portfolio.js
//  إدارة المحافظ الكاملة:
//  Multi-Portfolio + DCA Engine + P&L Tracking
//  + Allocation Chart + Performance Metrics
//
//  المسار: frontend/js/portfolio.js
//  يُضاف قبل app.js في dashboard.html
// ════════════════════════════════════════════
'use strict';

// ══════════════════════════════════════════
//  PORTFOLIO STATE
// ══════════════════════════════════════════
const PF = {
  // المحافظ المتعددة
  portfolios: [],
  activeId:   null,

  // DCA Plans
  dcaPlans: [],

  // إعدادات
  baseCurrency: 'USDT',
  refreshInterval: null,
};

// ══════════════════════════════════════════
//  DATA MODELS
// ══════════════════════════════════════════
function createPortfolio(name = 'محفظتي'){
  return {
    id:          `pf-${Date.now()}`,
    name,
    createdAt:   Date.now(),
    holdings:    [],     // [{sym, qty, avgCost, note}]
    transactions:[],     // سجل كامل
    tags:        [],
  };
}

function createHolding(sym, qty, avgCost, note=''){
  return {
    id:      `h-${Date.now()}-${Math.random().toString(36).slice(2,6)}`,
    sym,
    qty:     parseFloat(qty),
    avgCost: parseFloat(avgCost),
    note,
    addedAt: Date.now(),
  };
}

function createTransaction(type, sym, qty, price, fee=0, note=''){
  return {
    id:        `tx-${Date.now()}`,
    type,      // BUY | SELL | TRANSFER_IN | TRANSFER_OUT | DCA
    sym,
    qty:       parseFloat(qty),
    price:     parseFloat(price),
    fee:       parseFloat(fee),
    total:     parseFloat(qty) * parseFloat(price),
    note,
    timestamp: Date.now(),
  };
}

function createDCAPlan({ sym, amountUSDT, intervalHours, maxBuys, note='' }){
  return {
    id:           `dca-${Date.now()}`,
    sym,
    amountUSDT:   parseFloat(amountUSDT),
    intervalHours:parseFloat(intervalHours),
    maxBuys:      parseInt(maxBuys) || 0,   // 0 = لا نهاية
    note,
    active:       true,
    buysExecuted: 0,
    totalSpent:   0,
    totalQty:     0,
    lastBuyAt:    null,
    nextBuyAt:    Date.now() + intervalHours * 3600000,
    createdAt:    Date.now(),
    history:      [],
  };
}

// ══════════════════════════════════════════
//  PORTFOLIO CALCULATIONS
// ══════════════════════════════════════════
function calcHolding(h){
  const price    = S.prices[h.sym + 'USDT'] || S.prices[h.sym] || h.avgCost;
  const value    = h.qty * price;
  const cost     = h.qty * h.avgCost;
  const pnl      = value - cost;
  const pnlPct   = cost > 0 ? (pnl / cost) * 100 : 0;
  return { ...h, price, value, cost, pnl, pnlPct };
}

function calcPortfolioTotals(pf){
  const holdings = pf.holdings.map(calcHolding);
  const totalValue = holdings.reduce((a, h) => a + h.value, 0);
  const totalCost  = holdings.reduce((a, h) => a + h.cost,  0);
  const totalPnL   = totalValue - totalCost;
  const totalPnLPct = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

  // Allocation %
  const withAlloc = holdings.map(h => ({
    ...h,
    allocation: totalValue > 0 ? (h.value / totalValue) * 100 : 0,
  }));

  return { holdings: withAlloc, totalValue, totalCost, totalPnL, totalPnLPct };
}

function calcDCAAvgCost(plan){
  if(!plan.history.length) return 0;
  const totalCost = plan.history.reduce((a, b) => a + b.price * b.qty, 0);
  const totalQty  = plan.history.reduce((a, b) => a + b.qty, 0);
  return totalQty > 0 ? totalCost / totalQty : 0;
}

// ══════════════════════════════════════════
//  PORTFOLIO OPERATIONS
// ══════════════════════════════════════════
function addPortfolio(name){
  const pf = createPortfolio(name || `محفظة ${PF.portfolios.length + 1}`);
  PF.portfolios.push(pf);
  if(!PF.activeId) PF.activeId = pf.id;
  savePortfolio();
  renderPortfolioPage();
  return pf;
}

function deletePortfolio(id){
  if(PF.portfolios.length <= 1){ toast('يجب الإبقاء على محفظة واحدة على الأقل','var(--red)'); return; }
  if(!confirm('حذف المحفظة وكل بياناتها؟')) return;
  PF.portfolios = PF.portfolios.filter(p => p.id !== id);
  if(PF.activeId === id) PF.activeId = PF.portfolios[0]?.id || null;
  savePortfolio();
  renderPortfolioPage();
}

function getActivePortfolio(){
  return PF.portfolios.find(p => p.id === PF.activeId) || PF.portfolios[0];
}

// ── إضافة / تعديل holding ──
function addHolding({ sym, qty, avgCost, note='' }){
  const pf = getActivePortfolio();
  if(!pf) return;

  sym = sym.replace('USDT','').toUpperCase();
  const existing = pf.holdings.find(h => h.sym === sym);

  if(existing){
    // حساب متوسط التكلفة الجديد
    const totalQty  = existing.qty + parseFloat(qty);
    const totalCost = existing.qty * existing.avgCost + parseFloat(qty) * parseFloat(avgCost);
    existing.qty     = parseFloat(totalQty.toFixed(8));
    existing.avgCost = parseFloat((totalCost / totalQty).toFixed(4));
  } else {
    pf.holdings.push(createHolding(sym, qty, avgCost, note));
  }

  pf.transactions.push(createTransaction('BUY', sym, qty, avgCost, 0, note));
  savePortfolio();
  renderPortfolioPage();
  toast(`✅ أُضيف: ${qty} ${sym} @ $${fmt(avgCost)}`, 'var(--green)');
}

function removeHolding(holdingId){
  const pf = getActivePortfolio();
  if(!pf) return;
  const h = pf.holdings.find(x => x.id === holdingId);
  if(!h) return;
  if(!confirm(`حذف ${h.sym} من المحفظة؟`)) return;
  pf.holdings = pf.holdings.filter(x => x.id !== holdingId);
  pf.transactions.push(createTransaction('SELL', h.sym, h.qty, S.prices[h.sym+'USDT']||h.avgCost, 0, 'حذف يدوي'));
  savePortfolio();
  renderPortfolioPage();
}

function editHolding(holdingId){
  const pf = getActivePortfolio();
  const h  = pf?.holdings.find(x => x.id === holdingId);
  if(!h) return;
  const qty  = prompt(`كمية ${h.sym} الجديدة:`, h.qty);
  const cost = prompt(`متوسط تكلفة الشراء:`, h.avgCost);
  if(qty  !== null) h.qty     = parseFloat(qty)  || h.qty;
  if(cost !== null) h.avgCost = parseFloat(cost) || h.avgCost;
  savePortfolio();
  renderPortfolioPage();
}

// ══════════════════════════════════════════
//  DCA ENGINE
// ══════════════════════════════════════════
function addDCAPlan({ sym, amountUSDT, intervalHours, maxBuys, note }){
  const plan = createDCAPlan({ sym, amountUSDT, intervalHours, maxBuys, note });
  PF.dcaPlans.push(plan);
  savePortfolio();
  renderPortfolioPage();
  toast(`📅 خطة DCA: ${sym} $${amountUSDT} كل ${intervalHours}س`, 'var(--accent)');
  return plan;
}

function toggleDCAPlan(id){
  const plan = PF.dcaPlans.find(p => p.id === id);
  if(!plan) return;
  plan.active = !plan.active;
  if(plan.active) plan.nextBuyAt = Date.now() + plan.intervalHours * 3600000;
  savePortfolio();
  renderPortfolioPage();
}

function deleteDCAPlan(id){
  if(!confirm('حذف خطة DCA؟')) return;
  PF.dcaPlans = PF.dcaPlans.filter(p => p.id !== id);
  savePortfolio();
  renderPortfolioPage();
}

function executeDCABuy(plan){
  const price = S.prices[plan.sym + 'USDT'] || 0;
  if(!price){ log(`DCA: لا يوجد سعر لـ ${plan.sym}`); return; }

  const qty = plan.amountUSDT / price;
  const fee = qty * price * 0.001;

  plan.buysExecuted++;
  plan.totalSpent += plan.amountUSDT + fee;
  plan.totalQty   += qty;
  plan.lastBuyAt   = Date.now();
  plan.nextBuyAt   = Date.now() + plan.intervalHours * 3600000;
  plan.history.push({ price, qty, fee, timestamp: Date.now() });

  // أضف للمحفظة النشطة
  addHolding({ sym: plan.sym, qty, avgCost: price, note: `DCA #${plan.buysExecuted}` });

  // تحقق من الحد
  if(plan.maxBuys > 0 && plan.buysExecuted >= plan.maxBuys){
    plan.active = false;
    toast(`✅ اكتملت خطة DCA: ${plan.sym} (${plan.buysExecuted} عمليات)`, 'var(--green)');
  }

  if(typeof handleAlert === 'function'){
    handleAlert({
      alert_type: 'portfolio_alert',
      title: `📅 DCA: ${plan.sym}`,
      message: `شُرِي ${qty.toFixed(6)} ${plan.sym} @ $${fmt(price)}`,
      symbol: plan.sym + 'USDT',
      sound: 'portfolio',
    });
  }

  savePortfolio();
  log(`DCA: ${plan.sym} #${plan.buysExecuted} | ${qty.toFixed(6)} @ $${fmt(price)}`);
}

// فحص DCA كل دقيقة
function checkDCAPlans(){
  const now = Date.now();
  PF.dcaPlans
    .filter(p => p.active && p.nextBuyAt <= now)
    .forEach(plan => executeDCABuy(plan));
}

// ══════════════════════════════════════════
//  ALLOCATION CHART (Canvas)
// ══════════════════════════════════════════
const ALLOC_COLORS = ['#00d4ff','#00f07a','#f5a623','#e74c3c','#9b59b6','#1abc9c','#e67e22','#3498db'];

function drawAllocationChart(holdings, canvasId){
  const canvas = $(canvasId);
  if(!canvas || !holdings.length) return;

  const ctx = canvas.getContext('2d');
  const W   = canvas.width  = canvas.offsetWidth  || 180;
  const H   = canvas.height = canvas.offsetHeight || 180;
  const cx  = W / 2, cy = H / 2;
  const r   = Math.min(W, H) / 2 - 12;
  const ri  = r * 0.52;   // donut inner radius

  ctx.clearRect(0, 0, W, H);

  const total = holdings.reduce((a, h) => a + h.value, 0);
  if(!total) return;

  let startAngle = -Math.PI / 2;
  holdings.forEach((h, i) => {
    const slice = (h.value / total) * 2 * Math.PI;
    const color = ALLOC_COLORS[i % ALLOC_COLORS.length];

    // Slice
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, startAngle, startAngle + slice);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();

    // Inner hole
    ctx.beginPath();
    ctx.arc(cx, cy, ri, 0, 2 * Math.PI);
    ctx.fillStyle = getComputedStyle(document.documentElement)
      .getPropertyValue('--bg-panel').trim() || '#050c18';
    ctx.fill();

    startAngle += slice;
  });

  // Center text
  ctx.fillStyle = getComputedStyle(document.documentElement)
    .getPropertyValue('--text-secondary').trim() || '#8ab4d8';
  ctx.font = `bold 13px 'Share Tech Mono', monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(`$${total >= 1000 ? (total/1000).toFixed(1)+'K' : total.toFixed(0)}`, cx, cy - 8);
  ctx.font = `10px 'Share Tech Mono', monospace`;
  ctx.fillStyle = getComputedStyle(document.documentElement)
    .getPropertyValue('--text-dim').trim() || '#3a5878';
  ctx.fillText('TOTAL', cx, cy + 10);
}

// ══════════════════════════════════════════
//  RENDER — الصفحة الكاملة
// ══════════════════════════════════════════
function renderPortfolioPage(){
  const container = $('page-portfolio');
  if(!container) return;

  // إنشاء محفظة افتراضية إذا فارغة
  if(!PF.portfolios.length) addPortfolio('محفظتي الرئيسية');
  const pf     = getActivePortfolio();
  const totals = calcPortfolioTotals(pf);

  container.innerHTML = `
    <div class="pf-layout">

      <!-- SIDEBAR -->
      <div class="pf-sidebar">

        <!-- Portfolio Switcher -->
        <div class="pf-sb-section">
          <div class="pf-sb-title">المحافظ</div>
          <div class="pf-list" id="pfList">
            ${PF.portfolios.map(p => `
              <div class="pf-item ${p.id===PF.activeId?'active':''}" onclick="switchPortfolio('${p.id}')">
                <span class="pf-item-name">${p.name}</span>
                <span class="pf-item-count">${p.holdings.length}</span>
                ${PF.portfolios.length > 1
                  ? `<span class="pf-item-del" onclick="event.stopPropagation();deletePortfolio('${p.id}')">✕</span>`
                  : ''}
              </div>`).join('')}
          </div>
          <button class="pf-add-btn" onclick="promptAddPortfolio()">+ محفظة جديدة</button>
        </div>

        <!-- Summary -->
        <div class="pf-sb-section">
          <div class="pf-sb-title">ملخص</div>
          <div class="pf-summary-rows">
            <div class="pf-sum-row"><span>إجمالي القيمة</span><span class="a">$${totals.totalValue.toFixed(2)}</span></div>
            <div class="pf-sum-row"><span>إجمالي التكلفة</span><span>$${totals.totalCost.toFixed(2)}</span></div>
            <div class="pf-sum-row">
              <span>P&L</span>
              <span class="${totals.totalPnL>=0?'g':'r'}">
                ${totals.totalPnL>=0?'+':''}$${totals.totalPnL.toFixed(2)}
              </span>
            </div>
            <div class="pf-sum-row">
              <span>العائد</span>
              <span class="${totals.totalPnLPct>=0?'g':'r'}">
                ${totals.totalPnLPct>=0?'+':''}${totals.totalPnLPct.toFixed(2)}%
              </span>
            </div>
            <div class="pf-sum-row"><span>الأصول</span><span>${pf.holdings.length}</span></div>
            <div class="pf-sum-row"><span>الصفقات</span><span>${pf.transactions.length}</span></div>
          </div>
        </div>

        <!-- DCA Plans Count -->
        <div class="pf-sb-section">
          <div class="pf-sb-title">DCA النشطة</div>
          <div class="pf-sum-rows">
            ${PF.dcaPlans.filter(p=>p.active).map(p=>`
              <div class="pf-sum-row">
                <span>${p.sym}</span>
                <span class="a">$${p.amountUSDT}/كل ${p.intervalHours}س</span>
              </div>`).join('') || '<div style="font-family:\'Share Tech Mono\',monospace;font-size:10px;color:var(--text-dim);padding:4px 0">لا توجد خطط نشطة</div>'}
          </div>
        </div>

      </div>

      <!-- MAIN CONTENT -->
      <div class="pf-main">

        <!-- TABS -->
        <div class="pf-tabs">
          <button class="pf-tab active" data-pftab="holdings" onclick="switchPFTab('holdings')">الحيازات</button>
          <button class="pf-tab" data-pftab="allocation" onclick="switchPFTab('allocation')">التوزيع</button>
          <button class="pf-tab" data-pftab="dca" onclick="switchPFTab('dca')">DCA</button>
          <button class="pf-tab" data-pftab="transactions" onclick="switchPFTab('transactions')">السجل</button>
          <button class="pf-tab" data-pftab="performance" onclick="switchPFTab('performance')">الأداء</button>
        </div>

        <div class="pf-body">

          <!-- HOLDINGS TAB -->
          <div class="pf-page active" id="pftab-holdings">
            <!-- Add Holding Form -->
            <div class="pf-add-holding-form" id="pfAddForm" style="display:none">
              <div class="pf-form-title">➕ إضافة أصل</div>
              <div class="pf-form-row">
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">الرمز</label>
                  <select class="pf-field" id="pfSym">
                    <option value="BTC">BTC</option>
                    <option value="ETH">ETH</option>
                    <option value="BNB">BNB</option>
                    <option value="SOL">SOL</option>
                    <option value="ADA">ADA</option>
                    <option value="XRP">XRP</option>
                    <option value="DOGE">DOGE</option>
                    <option value="DOT">DOT</option>
                  </select>
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">الكمية</label>
                  <input type="number" class="pf-field" id="pfQty" placeholder="0.00" step="0.0001">
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">متوسط التكلفة $</label>
                  <input type="number" class="pf-field" id="pfCost" placeholder="0.00" step="0.01">
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">ملاحظة</label>
                  <input type="text" class="pf-field" id="pfNote" placeholder="اختياري">
                </div>
              </div>
              <div class="pf-form-actions">
                <button class="pf-form-btn confirm" onclick="submitAddHolding()">✅ إضافة</button>
                <button class="pf-form-btn cancel" onclick="$('pfAddForm').style.display='none'">إلغاء</button>
              </div>
            </div>

            <!-- Holdings List -->
            <div class="pf-holdings-header">
              <button class="pf-add-holding-btn" onclick="toggleAddHoldingForm()">➕ إضافة أصل</button>
              <div class="pf-sort-row">
                <span class="pf-sort-lbl">ترتيب:</span>
                <button class="pf-sort-btn active" onclick="sortHoldings('value')">القيمة</button>
                <button class="pf-sort-btn" onclick="sortHoldings('pnlPct')">العائد%</button>
                <button class="pf-sort-btn" onclick="sortHoldings('sym')">الرمز</button>
              </div>
            </div>

            ${!totals.holdings.length
              ? `<div class="pf-empty">📭 لا توجد أصول — أضف أول أصل بالزر أعلاه</div>`
              : `<div class="pf-holdings-grid">
                  ${buildHoldingsHeader()}
                  ${totals.holdings.map(h => buildHoldingRow(h)).join('')}
                 </div>`
            }
          </div>

          <!-- ALLOCATION TAB -->
          <div class="pf-page" id="pftab-allocation">
            <div class="pf-alloc-wrap">
              <div class="pf-alloc-chart-wrap">
                <canvas id="allocChart" style="width:200px;height:200px;"></canvas>
              </div>
              <div class="pf-alloc-legend">
                ${totals.holdings.map((h, i) => `
                  <div class="pf-legend-row">
                    <span class="pf-legend-dot" style="background:${ALLOC_COLORS[i%ALLOC_COLORS.length]}"></span>
                    <span class="pf-legend-sym">${h.sym}</span>
                    <div class="pf-legend-bar-wrap">
                      <div class="pf-legend-bar" style="width:${h.allocation.toFixed(1)}%;background:${ALLOC_COLORS[i%ALLOC_COLORS.length]}"></div>
                    </div>
                    <span class="pf-legend-pct">${h.allocation.toFixed(1)}%</span>
                    <span class="pf-legend-val">$${h.value.toFixed(2)}</span>
                  </div>`).join('')}
              </div>
            </div>
          </div>

          <!-- DCA TAB -->
          <div class="pf-page" id="pftab-dca">
            <!-- DCA Form -->
            <div class="pf-dca-form" id="dcaForm" style="display:none">
              <div class="pf-form-title">📅 خطة DCA جديدة</div>
              <div class="pf-form-row">
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">الرمز</label>
                  <select class="pf-field" id="dcaSym">
                    <option value="BTC">BTC</option>
                    <option value="ETH">ETH</option>
                    <option value="BNB">BNB</option>
                  </select>
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">المبلغ (USDT)</label>
                  <input type="number" class="pf-field" id="dcaAmt" placeholder="100" value="100">
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">كل (ساعة)</label>
                  <input type="number" class="pf-field" id="dcaInterval" placeholder="24" value="24">
                </div>
                <div class="pf-field-grp">
                  <label class="pf-field-lbl">حد الشراء (0=لا نهاية)</label>
                  <input type="number" class="pf-field" id="dcaMax" placeholder="0" value="0">
                </div>
              </div>
              <div class="pf-form-actions">
                <button class="pf-form-btn confirm" onclick="submitDCAPlan()">✅ إنشاء</button>
                <button class="pf-form-btn cancel" onclick="$('dcaForm').style.display='none'">إلغاء</button>
              </div>
            </div>

            <div class="pf-holdings-header">
              <button class="pf-add-holding-btn" onclick="$('dcaForm').style.display=$('dcaForm').style.display==='none'?'':'none'">
                📅 خطة جديدة
              </button>
            </div>

            ${!PF.dcaPlans.length
              ? `<div class="pf-empty">📭 لا توجد خطط DCA — أنشئ خطتك الأولى</div>`
              : PF.dcaPlans.map(plan => buildDCACard(plan)).join('')
            }
          </div>

          <!-- TRANSACTIONS TAB -->
          <div class="pf-page" id="pftab-transactions">
            ${!pf.transactions.length
              ? `<div class="pf-empty">📭 لا توجد معاملات</div>`
              : `<div class="pf-tx-list">
                  ${buildTxHeader()}
                  ${pf.transactions.slice().reverse().slice(0,100).map(tx => buildTxRow(tx)).join('')}
                 </div>`
            }
          </div>

          <!-- PERFORMANCE TAB -->
          <div class="pf-page" id="pftab-performance">
            ${buildPerformanceTab(pf, totals)}
          </div>

        </div>
      </div>
    </div>
  `;

  injectPortfolioCSS();

  // رسم الـ chart بعد الـ DOM
  setTimeout(() => drawAllocationChart(totals.holdings, 'allocChart'), 50);
}

// ══════════════════════════════════════════
//  HTML BUILDERS
// ══════════════════════════════════════════
function buildHoldingsHeader(){
  return `<div class="pf-h-header">
    <span>الرمز</span><span>الكمية</span><span>متوسط التكلفة</span>
    <span>السعر الحالي</span><span>القيمة</span><span>P&L</span>
    <span>العائد%</span><span>التوزيع</span><span>إجراء</span>
  </div>`;
}

function buildHoldingRow(h){
  const pnlCls = h.pnl >= 0 ? 'g' : 'r';
  return `
  <div class="pf-h-row">
    <span class="pf-h-sym">${h.sym}</span>
    <span>${h.qty.toFixed(h.qty >= 1 ? 4 : 6)}</span>
    <span>$${fmt(h.avgCost)}</span>
    <span class="a">$${fmt(h.price)}</span>
    <span>$${h.value.toFixed(2)}</span>
    <span class="${pnlCls}">${h.pnl>=0?'+':''}$${h.pnl.toFixed(2)}</span>
    <span class="${pnlCls}">${h.pnlPct>=0?'+':''}${h.pnlPct.toFixed(2)}%</span>
    <div class="pf-alloc-mini">
      <div class="pf-alloc-bar" style="width:${Math.min(100,h.allocation).toFixed(1)}%"></div>
      <span>${h.allocation.toFixed(1)}%</span>
    </div>
    <div class="pf-h-actions">
      <button class="pf-h-btn" onclick="editHolding('${h.id}')">✏️</button>
      <button class="pf-h-btn del" onclick="removeHolding('${h.id}')">🗑</button>
    </div>
  </div>`;
}

function buildDCACard(plan){
  const avgCost = calcDCAAvgCost(plan);
  const price   = S.prices[plan.sym + 'USDT'] || 0;
  const currentValue = plan.totalQty * price;
  const pnl     = currentValue - plan.totalSpent;
  const pnlPct  = plan.totalSpent > 0 ? (pnl / plan.totalSpent * 100) : 0;
  const nextIn  = plan.active && plan.nextBuyAt
    ? Math.max(0, Math.floor((plan.nextBuyAt - Date.now()) / 60000))
    : null;

  return `
  <div class="pf-dca-card ${plan.active?'active':'paused'}">
    <div class="pf-dca-top">
      <span class="pf-dca-sym">${plan.sym}</span>
      <span class="pf-dca-status ${plan.active?'on':'off'}">${plan.active?'🟢 نشط':'⏸ متوقف'}</span>
      <span class="pf-dca-int">كل ${plan.intervalHours}س</span>
      <span class="pf-dca-amt">$${plan.amountUSDT}/عملية</span>
    </div>
    <div class="pf-dca-stats">
      <div class="pf-dca-s"><span>عمليات</span><span>${plan.buysExecuted}${plan.maxBuys?'/'+plan.maxBuys:''}</span></div>
      <div class="pf-dca-s"><span>إجمالي الإنفاق</span><span>$${plan.totalSpent.toFixed(2)}</span></div>
      <div class="pf-dca-s"><span>إجمالي الكمية</span><span>${plan.totalQty.toFixed(6)}</span></div>
      <div class="pf-dca-s"><span>متوسط التكلفة</span><span>$${fmt(avgCost)}</span></div>
      <div class="pf-dca-s"><span>P&L</span>
        <span class="${pnl>=0?'g':'r'}">${pnl>=0?'+':''}$${pnl.toFixed(2)} (${pnlPct>=0?'+':''}${pnlPct.toFixed(1)}%)</span>
      </div>
      ${nextIn !== null ? `<div class="pf-dca-s"><span>الشراء القادم</span><span class="a">خلال ${nextIn}د</span></div>` : ''}
    </div>
    <div class="pf-dca-actions">
      <button class="pf-dca-btn" onclick="toggleDCAPlan('${plan.id}')">${plan.active?'⏸ إيقاف':'▶ تشغيل'}</button>
      <button class="pf-dca-btn" onclick="executeDCABuy(PF.dcaPlans.find(p=>p.id==='${plan.id}'))">⚡ شراء الآن</button>
      <button class="pf-dca-btn del" onclick="deleteDCAPlan('${plan.id}')">🗑 حذف</button>
    </div>
  </div>`;
}

function buildTxHeader(){
  return `<div class="pf-tx-header">
    <span>النوع</span><span>الرمز</span><span>الكمية</span>
    <span>السعر</span><span>الإجمالي</span><span>الرسوم</span><span>الوقت</span>
  </div>`;
}

function buildTxRow(tx){
  const typeColors = { BUY:'var(--green)', SELL:'var(--red)', DCA:'var(--accent)',
    TRANSFER_IN:'var(--green)', TRANSFER_OUT:'var(--red)' };
  return `
  <div class="pf-tx-row">
    <span style="color:${typeColors[tx.type]||'var(--text-secondary)'}">${tx.type}</span>
    <span class="pf-h-sym">${tx.sym}</span>
    <span>${parseFloat(tx.qty).toFixed(6)}</span>
    <span>$${fmt(tx.price)}</span>
    <span>$${tx.total.toFixed(2)}</span>
    <span style="color:var(--text-dim)">$${tx.fee.toFixed(4)}</span>
    <span style="color:var(--text-dim);font-size:10px">${new Date(tx.timestamp).toLocaleDateString()}</span>
  </div>`;
}

function buildPerformanceTab(pf, totals){
  const txs     = pf.transactions;
  const buys    = txs.filter(t=>t.type==='BUY'||t.type==='DCA');
  const sells   = txs.filter(t=>t.type==='SELL');
  const bestH   = [...totals.holdings].sort((a,b)=>b.pnlPct-a.pnlPct)[0];
  const worstH  = [...totals.holdings].sort((a,b)=>a.pnlPct-b.pnlPct)[0];

  return `
  <div class="pf-perf-grid">
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">إجمالي الاستثمار</div>
      <div class="pf-perf-val">$${totals.totalCost.toFixed(2)}</div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">القيمة الحالية</div>
      <div class="pf-perf-val a">$${totals.totalValue.toFixed(2)}</div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">الربح / الخسارة</div>
      <div class="pf-perf-val ${totals.totalPnL>=0?'g':'r'}">
        ${totals.totalPnL>=0?'+':''}$${totals.totalPnL.toFixed(2)}
      </div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">العائد الكلي</div>
      <div class="pf-perf-val ${totals.totalPnLPct>=0?'g':'r'}">
        ${totals.totalPnLPct>=0?'+':''}${totals.totalPnLPct.toFixed(2)}%
      </div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">عمليات الشراء</div>
      <div class="pf-perf-val">${buys.length}</div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">عمليات البيع</div>
      <div class="pf-perf-val">${sells.length}</div>
    </div>
    ${bestH ? `
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">أفضل أصل</div>
      <div class="pf-perf-val g">${bestH.sym} (+${bestH.pnlPct.toFixed(1)}%)</div>
    </div>` : ''}
    ${worstH ? `
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">أسوأ أصل</div>
      <div class="pf-perf-val r">${worstH.sym} (${worstH.pnlPct.toFixed(1)}%)</div>
    </div>` : ''}
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">خطط DCA نشطة</div>
      <div class="pf-perf-val a">${PF.dcaPlans.filter(p=>p.active).length}</div>
    </div>
    <div class="pf-perf-card">
      <div class="pf-perf-lbl">إجمالي إنفاق DCA</div>
      <div class="pf-perf-val">$${PF.dcaPlans.reduce((a,p)=>a+p.totalSpent,0).toFixed(2)}</div>
    </div>
  </div>`;
}

// ══════════════════════════════════════════
//  UI CONTROLS
// ══════════════════════════════════════════
let _activePFTab = 'holdings';
let _holdingsSort = 'value';

function switchPortfolio(id){
  PF.activeId = id;
  renderPortfolioPage();
}

function switchPFTab(tab){
  _activePFTab = tab;
  document.querySelectorAll('.pf-tab').forEach(b => b.classList.toggle('active', b.dataset.pftab === tab));
  document.querySelectorAll('.pf-page').forEach(p => p.classList.toggle('active', p.id === `pftab-${tab}`));
  if(tab === 'allocation') setTimeout(() => {
    const pf = getActivePortfolio();
    const totals = calcPortfolioTotals(pf);
    drawAllocationChart(totals.holdings, 'allocChart');
  }, 50);
}

function toggleAddHoldingForm(){
  const form = $('pfAddForm');
  if(form) form.style.display = form.style.display === 'none' ? '' : 'none';
}

function submitAddHolding(){
  const sym  = $('pfSym')?.value;
  const qty  = parseFloat($('pfQty')?.value  || 0);
  const cost = parseFloat($('pfCost')?.value || 0);
  const note = $('pfNote')?.value || '';
  if(!sym || qty <= 0 || cost <= 0){ toast('أدخل بيانات صحيحة','var(--red)'); return; }
  addHolding({ sym, qty, avgCost: cost, note });
  $('pfAddForm').style.display = 'none';
}

function submitDCAPlan(){
  const sym      = $('dcaSym')?.value;
  const amt      = parseFloat($('dcaAmt')?.value      || 100);
  const interval = parseFloat($('dcaInterval')?.value || 24);
  const maxB     = parseInt($('dcaMax')?.value        || 0);
  if(!sym || amt <= 0 || interval <= 0){ toast('أدخل بيانات صحيحة','var(--red)'); return; }
  addDCAPlan({ sym, amountUSDT:amt, intervalHours:interval, maxBuys:maxB });
  $('dcaForm').style.display = 'none';
}

function sortHoldings(by){
  _holdingsSort = by;
  document.querySelectorAll('.pf-sort-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll(`.pf-sort-btn`).forEach(b => {
    if(b.getAttribute('onclick')?.includes(by)) b.classList.add('active');
  });
  renderPortfolioPage();
}

function promptAddPortfolio(){
  const name = prompt('اسم المحفظة الجديدة:');
  if(name?.trim()) addPortfolio(name.trim());
}

// ══════════════════════════════════════════
//  PERSISTENCE
// ══════════════════════════════════════════
function savePortfolio(){
  try{
    localStorage.setItem('sc-portfolio', JSON.stringify({
      portfolios: PF.portfolios,
      activeId:   PF.activeId,
      dcaPlans:   PF.dcaPlans,
    }));
  }catch(e){}
}

function loadPortfolio(){
  try{
    const raw = localStorage.getItem('sc-portfolio');
    if(!raw) return;
    const d = JSON.parse(raw);
    if(d.portfolios) PF.portfolios = d.portfolios;
    if(d.activeId)   PF.activeId   = d.activeId;
    if(d.dcaPlans)   PF.dcaPlans   = d.dcaPlans;
  }catch(e){}
}

// ══════════════════════════════════════════
//  CSS INJECTION
// ══════════════════════════════════════════
function injectPortfolioCSS(){
  if(document.getElementById('portfolioCSS')) return;
  const style = document.createElement('style');
  style.id = 'portfolioCSS';
  style.textContent = `
    #page-portfolio{flex-direction:row;overflow:hidden;}
    .pf-layout{display:flex;width:100%;height:100%;overflow:hidden;}

    /* Sidebar */
    .pf-sidebar{width:210px;flex-shrink:0;background:var(--bg-panel);
      border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;}
    .pf-sidebar::-webkit-scrollbar{width:2px;}
    .pf-sidebar::-webkit-scrollbar-thumb{background:var(--border-glow);}
    .pf-sb-section{padding:10px 12px;border-bottom:1px solid var(--border);}
    .pf-sb-title{font-family:'Share Tech Mono',monospace;font-size:10px;
      color:var(--accent);letter-spacing:2px;margin-bottom:8px;}

    /* Portfolio list */
    .pf-list{display:flex;flex-direction:column;gap:3px;margin-bottom:6px;}
    .pf-item{display:flex;align-items:center;gap:5px;padding:6px 8px;border-radius:4px;
      border:1px solid transparent;cursor:pointer;background:var(--bg-card);transition:all .15s;}
    .pf-item:hover{border-color:var(--border);}
    .pf-item.active{border-color:var(--accent);background:rgba(0,180,255,.07);}
    .pf-item-name{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--text-secondary);flex:1;}
    .pf-item-count{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      background:var(--bg-card2);padding:1px 5px;border-radius:8px;}
    .pf-item-del{color:var(--text-dim);cursor:pointer;font-size:11px;padding:0 2px;transition:color .15s;}
    .pf-item-del:hover{color:var(--red);}
    .pf-add-btn{width:100%;padding:5px;background:rgba(0,180,255,.06);border:1px solid var(--border-glow);
      color:var(--accent);font-family:'Share Tech Mono',monospace;font-size:10px;cursor:pointer;border-radius:3px;}

    /* Summary */
    .pf-summary-rows,.pf-sum-rows{display:flex;flex-direction:column;gap:4px;}
    .pf-sum-row{display:flex;justify-content:space-between;
      font-family:'Share Tech Mono',monospace;font-size:11px;}
    .pf-sum-row span:first-child{color:var(--text-dim);}

    /* Main */
    .pf-main{flex:1;display:flex;flex-direction:column;overflow:hidden;}
    .pf-tabs{display:flex;border-bottom:1px solid var(--border);background:var(--bg-card);}
    .pf-tab{padding:8px 14px;border:none;background:transparent;color:var(--text-dim);
      font-family:'Share Tech Mono',monospace;font-size:11px;cursor:pointer;
      border-bottom:2px solid transparent;transition:all .15s;}
    .pf-tab.active{color:var(--accent);border-bottom-color:var(--accent);}
    .pf-body{flex:1;overflow-y:auto;}
    .pf-body::-webkit-scrollbar{width:3px;}
    .pf-body::-webkit-scrollbar-thumb{background:var(--border-glow);}
    .pf-page{display:none;padding:12px;flex-direction:column;gap:10px;}
    .pf-page.active{display:flex;}

    /* Add Form */
    .pf-add-holding-form,.pf-dca-form{background:var(--bg-card);border:1px solid var(--border-glow);
      border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;}
    .pf-form-title{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--accent);letter-spacing:1px;}
    .pf-form-row{display:flex;gap:8px;flex-wrap:wrap;}
    .pf-field-grp{display:flex;flex-direction:column;gap:3px;min-width:120px;flex:1;}
    .pf-field-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);}
    .pf-field{background:var(--bg-card2);border:1px solid var(--border);color:var(--text-primary);
      font-family:'Share Tech Mono',monospace;font-size:12px;padding:5px 8px;border-radius:3px;outline:none;}
    .pf-field:focus{border-color:var(--accent);}
    .pf-form-actions{display:flex;gap:6px;}
    .pf-form-btn{padding:5px 14px;border:1px solid var(--border);font-family:'Share Tech Mono',monospace;
      font-size:10px;cursor:pointer;border-radius:3px;transition:all .15s;}
    .pf-form-btn.confirm{background:rgba(0,240,122,.1);border-color:var(--green);color:var(--green);}
    .pf-form-btn.cancel{background:transparent;color:var(--text-dim);}

    /* Holdings */
    .pf-holdings-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;}
    .pf-add-holding-btn{padding:6px 14px;background:rgba(0,180,255,.07);border:1px solid var(--border-glow);
      color:var(--accent);font-family:'Share Tech Mono',monospace;font-size:11px;cursor:pointer;border-radius:4px;}
    .pf-sort-row{display:flex;align-items:center;gap:4px;}
    .pf-sort-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);}
    .pf-sort-btn{padding:3px 8px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);cursor:pointer;
      border-radius:2px;transition:all .15s;}
    .pf-sort-btn.active{border-color:var(--accent);color:var(--accent);}
    .pf-empty{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-dim);
      text-align:center;padding:30px 0;}

    /* Holdings Grid */
    .pf-holdings-grid{display:flex;flex-direction:column;gap:1px;background:var(--border);border-radius:5px;overflow:hidden;}
    .pf-h-header,.pf-h-row{display:grid;
      grid-template-columns:60px 80px 110px 110px 90px 90px 80px 1fr 70px;
      gap:4px;align-items:center;padding:7px 10px;}
    .pf-h-header{background:var(--bg-card);font-family:'Share Tech Mono',monospace;
      font-size:10px;color:var(--text-dim);letter-spacing:1px;}
    .pf-h-row{background:var(--bg-panel);font-family:'Share Tech Mono',monospace;
      font-size:11px;color:var(--text-secondary);transition:background .1s;}
    .pf-h-row:hover{background:var(--bg-card);}
    .pf-h-sym{font-size:13px;color:var(--text-primary);font-weight:700;}
    .pf-h-actions{display:flex;gap:3px;}
    .pf-h-btn{background:transparent;border:1px solid var(--border);color:var(--text-dim);
      font-size:11px;cursor:pointer;border-radius:2px;padding:2px 5px;transition:all .15s;}
    .pf-h-btn:hover{border-color:var(--border-glow);color:var(--text-secondary);}
    .pf-h-btn.del:hover{border-color:var(--red);color:var(--red);}
    .pf-alloc-mini{display:flex;align-items:center;gap:5px;}
    .pf-alloc-bar-wrap{flex:1;height:4px;background:var(--bg-card2);border-radius:2px;overflow:hidden;}
    .pf-alloc-bar{height:4px;background:var(--accent);border-radius:2px;transition:width .3s;}

    /* Allocation */
    .pf-alloc-wrap{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap;}
    .pf-alloc-chart-wrap{flex-shrink:0;}
    .pf-alloc-legend{flex:1;display:flex;flex-direction:column;gap:7px;min-width:200px;}
    .pf-legend-row{display:flex;align-items:center;gap:8px;}
    .pf-legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
    .pf-legend-sym{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-primary);
      font-weight:700;width:40px;}
    .pf-legend-bar-wrap{flex:1;height:6px;background:var(--bg-card2);border-radius:3px;overflow:hidden;}
    .pf-legend-bar{height:100%;border-radius:3px;transition:width .4s;}
    .pf-legend-pct{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--text-secondary);width:40px;text-align:right;}
    .pf-legend-val{font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--accent);width:70px;text-align:right;}

    /* DCA */
    .pf-dca-card{background:var(--bg-card);border:1px solid var(--border);border-radius:6px;
      padding:12px;display:flex;flex-direction:column;gap:8px;}
    .pf-dca-card.active{border-left:3px solid var(--green);}
    .pf-dca-card.paused{border-left:3px solid var(--text-dim);opacity:.8;}
    .pf-dca-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
    .pf-dca-sym{font-family:'Share Tech Mono',monospace;font-size:15px;color:var(--text-primary);font-weight:700;}
    .pf-dca-status{font-family:'Share Tech Mono',monospace;font-size:11px;}
    .pf-dca-int,.pf-dca-amt{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--accent);
      background:rgba(0,180,255,.08);border:1px solid rgba(0,180,255,.2);padding:2px 7px;border-radius:3px;}
    .pf-dca-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;}
    .pf-dca-s{display:flex;flex-direction:column;gap:2px;background:var(--bg-card2);
      padding:6px 8px;border-radius:3px;}
    .pf-dca-s span:first-child{font-family:'Share Tech Mono',monospace;font-size:9px;color:var(--text-dim);}
    .pf-dca-s span:last-child{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-secondary);}
    .pf-dca-actions{display:flex;gap:6px;}
    .pf-dca-btn{padding:5px 12px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      cursor:pointer;border-radius:3px;transition:all .15s;}
    .pf-dca-btn:hover{border-color:var(--accent);color:var(--accent);}
    .pf-dca-btn.del:hover{border-color:var(--red);color:var(--red);}

    /* Transactions */
    .pf-tx-list{display:flex;flex-direction:column;gap:1px;background:var(--border);border-radius:4px;overflow:hidden;}
    .pf-tx-header,.pf-tx-row{display:grid;
      grid-template-columns:90px 60px 90px 90px 90px 80px 90px;
      gap:4px;padding:6px 10px;align-items:center;}
    .pf-tx-header{background:var(--bg-card);font-family:'Share Tech Mono',monospace;
      font-size:10px;color:var(--text-dim);}
    .pf-tx-row{background:var(--bg-panel);font-family:'Share Tech Mono',monospace;
      font-size:11px;color:var(--text-secondary);transition:background .1s;}
    .pf-tx-row:hover{background:var(--bg-card);}

    /* Performance */
    .pf-perf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;}
    .pf-perf-card{background:var(--bg-card);border:1px solid var(--border);border-radius:5px;padding:14px;}
    .pf-perf-lbl{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      letter-spacing:1px;margin-bottom:6px;}
    .pf-perf-val{font-family:'Share Tech Mono',monospace;font-size:18px;color:var(--text-primary);}

    .g{color:var(--green)!important;} .r{color:var(--red)!important;} .a{color:var(--accent)!important;}

    @media(max-width:900px){
      .pf-sidebar{width:100%;max-height:160px;flex-direction:row;flex-wrap:wrap;overflow-x:auto;}
      #page-portfolio{flex-direction:column;}
      .pf-h-header,.pf-h-row{grid-template-columns:50px 70px 90px 90px 80px 80px 70px 60px 60px;}
    }
  `;
  document.head.appendChild(style);
}

// ══════════════════════════════════════════
//  INIT PORTFOLIO
// ══════════════════════════════════════════
function initPortfolio(){
  loadPortfolio();
  renderPortfolioPage();

  // DCA checker كل دقيقة
  PF.refreshInterval = setInterval(()=>{
    checkDCAPlans();
    // تحديث القيم اللحظية إذا الصفحة مفتوحة
    if($('page-portfolio')?.classList.contains('active')) renderPortfolioPage();
  }, 60000);

  log('Portfolio initialized — Multi-Portfolio + DCA + P&L + Allocation Chart');
}