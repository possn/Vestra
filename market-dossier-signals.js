/* Vestra Market Dossier Signals v1.0 — read-only evidence, catalyst, recovery and drawdown panels. */
(() => {
  'use strict';

  function create(options={}){
    const text = options.text || (v => String(v ?? '').trim());
    const number = options.number || (v => {
      if (v === null || v === undefined || v === '') return null;
      const x=Number(v); return Number.isFinite(x)?x:null;
    });
    const escapeHtml = options.escapeHtml || (v => text(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
    const formatShortDate = options.formatShortDate || (v => text(v));

    function evidencePanel(s={}){
      const p=s?.data_provenance;
      if(!p || typeof p!=='object') return '';
      const independent=number(p.independent_fundamental_source_count);
      const confidence=number(s.confidence_score);
      const coverage=number(s.data_coverage_pct);
      const age=number(s.fundamental_age_days);
      const state=text(p.evidence_state);
      const stateLabel={observed:'Observado no build atual',carried_forward:'Transportado do último build válido',metadata_only:'Apenas identidade/metadata'}[state]||'Estado de evidência não classificado';
      const stateTone=state==='observed'?'is-positive':state==='carried_forward'?'is-warn':'is-risk';
      const familyLabels={yahoo:'Yahoo',sec_edgar:'SEC EDGAR',esef:'ESEF'};
      const families=Array.isArray(p.independent_fundamental_source_families)?p.independent_fundamental_source_families:[];
      const sourceText=families.length?families.map(x=>familyLabels[text(x)]||text(x)).filter(Boolean).join(' + '):'Sem fonte fundamental independente identificada';
      const reasons=Array.isArray(s.confidence_reasons)?s.confidence_reasons.filter(Boolean).slice(0,4):[];
      const ageLabel=age==null?'Sem data oficial comparável':age<=180?`${Math.round(age)} dias · recente`:age<=365?`${Math.round(age)} dias`:`${Math.round(age)} dias · atenção`;
      const sourceLabel=independent==null?'—':`${Math.round(independent)} ${Math.round(independent)===1?'fonte':'fontes'}`;
      const confidenceLabel=confidence==null?'—':`${Math.round(confidence)}/100`;
      const coverageLabel=coverage==null?'—':`${Math.round(coverage)}%`;
      return `<div class="market-detail-card market-evidence-quality"><div class="market-perspective-head"><div><small>QUALIDADE DA EVIDÊNCIA</small><h4>${escapeHtml(sourceText)}</h4></div><span class="market-data-age ${stateTone}">${escapeHtml(stateLabel)}</span></div><div class="market-mini-grid"><div><small>Fontes fundamentais</small><strong>${escapeHtml(sourceLabel)}</strong></div><div><small>Confiança dos dados</small><strong>${escapeHtml(confidenceLabel)}</strong></div><div><small>Cobertura</small><strong>${escapeHtml(coverageLabel)}</strong></div><div><small>Atualidade fundamental</small><strong>${escapeHtml(ageLabel)}</strong></div></div>${reasons.length?`<p class="market-case-note">${reasons.map(escapeHtml).join(' · ')}</p>`:''}<p class="market-case-note">Analyst, insiders e divulgações políticas são domínios complementares e não contam como segunda confirmação independente dos fundamentais. Este painel descreve a evidência; não altera o Score Vestra.</p></div>`;
    }

    function catalystPanel(s={}){
      const evidence=evidencePanel(s);
      const events=Array.isArray(s.catalyst_events)?s.catalyst_events.slice(0,5):[];
      if(!events.length) return evidence;
      const icon=e=>e.tone==='risk'?'!':e.tone==='positive'?'↗':e.tone==='event'?'◷':'•';
      const tone=e=>e.tone==='risk'?'down':e.tone==='positive'?'up':e.tone==='event'?'event':'neutral';
      const when=e=>e.date?formatShortDate(e.date):(e.window?e.window:'Sem data');
      const next=s.catalyst_next_date?`Próximo · ${formatShortDate(s.catalyst_next_date)}`:`${events.length} sinais`;
      const catalyst=`<div class="market-detail-card"><div class="market-perspective-head"><div><small>CATALYSTS & RISKS</small><h4>${escapeHtml(s.catalyst_summary||'Eventos a acompanhar')}</h4></div><span class="market-data-age">${escapeHtml(next)}</span></div><div class="market-change-list">${events.map(e=>`<div class="market-change-item market-change-item--${tone(e)}"><b>${icon(e)}</b><span><strong>${escapeHtml(e.label||'Evento')}</strong><small style="display:block;margin-top:2px">${escapeHtml(when(e))}${e.evidence?` · ${escapeHtml(e.evidence)}`:''}${e.source?` · ${escapeHtml(e.source)}`:''}</small></span></div>`).join('')}</div></div>`;
      return `${evidence}${catalyst}`;
    }

    function recoveryPanel(s={}){
      const status=text(s.recovery_status), label=text(s.recovery_label), score=number(s.recovery_score);
      if(!status || status==='insufficient') return '';
      const r20=number(s.recovery_return_20d_pct), r60=number(s.recovery_return_60d_pct);
      const reasons=Array.isArray(s.recovery_reasons)?s.recovery_reasons:[];
      const tone=(status==='confirmed'||status==='recovering')?'is-positive':(status==='failed'||status==='bounce_only')?'is-risk':'';
      return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>RECOVERY CONFIRMATION</small><h4>${escapeHtml(label||'Sem confirmação')}</h4></div><span class="market-data-age ${tone}">${score==null?'—':Math.round(score)+'/100'}</span></div><div class="market-mini-grid"><div><small>Preço 20d</small><strong>${r20==null?'—':`${r20>0?'+':''}${r20.toFixed(1)}%`}</strong></div><div><small>Preço 60d</small><strong>${r60==null?'—':`${r60>0?'+':''}${r60.toFixed(1)}%`}</strong></div><div><small>Confirmação preço</small><strong>${number(s.recovery_price_score)==null?'—':Math.round(number(s.recovery_price_score))+'/100'}</strong></div><div><small>Confirmação fundamental</small><strong>${number(s.recovery_fundamental_score)==null?'—':Math.round(number(s.recovery_fundamental_score))+'/100'}</strong></div></div>${reasons.length?`<p class="market-case-note">${reasons.slice(0,4).map(escapeHtml).join(' · ')}</p>`:''}<p class="market-case-note">Confirmação de recuperação combina preço recente e melhoria fundamental; não é sinal de entrada nem altera o Score Vestra.</p></div>`;
    }

    function drawdownPanel(s={}){
      const items=Array.isArray(s.drawdown_diagnosis)?s.drawdown_diagnosis:[];
      if(!items.length || text(s.drawdown_diagnosis_status)==='not_material') return '';
      const trendLabel={improving:'a melhorar',deteriorating:'a piorar',stable:'estável'};
      const trendTone={improving:'is-positive',deteriorating:'is-risk',stable:''};
      const primary=items[0]||{};
      const mixed=text(s.drawdown_diagnosis_status)==='mixed';
      const title=mixed?'Queda com causas mistas':(s.drawdown_primary_label||primary.label||'Causa não identificada');
      const dd=number(s.drawdown_from_high_pct);
      return `<div class="market-detail-card market-drawdown-panel"><div class="market-perspective-head"><div><small>PORQUE CAIU? · DIAGNÓSTICO</small><h4>${escapeHtml(title)}</h4></div><span class="market-data-age">${dd==null?'drawdown':`${dd.toFixed(0)}% vs máximo 52s`}</span></div><p class="market-case-note">Diagnóstico por evidência disponível; identifica drivers prováveis, não prova causalidade.</p>${text(s.sector_relative_drawdown_label)?`<p class="market-case-note"><strong>${escapeHtml(s.sector_relative_drawdown_label)}</strong>${number(s.sector_relative_return_1y_pct)!=null?` · ${number(s.sector_relative_return_1y_pct)>0?'+':''}${number(s.sector_relative_return_1y_pct).toFixed(1)} pp vs mediana do setor · ${number(s.sector_relative_peer_count)||0} pares`:''}</p>`:''}<div class="market-drawdown-drivers">${items.slice(0,4).map((d,i)=>`<div class="market-drawdown-driver ${i===0?'is-primary':''}"><div><strong>${escapeHtml(d.label||d.key||'Driver')}</strong><small>${(d.evidence||[]).slice(0,2).map(escapeHtml).join(' · ')||'Evidência limitada'}</small></div><span><b>${Math.round(number(d.strength)||0)}</b><em class="${trendTone[text(d.trend)]||''}">${escapeHtml(trendLabel[text(d.trend)]||'estável')}</em></span></div>`).join('')}</div></div>`;
    }

    return Object.freeze({evidencePanel,catalystPanel,recoveryPanel,drawdownPanel});
  }

  window.VestraMarketDossierSignals = Object.freeze({create,version:'1.0'});
})();
