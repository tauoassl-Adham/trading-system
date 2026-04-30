// ════════════════════════════════════════════
//  SCYLLA v4.0 — config.js
//  الثوابت والـ State المشترك بين كل الملفات
// ════════════════════════════════════════════
'use strict';

// ── API endpoints ────────────────────────────
const API    = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws/dashboard';

// ── DOM helper ───────────────────────────────
const $ = id => document.getElementById(id);

// ── Global State ─────────────────────────────
const S = {
  // رمز وإطار زمني نشط
  sym:  'BTCUSDT',
  tf:   '5m',
  mode: 'buy',

  // أسعار حية
  prices: {BTCUSDT:0, ETHUSDT:0, BNBUSDT:0},
  prev:   {BTCUSDT:0, ETHUSDT:0, BNBUSDT:0},
  open24: {BTCUSDT:0, ETHUSDT:0, BNBUSDT:0},

  // Sparklines
  spark: {BTCUSDT:[], ETHUSDT:[], BNBUSDT:[]},

  // عدادات
  feedCount: 0,
  tpsCount:  0,

  // حالة الاتصال
  bOk:  false,   // Binance WS
  beOk: false,   // Backend WS

  // إعدادات المستخدم
  theme: localStorage.getItem('sc-theme') || 'dark',
  lang:  localStorage.getItem('sc-lang')  || 'ar',
  use12h: localStorage.getItem('sc-12h') === 'true',

  // SMC
  smcSym: 'BTCUSDT',

  // MA visibility
  maVisible: {20:true, 50:true, 100:true, 200:true},
};

// ── Log Queue ────────────────────────────────
const LQ = [];
function log(m){
  LQ.push('['+new Date().toLocaleTimeString('en-US',{hour12:false})+'] '+m);
  if(LQ.length>30) LQ.shift();
  $('logTxt').textContent = LQ.slice(-2).join(' | ');
}

// ── Toast ────────────────────────────────────
function toast(msg, color='var(--accent)'){
  const e = $('toast');
  e.textContent = msg;
  e.style.color = color;
  e.classList.add('show');
  setTimeout(()=>e.classList.remove('show'), 3000);
}

// ── Format price ─────────────────────────────
function fmt(p){
  if(!p) return '--';
  return p>=1000
    ? p.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})
    : p.toFixed(4);
}