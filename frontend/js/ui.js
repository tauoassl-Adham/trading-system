// ════════════════════════════════════════════
//  SCYLLA v4.0 — ui.js
//  Order Book + Live Feed + Trade Panel
// ════════════════════════════════════════════

// ════════════════════════════════════════════
//  ORDER BOOK (simulated)
// ════════════════════════════════════════════
function drawOB(price){
  if(!price) return;
  const asks=[], bids=[];

  for(let i=0; i<8; i++){
    const ap = price*(1+(0.0001+Math.random()*0.0004)*(i+1));
    const bp = price*(1-(0.0001+Math.random()*0.0004)*(i+1));
    const as = (Math.random()*2+.1).toFixed(3);
    const bs = (Math.random()*2+.1).toFixed(3);
    asks.push({p:ap, s:+as, t:+(ap*as).toFixed(0)});
    bids.push({p:bp, s:+bs, t:+(bp*bs).toFixed(0)});
  }
  asks.sort((a,b)=>a.p-b.p);

  const maxT = Math.max(...asks.map(a=>a.t), ...bids.map(b=>b.t));
  const row  = (r,cls,pc) =>
    `<div class="ob-row ${cls}">` +
    `<div class="ob-fill" style="width:${(r.t/maxT*100).toFixed(0)}%"></div>` +
    `<span class="${pc}">${r.p.toFixed(1)}</span>` +
    `<span class="ob-size">${r.s}</span>` +
    `<span class="ob-total">${r.t.toLocaleString()}</span></div>`;

  $('askRows').innerHTML  = asks.slice().reverse().map(a=>row(a,'ob-ask','ob-price-ask')).join('');
  $('obSpread').textContent = 'SPREAD: '+(asks[0].p-bids[0].p).toFixed(2);
  $('bidRows').innerHTML  = bids.map(b=>row(b,'ob-bid','ob-price-bid')).join('');
}

// ════════════════════════════════════════════
//  LIVE FEED
// ════════════════════════════════════════════
function addFeed(sym, price, isBuy){
  const feed = $('feedBody');
  const d    = document.createElement('div');
  d.className = 'feed-item '+(isBuy?'buy':'sell');
  d.innerHTML =
    `<span class="fsym">${sym.replace('USDT','/U')}</span>` +
    `<span class="${isBuy?'fp-buy':'fp-sell'}">${fmt(price)}</span>` +
    `<span class="ft">${new Date().toLocaleTimeString('en-US',{hour12:S.use12h})}</span>`;

  feed.insertBefore(d, feed.firstChild);
  while(feed.children.length > 50) feed.removeChild(feed.lastChild);

  S.feedCount++;
  $('feedCnt').textContent = S.feedCount+' TICKS';
}

// ════════════════════════════════════════════
//  TRADE PANEL EVENTS
// ════════════════════════════════════════════
function setupTradePanel(){

  // BUY tab
  $('buyTab').onclick = ()=>{
    S.mode = 'buy';
    $('buyTab').classList.add('active');
    $('sellTab').classList.remove('active');
    $('execBtn').className = 'exec-btn buy';
    const s = $('execBtn').querySelector('.t');
    if(s) s.textContent = S.lang==='ar' ? 'تنفيذ شراء' : 'Execute BUY';
  };

  // SELL tab
  $('sellTab').onclick = ()=>{
    S.mode = 'sell';
    $('sellTab').classList.add('active');
    $('buyTab').classList.remove('active');
    $('execBtn').className = 'exec-btn sell';
    const s = $('execBtn').querySelector('.t');
    if(s) s.textContent = S.lang==='ar' ? 'تنفيذ بيع' : 'Execute SELL';
  };

  // Execute button
  $('execBtn').onclick = ()=>{
    const qty   = +$('tradeQty').value || 0;
    const price = S.prices[S.sym];
    if(!qty || !price)
      return toast(S.lang==='ar'?'أدخل الكمية':'Enter quantity', 'var(--red)');

    const side = S.mode.toUpperCase();
    if(beWS && beWS.readyState === WebSocket.OPEN)
      beWS.send(JSON.stringify({action:'paper_trade', symbol:S.sym, side, qty, price}));

    toast(
      `Paper ${side}: ${qty} USDT @ ${price.toFixed(2)}`,
      side==='BUY' ? 'var(--green)' : 'var(--red)'
    );
    log(`Paper ${side} ${qty} USDT ${S.sym} @ ${price.toFixed(2)}`);
  };
}