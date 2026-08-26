/* Vestra shared application utilities v1.0 — pure helpers only. */
(() => {
  'use strict';

  const normStr = (s) => String(s || '')
    .toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ').trim();

  const escapeHtml = (s) => String(s || '').replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const uid = () => Math.random().toString(16).slice(2) + Date.now().toString(16);
  const isoToday = () => new Date().toISOString().slice(0, 10);

  function safeClone(obj){
    try { if (typeof structuredClone === 'function') return structuredClone(obj); } catch (_) {}
    return JSON.parse(JSON.stringify(obj));
  }

  function parseNum(x){
    if (x === null || x === undefined) return 0;
    if (typeof x === 'number') return Number.isFinite(x) ? x : 0;
    let s = String(x).trim().replace(/[\u2212−]/g, '-').replace(/\u00A0/g, ' ').replace(/\s+/g, ' ');
    let neg = false;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
    let t = s.replace(/[^0-9,.\-]+/g, '').replace(/\s/g, '');
    const hasComma=t.includes(','), hasDot=t.includes('.');
    if (hasComma && hasDot) {
      if (t.lastIndexOf(',') > t.lastIndexOf('.')) t=t.replace(/\./g,'').replace(/,/g,'.');
      else t=t.replace(/,/g,'');
    } else if (hasComma) {
      if ((t.match(/,/g)||[]).length===1) {
        const [before,after]=t.split(',');
        const thousands=/^[0-9]{3}$/.test(after)&&before!=='0'&&before.length>=1;
        t=thousands?t.replace(/,/g,''):t.replace(/,/g,'.');
      } else t=t.replace(/,/g,'');
    } else if (hasDot) {
      if ((t.match(/\./g)||[]).length===1) {
        const [before,after]=t.split('.');
        const thousands=/^[0-9]{3}$/.test(after)&&before!=='0'&&before.length>=1;
        t=thousands?t.replace(/\./g,''):t;
      } else t=t.replace(/\./g,'');
    }
    const n=Number(t); const out=Number.isFinite(n)?n:0;
    return neg?-out:out;
  }

  function parseQty(x){
    if (x === null || x === undefined || x === '') return 0;
    if (typeof x === 'number') return Number.isFinite(x) ? x : 0;
    let t=String(x).trim().replace(/[\u2212−]/g,'-').replace(/\u00A0/g,'').replace(/\s+/g,'').replace(/[^0-9,.-]+/g,'');
    const commas=(t.match(/,/g)||[]).length, dots=(t.match(/\./g)||[]).length;
    if (commas&&dots) {
      if (t.lastIndexOf(',')>t.lastIndexOf('.')) t=t.replace(/\./g,'').replace(',','.');
      else t=t.replace(/,/g,'');
    } else if (commas) t=commas===1?t.replace(',','.'):t.replace(/,/g,'');
    const n=Number(t); return Number.isFinite(n)?n:0;
  }

  function normalizeDate(s){
    if (!s) return null;
    s=String(s).trim();
    const noTime=s.replace(/[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$/,'').trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(noTime)) return noTime;
    const parts=noTime.split(/[\/\-\.]/).filter(Boolean);
    if (parts.length===3) {
      const [a,b,c]=parts.map(Number);
      if (Number.isFinite(c)&&c>1000) return `${c}-${String(b).padStart(2,'0')}-${String(a).padStart(2,'0')}`;
      if (Number.isFinite(a)&&a>1000) return `${a}-${String(b).padStart(2,'0')}-${String(c).padStart(2,'0')}`;
    }
    return null;
  }

  function formatNumber(n,maxFrac=4){
    const v=Number(n); if(!Number.isFinite(v)) return '0';
    return new Intl.NumberFormat('pt-PT',{maximumFractionDigits:maxFrac,minimumFractionDigits:0}).format(v);
  }

  function normalizeClassName(s) {
    const map = {
      "stock":"Ações/ETFs","etf":"Ações/ETFs","equity":"Ações/ETFs","fund":"Fundos",
      "crypto":"Cripto","gold":"Ouro","silver":"Prata","real estate":"Imobiliário",
      "deposit":"Depósitos","cash":"Liquidez","ppr":"PPR","debt":"Dívida"
    };
    const n = normStr(s || "");
    for (const [k,v] of Object.entries(map)) { if (n.includes(k)) return v; }
    return s || "Outros";
  }

  function normalizeYieldType(s) {
    const n = normStr(s || "");
    if (n.includes("pct") || n.includes("%") || n.includes("percent")) return "yield_pct";
    if (n.includes("eur") || n.includes("year") || n.includes("annual")) return "yield_eur_year";
    if (n.includes("rent") || n.includes("month")) return "rent_month";
    return "none";
  }

  window.VestraUtils = Object.freeze({normStr,escapeHtml,uid,isoToday,safeClone,parseNum,parseQty,normalizeDate,formatNumber,normalizeClassName,normalizeYieldType});
})();
