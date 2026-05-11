// ════════════════════════════════════════════
//  SCYLLA v4.0 — news.js
//  صفحة الأخبار الكاملة:
//  GNews AR + Finnhub EN + Filters + AI Summary
//  + Impact Classifier + Search + Bookmarks
//
//  المسار: frontend/js/news.js
//  يُضاف قبل app.js في dashboard.html
// ════════════════════════════════════════════
'use strict';

// ══════════════════════════════════════════
//  NEWS STATE
// ══════════════════════════════════════════
const N = {
  items:      [],         // كل الأخبار
  bookmarks:  [],         // محفوظات
  filter: {
    impact:   'all',      // all | high | medium | low
    source:   'all',      // all | ar | en
    symbol:   'all',      // all | BTC | ETH | BNB
    search:   '',
  },
  page:        0,
  pageSize:    20,
  loading:     false,
  lastFetch:   0,
  autoRefresh: null,
};

// مصادر الأخبار وألوانها
const NEWS_SOURCES = {
  gnews:    { label:'GNews AR',  color:'#00d4ff', flag:'🇸🇦' },
  finnhub:  { label:'Finnhub',   color:'#f5a623', flag:'🇺🇸' },
  rss:      { label:'RSS',       color:'#9b59b6', flag:'🌐' },
  internal: { label:'Internal',  color:'#00f07a', flag:'⚡' },
};

// مستويات الأثر
const IMPACT_LEVELS = {
  high:   { label:'عالي',   color:'#ff2d55', bg:'rgba(255,45,85,.12)',   icon:'🔴' },
  medium: { label:'متوسط',  color:'#ffe033', bg:'rgba(255,224,51,.10)', icon:'🟡' },
  low:    { label:'منخفض',  color:'#8ab4d8', bg:'rgba(138,180,216,.08)',icon:'⚪' },
};

// الكلمات المفتاحية لتصنيف الأثر
const HIGH_IMPACT_KEYWORDS = [
  'ETF','SEC','fed','federal reserve','rate','inflation','crash','ban',
  'regulation','hack','exploit','lawsuit','bankrupt','delist',
  'حظر','احتياطي فيدرالي','تنظيم','اختراق','إفلاس','هبوط حاد',
  'تصفية','تحقيق','غرامة','انهيار',
];
const MEDIUM_IMPACT_KEYWORDS = [
  'partnership','launch','upgrade','halving','whale','adoption',
  'شراكة','إطلاق','ترقية','تبني','مؤسسي','تحديث',
];

// ══════════════════════════════════════════
//  IMPACT CLASSIFIER
// ══════════════════════════════════════════
function classifyImpact(item){
  const text = `${item.headline||''} ${item.headline_ar||''} ${item.summary||''}`.toLowerCase();
  for(const kw of HIGH_IMPACT_KEYWORDS){
    if(text.includes(kw.toLowerCase())) return 'high';
  }
  for(const kw of MEDIUM_IMPACT_KEYWORDS){
    if(text.includes(kw.toLowerCase())) return 'medium';
  }
  return 'low';
}

// ══════════════════════════════════════════
//  SYMBOL TAGGER — يكتشف الرمز من النص
// ══════════════════════════════════════════
function detectSymbols(item){
  const text = `${item.headline||''} ${item.headline_ar||''} ${item.summary||''}`.toUpperCase();
  const found = [];
  if(/BTC|BITCOIN|بيتكوين/.test(text))  found.push('BTC');
  if(/ETH|ETHEREUM|إيثريوم/.test(text)) found.push('ETH');
  if(/BNB|BINANCE/.test(text))          found.push('BNB');
  if(/CRYPTO|DIGITAL|BLOCKCHAIN|بلوك/.test(text) && !found.length) found.push('CRYPTO');
  return found.length ? found : ['GENERAL'];
}

// ══════════════════════════════════════════
//  FETCH NEWS
// ══════════════════════════════════════════
async function fetchNews(force=false){
  if(N.loading) return;
  const now = Date.now();
  if(!force && now - N.lastFetch < 60000) return;   // throttle: مرة كل دقيقة

  N.loading = true;
  setNewsLoading(true);

  let fetched = [];

  // 1. من الباكند
  try{
    const r = await fetch(`${API}/api/news?limit=50`);
    if(r.ok){
      const d = await r.json();
      fetched = [...fetched, ...(d.items || d.news || [])];
    }
  }catch(e){}

  // 2. أخبار مهمة فقط
  try{
    const r = await fetch(`${API}/api/news/important`);
    if(r.ok){
      const d = await r.json();
      const imp = (d.items || []).map(x=>({...x, is_important:true}));
      // دمج بدون تكرار
      imp.forEach(item=>{
        if(!fetched.find(f=>f.id===item.id||f.headline===item.headline))
          fetched.push(item);
      });
    }
  }catch(e){}

  // إذا فارغ → demo items للعرض
  if(!fetched.length) fetched = buildDemoNews();

  // تطبيع + تصنيف
  fetched = fetched.map(normalizeNewsItem).filter(Boolean);

  // دمج مع الموجود (بدون تكرار)
  const existingIds = new Set(N.items.map(i=>i.id));
  const newItems    = fetched.filter(i => !existingIds.has(i.id));

  N.items = [...newItems, ...N.items].slice(0, 500);
  N.lastFetch = now;
  N.loading   = false;

  renderNewsPage();
  setNewsLoading(false);

  if(newItems.length){
    log(`News: +${newItems.length} مقالة جديدة`);
    newItems.filter(i=>i.impact==='high').forEach(i=>{
      NewsTicker.add(`🔴 ${i.headline_ar || i.headline}`);
    });
  }
}

function normalizeNewsItem(raw){
  if(!raw) return null;
  const id = raw.id || raw.url || raw.headline || Math.random().toString(36).slice(2);
  return {
    id:          id,
    headline:    raw.headline    || raw.title    || '',
    headline_ar: raw.headline_ar || raw.title_ar || '',
    summary:     raw.summary     || raw.description || '',
    summary_ar:  raw.summary_ar  || '',
    source:      raw.source      || raw.source_name || 'gnews',
    url:         raw.url         || raw.link || '#',
    publishedAt: raw.published_at || raw.datetime || raw.publishedAt || Date.now()/1000,
    image:       raw.image       || raw.image_url || null,
    is_important:raw.is_important || false,
    impact:      raw.impact      || classifyImpact(raw),
    symbols:     raw.symbols     || detectSymbols(raw),
    bookmarked:  N.bookmarks.includes(id),
    aiSummary:   raw.ai_summary  || null,
  };
}

// Demo news للعرض عند غياب الباكند
function buildDemoNews(){
  return [
    { id:'d1', headline:'Bitcoin ETF Sees Record Inflows of $500M in Single Day',
      headline_ar:'صناديق بيتكوين المتداولة تسجل تدفقات قياسية بـ 500 مليون دولار',
      source:'finnhub', is_important:true, impact:'high', symbols:['BTC'],
      publishedAt: Date.now()/1000 - 300,
      summary:'Institutional investors continue to pour money into Bitcoin ETFs...',
    },
    { id:'d2', headline:'Ethereum Developers Confirm Next Hard Fork Timeline',
      headline_ar:'مطورو إيثريوم يؤكدون موعد الشوكة الصلبة القادمة',
      source:'rss', impact:'medium', symbols:['ETH'],
      publishedAt: Date.now()/1000 - 1200,
      summary:'The Ethereum core development team has confirmed...',
    },
    { id:'d3', headline:'Federal Reserve Signals Possible Rate Cut in Q3',
      headline_ar:'الاحتياطي الفيدرالي يلمح لخفض محتمل في أسعار الفائدة',
      source:'finnhub', is_important:true, impact:'high', symbols:['BTC','ETH'],
      publishedAt: Date.now()/1000 - 3600,
      summary:'Federal Reserve officials signaled a possible interest rate reduction...',
    },
    { id:'d4', headline:'BNB Chain Launches New DeFi Incentive Program',
      headline_ar:'سلسلة BNB تطلق برنامج حوافز DeFi جديد',
      source:'gnews', impact:'medium', symbols:['BNB'],
      publishedAt: Date.now()/1000 - 7200,
      summary:'Binance Smart Chain announced a new incentive program...',
    },
    { id:'d5', headline:'Crypto Market Shows Resilience Amid Global Uncertainty',
      headline_ar:'سوق العملات الرقمية يُظهر مرونة وسط حالة عدم اليقين العالمية',
      source:'gnews', impact:'low', symbols:['CRYPTO'],
      publishedAt: Date.now()/1000 - 14400,
      summary:'Despite ongoing macroeconomic challenges...',
    },
  ];
}

// ══════════════════════════════════════════
//  FILTER ENGINE
// ══════════════════════════════════════════
function getFilteredNews(){
  return N.items.filter(item => {
    if(N.filter.impact !== 'all' && item.impact !== N.filter.impact) return false;
    if(N.filter.source !== 'all'){
      const src = item.source?.toLowerCase() || '';
      if(N.filter.source === 'ar' && !src.includes('gnews')) return false;
      if(N.filter.source === 'en' && src.includes('gnews'))  return false;
    }
    if(N.filter.symbol !== 'all' && !item.symbols.includes(N.filter.symbol)) return false;
    if(N.filter.search){
      const q = N.filter.search.toLowerCase();
      const t = `${item.headline} ${item.headline_ar} ${item.summary}`.toLowerCase();
      if(!t.includes(q)) return false;
    }
    return true;
  });
}

// ══════════════════════════════════════════
//  BOOKMARK
// ══════════════════════════════════════════
function toggleBookmark(id){
  const item = N.items.find(i=>i.id===id);
  if(!item) return;
  item.bookmarked = !item.bookmarked;
  if(item.bookmarked){
    if(!N.bookmarks.includes(id)) N.bookmarks.push(id);
  } else {
    N.bookmarks = N.bookmarks.filter(b=>b!==id);
  }
  saveNewsState();
  renderNewsPage();
}

// ══════════════════════════════════════════
//  AI SUMMARY (يستخدم الباكند)
// ══════════════════════════════════════════
async function fetchAISummary(itemId){
  const item = N.items.find(i=>i.id===itemId);
  if(!item || item.aiSummary) return;

  const el = $(`aiSum-${itemId}`);
  if(el) el.innerHTML = '<span style="color:var(--text-dim);font-size:10px">⏳ الذكاء الاصطناعي يحلل...</span>';

  try{
    const r = await fetch(`${API}/api/ai/analyze-market`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        prompt: `حلل هذا الخبر المالي في جملتين بالعربية وأثره على سوق العملات الرقمية:\n${item.headline_ar||item.headline}`,
      }),
    });
    if(r.ok){
      const d = await r.json();
      item.aiSummary = d.response || d.analysis || 'لا يوجد تحليل متاح';
      if(el) el.innerHTML = `<div class="news-ai-box">🤖 ${item.aiSummary}</div>`;
    }
  }catch(e){
    if(el) el.innerHTML = '<span style="color:var(--red);font-size:10px">تعذر الاتصال بالذكاء الاصطناعي</span>';
  }
}

// ══════════════════════════════════════════
//  RENDER — الصفحة الكاملة
// ══════════════════════════════════════════
function renderNewsPage(){
  const container = $('page-news');
  if(!container) return;

  const filtered = getFilteredNews();
  const paged    = filtered.slice(0, (N.page + 1) * N.pageSize);
  const hasMore  = filtered.length > paged.length;

  container.innerHTML = `
    <div class="news-layout">

      <!-- SIDEBAR -->
      <div class="news-sidebar">
        <div class="news-sb-section">
          <div class="news-sb-title">FILTERS</div>

          <!-- Search -->
          <div class="news-search-wrap">
            <span class="news-search-icon">🔍</span>
            <input type="text" class="news-search-input" id="newsSearch"
              placeholder="ابحث في الأخبار..." value="${N.filter.search}"
              oninput="setNewsFilter('search',this.value)">
          </div>

          <!-- Impact -->
          <div class="news-filter-group">
            <div class="news-filter-lbl">الأثر</div>
            <div class="news-filter-btns">
              ${['all','high','medium','low'].map(v=>`
                <button class="news-filter-btn ${N.filter.impact===v?'active':''}"
                  onclick="setNewsFilter('impact','${v}')"
                  ${v!=='all'?`style="--fc:${IMPACT_LEVELS[v]?.color||'var(--accent)'}"`:''}>
                  ${v==='all'?'الكل':IMPACT_LEVELS[v].icon+' '+IMPACT_LEVELS[v].label}
                </button>`).join('')}
            </div>
          </div>

          <!-- Source -->
          <div class="news-filter-group">
            <div class="news-filter-lbl">المصدر</div>
            <div class="news-filter-btns">
              ${[['all','الكل'],['ar','🇸🇦 عربي'],['en','🇺🇸 إنجليزي']].map(([v,l])=>`
                <button class="news-filter-btn ${N.filter.source===v?'active':''}"
                  onclick="setNewsFilter('source','${v}')">${l}</button>`).join('')}
            </div>
          </div>

          <!-- Symbol -->
          <div class="news-filter-group">
            <div class="news-filter-lbl">الرمز</div>
            <div class="news-filter-btns">
              ${[['all','الكل'],['BTC','₿ BTC'],['ETH','Ξ ETH'],['BNB','◈ BNB']].map(([v,l])=>`
                <button class="news-filter-btn ${N.filter.symbol===v?'active':''}"
                  onclick="setNewsFilter('symbol','${v}')">${l}</button>`).join('')}
            </div>
          </div>
        </div>

        <!-- Stats -->
        <div class="news-sb-section">
          <div class="news-sb-title">إحصائيات</div>
          <div class="news-stats-mini">
            <div class="nsm-row"><span>إجمالي</span><span>${N.items.length}</span></div>
            <div class="nsm-row"><span>🔴 عالي</span><span>${N.items.filter(i=>i.impact==='high').length}</span></div>
            <div class="nsm-row"><span>🟡 متوسط</span><span>${N.items.filter(i=>i.impact==='medium').length}</span></div>
            <div class="nsm-row"><span>محفوظات</span><span>${N.bookmarks.length}</span></div>
            <div class="nsm-row"><span>معروض</span><span>${filtered.length}</span></div>
          </div>
        </div>

        <!-- Refresh -->
        <button class="news-refresh-btn" onclick="fetchNews(true)" id="newsRefreshBtn">
          ⟳ تحديث الأخبار
        </button>
        <div class="news-last-update" id="newsLastUpdate">
          ${N.lastFetch ? 'آخر تحديث: ' + new Date(N.lastFetch).toLocaleTimeString() : 'لم يتم التحديث بعد'}
        </div>
      </div>

      <!-- MAIN FEED -->
      <div class="news-feed-wrap">

        <!-- Header -->
        <div class="news-feed-header">
          <span class="news-feed-title">📡 بث الأخبار المباشر</span>
          <span class="news-feed-count">${filtered.length} خبر</span>
          <div class="news-view-toggle">
            <button class="nvt-btn active" id="nvtCard" onclick="setNewsView('card')">⊞</button>
            <button class="nvt-btn" id="nvtList" onclick="setNewsView('list')">☰</button>
          </div>
        </div>

        <!-- Loading -->
        <div class="news-loading" id="newsLoadingBar" style="display:${N.loading?'flex':'none'}">
          <div class="news-spinner"></div>
          <span>جارٍ تحميل الأخبار...</span>
        </div>

        <!-- Empty State -->
        ${!filtered.length ? `
          <div class="news-empty">
            <div class="news-empty-icon">📭</div>
            <div class="news-empty-txt">لا توجد أخبار تطابق الفلتر الحالي</div>
            <button class="news-reset-filter" onclick="resetNewsFilters()">إعادة تعيين الفلاتر</button>
          </div>` : ''}

        <!-- Cards -->
        <div class="news-cards" id="newsCards">
          ${paged.map(item => buildNewsCard(item)).join('')}
        </div>

        <!-- Load More -->
        ${hasMore ? `
          <button class="news-load-more" onclick="loadMoreNews()">
            تحميل المزيد (${filtered.length - paged.length} خبر)
          </button>` : ''}
      </div>
    </div>
  `;

  injectNewsCSS();
}

// ══════════════════════════════════════════
//  BUILD NEWS CARD
// ══════════════════════════════════════════
function buildNewsCard(item){
  const imp      = IMPACT_LEVELS[item.impact] || IMPACT_LEVELS.low;
  const src      = NEWS_SOURCES[item.source]  || { label:item.source||'?', color:'#8ab4d8', flag:'🌐' };
  const timeAgo  = formatTimeAgo(item.publishedAt);
  const title    = item.headline_ar || item.headline || 'بدون عنوان';
  const subtitle = item.headline_ar && item.headline ? item.headline : '';

  return `
  <div class="news-card ${item.impact}" id="nc-${item.id}"
       style="--imp-color:${imp.color}; --imp-bg:${imp.bg};">

    <!-- Impact Badge + Source -->
    <div class="nc-meta">
      <span class="nc-impact" style="background:${imp.bg};color:${imp.color};border-color:${imp.color}20;">
        ${imp.icon} ${imp.label}
      </span>
      <span class="nc-source" style="color:${src.color}">
        ${src.flag} ${src.label}
      </span>
      <span class="nc-time">${timeAgo}</span>
      <span class="nc-bookmark ${item.bookmarked?'active':''}"
            onclick="toggleBookmark('${item.id}')" title="حفظ">
        ${item.bookmarked ? '🔖' : '📑'}
      </span>
    </div>

    <!-- Symbol Tags -->
    ${item.symbols.map(s=>`<span class="nc-sym-tag">${s}</span>`).join('')}

    <!-- Title -->
    <div class="nc-title">${title}</div>
    ${subtitle ? `<div class="nc-subtitle">${subtitle}</div>` : ''}

    <!-- Summary -->
    ${item.summary_ar || item.summary ? `
      <div class="nc-summary">${(item.summary_ar||item.summary).slice(0,160)}${(item.summary_ar||item.summary).length>160?'...':''}</div>
    ` : ''}

    <!-- AI Summary -->
    <div class="nc-ai" id="aiSum-${item.id}">
      ${item.aiSummary
        ? `<div class="news-ai-box">🤖 ${item.aiSummary}</div>`
        : `<button class="nc-ai-btn" onclick="fetchAISummary('${item.id}')">🤖 تحليل ذكاء اصطناعي</button>`
      }
    </div>

    <!-- Actions -->
    <div class="nc-actions">
      ${item.url && item.url !== '#'
        ? `<a href="${item.url}" target="_blank" class="nc-link-btn">قراءة الكاملة ↗</a>`
        : ''}
      <button class="nc-share-btn" onclick="shareNews('${item.id}')">مشاركة</button>
    </div>
  </div>`;
}

// ══════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════
function formatTimeAgo(ts){
  const seconds = Math.floor(Date.now()/1000 - ts);
  if(seconds < 60)   return `${seconds}ث`;
  if(seconds < 3600) return `${Math.floor(seconds/60)}د`;
  if(seconds < 86400)return `${Math.floor(seconds/3600)}س`;
  return `${Math.floor(seconds/86400)}ي`;
}

function setNewsFilter(key, value){
  N.filter[key] = value;
  N.page = 0;
  renderNewsPage();
}

function resetNewsFilters(){
  N.filter = { impact:'all', source:'all', symbol:'all', search:'' };
  N.page   = 0;
  renderNewsPage();
}

function loadMoreNews(){
  N.page++;
  renderNewsPage();
}

let _newsView = 'card';
function setNewsView(view){
  _newsView = view;
  const cards = $('newsCards');
  if(cards) cards.className = view==='list' ? 'news-cards list-view' : 'news-cards';
  document.querySelectorAll('.nvt-btn').forEach(b=>b.classList.remove('active'));
  const btn = view==='card' ? $('nvtCard') : $('nvtList');
  if(btn) btn.classList.add('active');
}

function setNewsLoading(on){
  const el = $('newsLoadingBar');
  if(el) el.style.display = on ? 'flex' : 'none';
  const btn = $('newsRefreshBtn');
  if(btn) btn.disabled = on;
}

function shareNews(id){
  const item = N.items.find(i=>i.id===id);
  if(!item) return;
  const text = `${item.headline_ar||item.headline}\n${item.url||''}`;
  if(navigator.clipboard) navigator.clipboard.writeText(text).then(()=>toast('تم النسخ ✓','var(--green)'));
}

// ══════════════════════════════════════════
//  PERSISTENCE
// ══════════════════════════════════════════
function saveNewsState(){
  try{
    localStorage.setItem('sc-news-bookmarks', JSON.stringify(N.bookmarks));
  }catch(e){}
}

function loadNewsState(){
  try{
    const bm = localStorage.getItem('sc-news-bookmarks');
    if(bm) N.bookmarks = JSON.parse(bm);
  }catch(e){}
}

// ══════════════════════════════════════════
//  CSS INJECTION
// ══════════════════════════════════════════
function injectNewsCSS(){
  if(document.getElementById('newsCSS')) return;
  const style = document.createElement('style');
  style.id = 'newsCSS';
  style.textContent = `
    /* ── News Page Layout ── */
    #page-news{flex-direction:row;overflow:hidden;}
    .news-layout{display:flex;width:100%;height:100%;overflow:hidden;}

    /* ── Sidebar ── */
    .news-sidebar{
      width:220px;flex-shrink:0;
      background:var(--bg-panel);border-right:1px solid var(--border);
      display:flex;flex-direction:column;gap:0;overflow-y:auto;
    }
    .news-sidebar::-webkit-scrollbar{width:2px;}
    .news-sidebar::-webkit-scrollbar-thumb{background:var(--border-glow);}
    .news-sb-section{padding:12px;border-bottom:1px solid var(--border);}
    .news-sb-title{font-family:'Share Tech Mono',monospace;font-size:10px;
      color:var(--accent);letter-spacing:2px;margin-bottom:10px;}

    /* Search */
    .news-search-wrap{display:flex;align-items:center;gap:6px;
      background:var(--bg-card);border:1px solid var(--border);border-radius:4px;
      padding:4px 8px;margin-bottom:10px;}
    .news-search-icon{font-size:12px;color:var(--text-dim);}
    .news-search-input{background:transparent;border:none;outline:none;
      font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--text-primary);width:100%;}
    .news-search-input::placeholder{color:var(--text-dim);}

    /* Filter Groups */
    .news-filter-group{margin-bottom:10px;}
    .news-filter-lbl{font-family:'Share Tech Mono',monospace;font-size:9px;
      color:var(--text-dim);letter-spacing:1.5px;margin-bottom:5px;}
    .news-filter-btns{display:flex;flex-wrap:wrap;gap:3px;}
    .news-filter-btn{padding:3px 7px;border:1px solid var(--border);background:transparent;
      font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);
      cursor:pointer;border-radius:3px;transition:all .15s;}
    .news-filter-btn:hover{border-color:var(--border-glow);color:var(--text-secondary);}
    .news-filter-btn.active{
      border-color:var(--fc,var(--accent));
      color:var(--fc,var(--accent));
      background:rgba(0,180,255,.08);
    }

    /* Stats mini */
    .news-stats-mini{display:flex;flex-direction:column;gap:4px;}
    .nsm-row{display:flex;justify-content:space-between;
      font-family:'Share Tech Mono',monospace;font-size:11px;}
    .nsm-row span:first-child{color:var(--text-dim);}
    .nsm-row span:last-child{color:var(--text-secondary);}

    /* Refresh */
    .news-refresh-btn{margin:10px 12px 0;padding:7px;
      background:rgba(0,180,255,.07);border:1px solid var(--border-glow);
      color:var(--accent);font-family:'Share Tech Mono',monospace;font-size:11px;
      cursor:pointer;border-radius:4px;transition:all .2s;}
    .news-refresh-btn:hover{background:rgba(0,180,255,.14);}
    .news-refresh-btn:disabled{opacity:.4;cursor:not-allowed;}
    .news-last-update{font-family:'Share Tech Mono',monospace;font-size:9px;
      color:var(--text-dim);text-align:center;padding:5px 12px 10px;}

    /* ── Feed Wrap ── */
    .news-feed-wrap{flex:1;display:flex;flex-direction:column;overflow:hidden;}
    .news-feed-header{
      display:flex;align-items:center;gap:10px;padding:10px 14px;
      border-bottom:1px solid var(--border);background:var(--bg-card);flex-shrink:0;
    }
    .news-feed-title{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--accent);letter-spacing:2px;}
    .news-feed-count{font-family:'Share Tech Mono',monospace;font-size:11px;
      color:var(--text-dim);background:var(--bg-card2);padding:2px 8px;border-radius:10px;border:1px solid var(--border);}
    .news-view-toggle{margin-left:auto;display:flex;gap:3px;}
    .nvt-btn{width:26px;height:26px;border:1px solid var(--border);background:transparent;
      color:var(--text-dim);cursor:pointer;border-radius:3px;font-size:14px;transition:all .15s;}
    .nvt-btn.active{border-color:var(--accent);color:var(--accent);}

    /* Loading / Empty */
    .news-loading{display:flex;align-items:center;gap:10px;padding:20px;
      font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-dim);}
    .news-spinner{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);
      border-radius:50%;animation:spin 1s linear infinite;flex-shrink:0;}
    .news-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
      gap:10px;padding:40px;flex:1;}
    .news-empty-icon{font-size:32px;}
    .news-empty-txt{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--text-dim);}
    .news-reset-filter{padding:6px 14px;background:rgba(0,180,255,.07);
      border:1px solid var(--border-glow);color:var(--accent);
      font-family:'Share Tech Mono',monospace;font-size:11px;cursor:pointer;border-radius:4px;}

    /* ── Cards Container ── */
    .news-cards{flex:1;overflow-y:auto;padding:12px;
      display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
      gap:10px;align-content:start;}
    .news-cards::-webkit-scrollbar{width:3px;}
    .news-cards::-webkit-scrollbar-thumb{background:var(--border-glow);}
    .news-cards.list-view{grid-template-columns:1fr;}

    /* ── News Card ── */
    .news-card{
      background:var(--bg-card);border:1px solid var(--border);border-radius:6px;
      padding:12px;display:flex;flex-direction:column;gap:7px;
      border-left:3px solid var(--imp-color,var(--border));
      transition:border-color .15s,background .15s;
    }
    .news-card:hover{background:var(--bg-card2);}
    .news-card.high{border-left-color:#ff2d55;}
    .news-card.medium{border-left-color:#ffe033;}
    .news-card.low{border-left-color:var(--border-glow);}

    /* Card Meta */
    .nc-meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
    .nc-impact{font-family:'Share Tech Mono',monospace;font-size:10px;
      padding:2px 7px;border-radius:10px;border:1px solid;flex-shrink:0;}
    .nc-source{font-family:'Share Tech Mono',monospace;font-size:10px;}
    .nc-time{font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--text-dim);margin-right:auto;}
    .nc-bookmark{cursor:pointer;font-size:14px;transition:transform .15s;}
    .nc-bookmark:hover{transform:scale(1.2);}
    .nc-bookmark.active{filter:drop-shadow(0 0 4px var(--yellow));}

    /* Symbol Tags */
    .nc-sym-tag{display:inline-block;font-family:'Share Tech Mono',monospace;font-size:10px;
      color:var(--accent);background:rgba(0,180,255,.08);border:1px solid rgba(0,180,255,.2);
      padding:1px 6px;border-radius:3px;margin-left:3px;}

    /* Titles */
    .nc-title{font-family:'Tajawal',sans-serif;font-size:14px;font-weight:700;
      color:var(--text-primary);line-height:1.5;}
    .nc-subtitle{font-family:'Inter',sans-serif;font-size:11px;color:var(--text-dim);
      line-height:1.4;font-style:italic;}
    .nc-summary{font-family:'Tajawal',sans-serif;font-size:12px;color:var(--text-secondary);
      line-height:1.7;direction:rtl;}

    /* AI */
    .nc-ai{min-height:24px;}
    .nc-ai-btn{background:rgba(231,76,60,.08);border:1px solid rgba(231,76,60,.2);
      color:#e74c3c;font-family:'Share Tech Mono',monospace;font-size:10px;
      cursor:pointer;padding:3px 10px;border-radius:3px;transition:all .15s;}
    .nc-ai-btn:hover{background:rgba(231,76,60,.16);}
    .news-ai-box{background:rgba(231,76,60,.06);border:1px solid rgba(231,76,60,.15);
      border-radius:4px;padding:7px 10px;font-family:'Tajawal',sans-serif;
      font-size:12px;color:var(--text-secondary);line-height:1.6;direction:rtl;}

    /* Actions */
    .nc-actions{display:flex;gap:6px;margin-top:2px;}
    .nc-link-btn{padding:4px 10px;background:rgba(0,180,255,.07);
      border:1px solid var(--border-glow);color:var(--accent);
      font-family:'Share Tech Mono',monospace;font-size:10px;
      text-decoration:none;border-radius:3px;transition:all .15s;}
    .nc-link-btn:hover{background:rgba(0,180,255,.14);}
    .nc-share-btn{padding:4px 10px;background:transparent;border:1px solid var(--border);
      color:var(--text-dim);font-family:'Share Tech Mono',monospace;font-size:10px;
      cursor:pointer;border-radius:3px;transition:all .15s;}
    .nc-share-btn:hover{border-color:var(--border-glow);color:var(--text-secondary);}

    /* Load More */
    .news-load-more{margin:10px auto;display:block;padding:8px 24px;
      background:rgba(0,180,255,.07);border:1px solid var(--border-glow);
      color:var(--accent);font-family:'Share Tech Mono',monospace;font-size:11px;
      cursor:pointer;border-radius:4px;transition:all .2s;}
    .news-load-more:hover{background:rgba(0,180,255,.14);}

    /* List View override */
    .list-view .news-card{grid-template-columns:1fr;border-radius:3px;}
    .list-view .nc-title{font-size:13px;}
    .list-view .nc-summary{display:none;}
    .list-view .nc-ai{display:none;}

    @media(max-width:900px){
      .news-sidebar{width:100%;max-height:200px;flex-direction:row;flex-wrap:wrap;}
      #page-news{flex-direction:column;}
      .news-cards{grid-template-columns:1fr;}
    }
  `;
  document.head.appendChild(style);
}

// ══════════════════════════════════════════
//  INTEGRATION — WebSocket news_update
//  يستقبل الأخبار من connectBackend() في market.js
// ══════════════════════════════════════════
function processNewsUpdate(items){
  if(!items?.length) return;
  let newCount = 0;
  items.forEach(raw => {
    const item = normalizeNewsItem(raw);
    if(!item) return;
    if(!N.items.find(i=>i.id===item.id)){
      N.items.unshift(item);
      newCount++;
    }
  });
  if(N.items.length > 500) N.items = N.items.slice(0, 500);

  // إذا الصفحة مفتوحة، حدِّث
  if($('page-news')?.classList.contains('active')) renderNewsPage();

  // أخبار عالية الأثر → ticker + alert
  items.filter(i=>i.is_important||classifyImpact(i)==='high').forEach(i=>{
    const title = i.headline_ar || i.headline || '';
    if(title) NewsTicker.add(`🔴 ${title}`);
  });

  N.lastFetch = Date.now();
  log(`News: +${newCount} مقالة`);
}

// ══════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════
function initNews(){
  loadNewsState();

  // بناء صفحة فارغة فوراً
  renderNewsPage();

  // تحميل أولي
  fetchNews(true);

  // تحديث تلقائي كل 5 دقائق
  N.autoRefresh = setInterval(()=> fetchNews(), 5 * 60 * 1000);

  log('News system initialized — GNews AR + Finnhub EN + AI + Bookmarks');
}