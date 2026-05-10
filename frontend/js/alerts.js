// ════════════════════════════════════════════
//  SCYLLA v4.0 — alerts.js
//  نظام التنبيهات: Toast + Sound + Settings
// ════════════════════════════════════════════

// ══════════════════════════════════════════
//  SOUND ENGINE
// ══════════════════════════════════════════
const SoundEngine = {
  ctx: null,

  init(){
    try{
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }catch(e){}
  },

  _play(freq, duration, type='sine', volume=0.3){
    if(!this.ctx) return;
    try{
      const osc  = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(volume, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    }catch(e){}
  },

  sounds: {
    entry(){
      SoundEngine._play(440,0.1);
      setTimeout(()=>SoundEngine._play(550,0.1),120);
      setTimeout(()=>SoundEngine._play(660,0.2),240);
    },
    exit(){
      SoundEngine._play(660,0.1);
      setTimeout(()=>SoundEngine._play(550,0.1),120);
      setTimeout(()=>SoundEngine._play(440,0.2),240);
    },
    choch(){
      SoundEngine._play(520,0.15,'square',0.2);
      setTimeout(()=>SoundEngine._play(520,0.15,'square',0.2),200);
    },
    bos(){
      SoundEngine._play(480,0.2,'triangle',0.25);
    },
    news(){
      SoundEngine._play(880,0.1,'sine',0.3);
      setTimeout(()=>SoundEngine._play(880,0.1,'sine',0.3),180);
    },
    warning(){
      SoundEngine._play(300,0.3,'sawtooth',0.4);
      setTimeout(()=>SoundEngine._play(300,0.3,'sawtooth',0.4),400);
    },
    portfolio(){
      SoundEngine._play(600,0.15);
      setTimeout(()=>SoundEngine._play(750,0.15),180);
    },
    system(){
      SoundEngine._play(350,0.1,'sine',0.15);
    },
    default(){
      SoundEngine._play(440,0.15);
    },
  },

  play(soundName){
    if(!A.settings.soundEnabled) return;
    const fn = this.sounds[soundName] || this.sounds.default;
    fn();
  },
};

// ══════════════════════════════════════════
//  ALERTS STATE
// ══════════════════════════════════════════
const A = {
  settings: {
    soundEnabled:  true,
    toastEnabled:  true,
    toastDuration: 6000,
    maxToasts:     5,
  },

  // ── خريطة نوع التنبيه → الصفحة التي ينقل إليها ──
  pageMap: {
    signal_entry:     'strategy',
    signal_exit:      'strategy',
    signal_choch:     'strategy',
    signal_bos:       'strategy',
    news_high_impact: 'news',
    psychology_alert: 'analytics',
    portfolio_alert:  'portfolio',
    system:           'dashboard',
  },

  types: {
    signal_entry: {
      label:'إشارة دخول', emoji:'🟢', sound:'entry',
      color:'var(--green)', enabled:true, telegram:true,
    },
    signal_exit: {
      label:'إشارة خروج', emoji:'🔴', sound:'exit',
      color:'var(--red)', enabled:true, telegram:true,
    },
    signal_choch: {
      label:'CHoCH', emoji:'⚡', sound:'choch',
      color:'var(--yellow)', enabled:true, telegram:true,
    },
    signal_bos: {
      label:'BOS', emoji:'📐', sound:'bos',
      color:'var(--accent)', enabled:true, telegram:true,
    },
    news_high_impact: {
      label:'خبر مهم', emoji:'📰', sound:'news',
      color:'#ff9800', enabled:true, telegram:true,
    },
    psychology_alert: {
      label:'تنبيه نفسي', emoji:'🧠', sound:'warning',
      color:'#e91e63', enabled:true, telegram:true,
    },
    portfolio_alert: {
      label:'تنبيه محفظة', emoji:'💼', sound:'portfolio',
      color:'var(--accent)', enabled:true, telegram:true,
    },
    system: {
      label:'النظام', emoji:'⚙️', sound:'system',
      color:'var(--text-dim)', enabled:true, telegram:false,
    },
  },

  history:      [],
  activeToasts: [],
};

// ══════════════════════════════════════════
//  TOAST ENGINE
// ══════════════════════════════════════════
const ToastEngine = {
  container: null,

  init(){
    this.container = document.createElement('div');
    this.container.id = 'alertsContainer';
    this.container.style.cssText = `
      position:fixed; top:70px; right:14px; z-index:9999;
      display:flex; flex-direction:column; gap:8px; pointer-events:none;
    `;
    document.body.appendChild(this.container);

    // ── CSS animations ──
    if(!document.getElementById('alertsCSS')){
      const style = document.createElement('style');
      style.id = 'alertsCSS';
      style.textContent = `
        @keyframes slideIn {
          from{opacity:0;transform:translateX(100%);}
          to{opacity:1;transform:translateX(0);}
        }
        @keyframes slideOut {
          from{opacity:1;transform:translateX(0);}
          to{opacity:0;transform:translateX(100%);}
        }
      `;
      document.head.appendChild(style);
    }
  },

  show(alertData){
    if(!A.settings.toastEnabled) return;

    const type    = A.types[alertData.alert_type] || A.types.system;
    const toast   = document.createElement('div');
    const toastId = Date.now();
    const targetPage = A.pageMap[alertData.alert_type] || 'dashboard';

    toast.dataset.id = toastId;
    toast.style.cssText = `
      background:var(--bg-card2);
      border:1px solid ${type.color};
      border-left:3px solid ${type.color};
      border-radius:6px; padding:10px 14px;
      min-width:280px; max-width:340px;
      pointer-events:all; cursor:pointer;
      animation:slideIn 0.3s ease;
      box-shadow:0 4px 20px rgba(0,0,0,0.5);
    `;

    toast.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span style="font-size:16px;">${type.emoji}</span>
        <span style="font-family:'Share Tech Mono',monospace;font-size:12px;
              color:${type.color};letter-spacing:1px;font-weight:700;">
          ${alertData.title || type.label}
        </span>
        <span style="margin-left:auto;font-family:'Share Tech Mono',monospace;
              font-size:10px;color:var(--text-dim);">
          ${new Date().toLocaleTimeString('en-US',{hour12:S.use12h})}
        </span>
      </div>
      ${alertData.message ? `
      <div style="font-family:'Share Tech Mono',monospace;font-size:11px;
            color:var(--text-secondary);line-height:1.5;">
        ${alertData.message}
      </div>` : ''}
      ${alertData.symbol ? `
      <div style="margin-top:4px;font-family:'Share Tech Mono',monospace;
            font-size:11px;color:var(--text-dim);">${alertData.symbol}</div>` : ''}
      <div style="margin-top:6px;font-family:'Share Tech Mono',monospace;
            font-size:10px;color:${type.color};opacity:0.7;">
        اضغط للانتقال ←
      </div>
    `;

    // ── الضغط ينقل للصفحة المناسبة ──
    toast.onclick = ()=>{
      ToastEngine.remove(toastId);
      if(typeof showPage === 'function') showPage(targetPage);
    };

    this.container.appendChild(toast);
    A.activeToasts.push(toastId);

    // حذف تلقائي
    const timer = setTimeout(()=>ToastEngine.remove(toastId), A.settings.toastDuration);
    toast._timer = timer;

    // حد أقصى للتوست
    if(A.activeToasts.length > A.settings.maxToasts){
      ToastEngine.remove(A.activeToasts[0]);
    }
  },

  remove(toastId){
    const toast = this.container?.querySelector(`[data-id="${toastId}"]`);
    if(!toast) return;
    if(toast._timer) clearTimeout(toast._timer);
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(()=>{ toast.remove(); }, 300);
    A.activeToasts = A.activeToasts.filter(id=>id!==toastId);
  },
};

// ══════════════════════════════════════════
//  NEWS TICKER — يتوقف عند hover
// ══════════════════════════════════════════
const NewsTicker = {
  items:    ['📡 يتصل بمصادر الأخبار...'],
  index:    0,
  interval: null,
  paused:   false,

  init(){
    this.interval = setInterval(()=>{
      if(!this.paused) this.next();
    }, 6000);
    this.render();

    // ── إيقاف عند hover لقراءة الخبر ──
    const wrap = document.querySelector('.news-ticker-wrap');
    if(wrap){
      wrap.addEventListener('mouseenter', ()=>{ this.paused=true; });
      wrap.addEventListener('mouseleave', ()=>{ this.paused=false; });
      // الضغط ينقل لصفحة الأخبار
      wrap.style.cursor = 'pointer';
      wrap.addEventListener('click', ()=>{
        if(typeof showPage==='function') showPage('news');
      });
    }
  },

  add(text){
    // تجنب التكرار
    if(this.items[0] === text) return;
    this.items.unshift(text);
    if(this.items.length > 50) this.items.pop();
    this.render();
  },

  next(){
    this.index = (this.index+1) % this.items.length;
    this.render();
  },

  render(){
    const el = $('newsTicker');
    if(!el) return;
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = 'tickerFade 0.4s ease';
    el.textContent = this.items[this.index] || '';
  },
};

// ══════════════════════════════════════════
//  MAIN ALERT HANDLER
// ══════════════════════════════════════════
function handleAlert(data){
  const alertType = data.alert_type;
  const typeCfg   = A.types[alertType];
  if(!typeCfg || !typeCfg.enabled) return;

  A.history.unshift({...data, timestamp: new Date().toISOString()});
  if(A.history.length > 100) A.history.pop();

  SoundEngine.play(data.sound || typeCfg.sound || 'default');
  ToastEngine.show(data);
  updateAlertsBadge();
  log(`🔔 Alert: [${alertType}] ${data.title||''}`);
}

// ══════════════════════════════════════════
//  ALERTS SETTINGS PANEL
// ══════════════════════════════════════════
function buildAlertsPanel(){
  const panel = $('alertsPanel');
  if(!panel) return;

  panel.innerHTML = `
    <div class="alerts-panel-header">
      <span class="alerts-panel-title">🔔 إعدادات التنبيهات</span>
      <button class="alerts-close-btn" onclick="closeAlertsPanel()">✕</button>
    </div>
    <div style="padding:14px;">

      <!-- Global Settings -->
      <div style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border);">
        <div style="font-family:'Share Tech Mono',monospace;font-size:11px;
              color:var(--accent);letter-spacing:2px;margin-bottom:10px;">الإعدادات العامة</div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          ${buildToggleRow('soundEnabled','الصوت',A.settings.soundEnabled,'setting')}
          ${buildToggleRow('toastEnabled','التوست',A.settings.toastEnabled,'setting')}
        </div>
      </div>

      <!-- Alert Types -->
      <div style="font-family:'Share Tech Mono',monospace;font-size:11px;
            color:var(--accent);letter-spacing:2px;margin-bottom:10px;">أنواع التنبيهات</div>
      <div style="display:flex;flex-direction:column;gap:6px;">
        ${Object.entries(A.types).map(([key,cfg])=>`
          <div style="display:flex;align-items:center;justify-content:space-between;
                padding:8px 10px;background:var(--bg-card);border-radius:4px;
                border:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:8px;">
              <span>${cfg.emoji}</span>
              <span style="font-family:'Share Tech Mono',monospace;font-size:12px;
                    color:var(--text-secondary);">${cfg.label}</span>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
              <select onchange="changeAlertSound('${key}',this.value)"
                style="background:var(--bg-card2);border:1px solid var(--border);
                       color:var(--text-secondary);font-size:10px;border-radius:3px;
                       padding:2px 4px;font-family:'Share Tech Mono',monospace;">
                ${['entry','exit','choch','bos','news','warning','portfolio','system','default']
                  .map(s=>`<option value="${s}" ${cfg.sound===s?'selected':''}>${s}</option>`)
                  .join('')}
              </select>
              <span style="font-family:'Share Tech Mono',monospace;font-size:10px;
                    color:var(--text-dim);">TG</span>
              ${buildMiniToggle(`toggleAlertTelegram('${key}')`, cfg.telegram)}
              ${buildMiniToggle(`toggleAlertType('${key}')`, cfg.enabled, true)}
            </div>
          </div>
        `).join('')}
      </div>

      <!-- Test -->
      <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);">
        <div style="font-family:'Share Tech Mono',monospace;font-size:11px;
              color:var(--accent);letter-spacing:2px;margin-bottom:8px;">اختبار</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
          ${Object.entries(A.types).map(([key,cfg])=>`
            <button onclick="testAlert('${key}')"
              style="padding:5px;background:var(--bg-card);border:1px solid var(--border);
                     color:var(--text-secondary);font-family:'Share Tech Mono',monospace;
                     font-size:10px;border-radius:3px;cursor:pointer;text-align:left;">
              ${cfg.emoji} ${cfg.label}
            </button>
          `).join('')}
        </div>
      </div>

    </div>
  `;
}

function buildMiniToggle(onclick, value, wide=false){
  const w = wide ? '36px' : '28px';
  const h = wide ? '18px' : '15px';
  const dot = wide ? '14px' : '11px';
  return `
    <div onclick="${onclick}"
         style="width:${w};height:${h};border-radius:9px;cursor:pointer;
                background:${value?'var(--green)':'var(--bg-card2)'};
                border:1px solid ${value?'var(--green)':'var(--border)'};
                transition:all .2s;position:relative;flex-shrink:0;">
      <div style="width:${dot};height:${dot};border-radius:50%;background:#fff;
                  position:absolute;top:1px;
                  ${value?'right:1px':'left:1px'};transition:all .2s;"></div>
    </div>
  `;
}

function buildToggleRow(key, label, value, scope){
  return `
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <span style="font-family:'Share Tech Mono',monospace;font-size:12px;
            color:var(--text-secondary);">${label}</span>
      ${buildMiniToggle(`toggleSetting('${key}','${scope}')`, value, true)}
    </div>
  `;
}

// ══════════════════════════════════════════
//  CONTROLS
// ══════════════════════════════════════════
function toggleAlertType(key){
  if(!A.types[key]) return;
  A.types[key].enabled=!A.types[key].enabled;
  if(beWS&&beWS.readyState===WebSocket.OPEN)
    beWS.send(JSON.stringify({action:'toggle_alert',alert_type:key,enabled:A.types[key].enabled}));
  buildAlertsPanel();
  saveAlertsSettings();
}

function toggleAlertTelegram(key){
  if(!A.types[key]) return;
  A.types[key].telegram=!A.types[key].telegram;
  buildAlertsPanel();
  saveAlertsSettings();
}

function changeAlertSound(key,sound){
  if(!A.types[key]) return;
  A.types[key].sound=sound;
  SoundEngine.play(sound);
  saveAlertsSettings();
}

function toggleSetting(key,scope){
  if(scope==='setting') A.settings[key]=!A.settings[key];
  buildAlertsPanel();
  saveAlertsSettings();
}

function testAlert(type){
  const cfg=A.types[type]; if(!cfg)return;
  handleAlert({
    alert_type: type,
    title:      `اختبار — ${cfg.label}`,
    message:    'هذا تنبيه تجريبي',
    symbol:     'BTCUSDT',
    sound:      cfg.sound,
  });
}

// ══════════════════════════════════════════
//  PERSISTENCE
// ══════════════════════════════════════════
function saveAlertsSettings(){
  try{
    localStorage.setItem('sc-alerts-settings',JSON.stringify(A.settings));
    localStorage.setItem('sc-alerts-types',JSON.stringify(A.types));
  }catch(e){}
}

function loadAlertsSettings(){
  try{
    const settings=localStorage.getItem('sc-alerts-settings');
    const types=localStorage.getItem('sc-alerts-types');
    if(settings) Object.assign(A.settings,JSON.parse(settings));
    if(types){
      const saved=JSON.parse(types);
      Object.keys(A.types).forEach(k=>{
        if(saved[k]) Object.assign(A.types[k],saved[k]);
      });
    }
  }catch(e){}
}

// ══════════════════════════════════════════
//  BADGE
// ══════════════════════════════════════════
let unreadAlerts=0;

function updateAlertsBadge(){
  unreadAlerts++;
  const badge=$('alertsBadge');
  if(badge){
    badge.textContent=unreadAlerts>99?'99+':unreadAlerts;
    badge.style.display='flex';
  }
}

function clearAlertsBadge(){
  unreadAlerts=0;
  const badge=$('alertsBadge');
  if(badge) badge.style.display='none';
}

// ══════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════
function initAlerts(){
  loadAlertsSettings();
  SoundEngine.init();
  ToastEngine.init();
  NewsTicker.init();
  buildAlertsPanel();
  log('Alerts system initialized');
}