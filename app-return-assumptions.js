/* Vestra Return Assumptions v1.0 — pure defaults and settings normalization. */
(() => {
  'use strict';

  const PASSIVE_DEFAULTS = Object.freeze({
    'acoes/etfs':1.8,
    'fundos':1.2,
    'ppr':0.4,
    'imobiliario':4,
    'ouro':0,
    'prata':0,
    'cripto':0,
    'liquidez':0,
    'depositos':2,
    'obrigacoes':3,
    'outros':0,
  });

  const APPRECIATION_DEFAULTS = Object.freeze({
    'acoes/etfs':6,
    'fundos':4,
    'ppr':3.5,
    'imobiliario':2,
    'ouro':2,
    'prata':1.5,
    'cripto':0,
    'liquidez':0,
    'depositos':0,
    'obrigacoes':0,
    'outros':0,
  });

  const DEFAULT_RETURN_SETTINGS = Object.freeze({
    classPassivePct:Object.freeze({...PASSIVE_DEFAULTS}),
    classAppreciationPct:Object.freeze({...APPRECIATION_DEFAULTS}),
    preferTWR:true,
    twrMinYears:0.5,
  });

  const RETURN_CLASS_DEFINITIONS = Object.freeze([
    {key:'acoes/etfs',label:'Ações / ETFs',hint:'dividendos + crescimento do mercado',passiveHint:'dividendo esperado',appreciationHint:'crescimento esperado'},
    {key:'fundos',label:'Fundos',hint:'fundos multi-activos / UCITS',passiveHint:'distribuição esperada',appreciationHint:'crescimento esperado'},
    {key:'ppr',label:'PPR',hint:'fundos PPR / seguros PPR',passiveHint:'distribuição / participação',appreciationHint:'crescimento esperado'},
    {key:'imobiliario',label:'Imobiliário',hint:'renda + valorização do activo',passiveHint:'yield renda',appreciationHint:'valorização do imóvel'},
    {key:'ouro',label:'Ouro',hint:'activo sem yield natural',passiveHint:'yield projectado',appreciationHint:'valorização esperada'},
    {key:'prata',label:'Prata',hint:'activo sem yield natural',passiveHint:'yield projectado',appreciationHint:'valorização esperada'},
    {key:'cripto',label:'Cripto',hint:'staking separado da apreciação',passiveHint:'staking / yield',appreciationHint:'apreciação esperada'},
    {key:'liquidez',label:'Liquidez',hint:'contas / saldo à ordem',passiveHint:'juro esperado',appreciationHint:'valorização'},
    {key:'depositos',label:'Depósitos',hint:'juro contratual',passiveHint:'juro esperado',appreciationHint:'valorização'},
    {key:'obrigacoes',label:'Obrigações',hint:'cupão separado do capital',passiveHint:'cupão / carry',appreciationHint:'pull-to-par / preço'},
    {key:'outros',label:'Outros',hint:'fallback residual',passiveHint:'rendimento base',appreciationHint:'valorização'},
  ].map(Object.freeze));

  function normalizeReturnSettings(raw, parseNumber=Number) {
    const s=(raw&&typeof raw==='object')?raw:{};
    const parsed=parseNumber(s.twrMinYears);
    return {
      classPassivePct:{...PASSIVE_DEFAULTS,...(s.classPassivePct||{})},
      classAppreciationPct:{...APPRECIATION_DEFAULTS,...(s.classAppreciationPct||{})},
      preferTWR:s.preferTWR!==false,
      twrMinYears:Number.isFinite(parsed)&&parsed>0?parsed:DEFAULT_RETURN_SETTINGS.twrMinYears,
    };
  }

  function getReturnClassDefinitions(){
    return RETURN_CLASS_DEFINITIONS.map(x=>({...x}));
  }

  window.VestraReturnAssumptions=Object.freeze({
    version:'1.0',
    PASSIVE_DEFAULTS,
    APPRECIATION_DEFAULTS,
    DEFAULT_RETURN_SETTINGS,
    RETURN_CLASS_DEFINITIONS,
    normalizeReturnSettings,
    getReturnClassDefinitions,
  });
})();
