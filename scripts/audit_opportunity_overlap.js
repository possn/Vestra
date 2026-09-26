const fs = require('fs');
const vm = require('vm');

const payload = JSON.parse(fs.readFileSync('data/stocks-index.json', 'utf8'));
const stocks = Array.isArray(payload?.stocks) ? payload.stocks : [];

global.window = {
  VestraMarketStaticUniverse: { getStocks: () => stocks },
};
global.document = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
  querySelectorAll() { return []; },
  head: { appendChild() {} },
  createElement() { return { addEventListener() {}, removeEventListener() {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {} } }; },
};
global.MutationObserver = class { observe() {} };
global.requestAnimationFrame = fn => fn();
global.CustomEvent = class {};

const source = fs.readFileSync('market-opportunities.js', 'utf8');
vm.runInThisContext(source, { filename: 'market-opportunities.js' });
const api = global.window.VestraMarketOpportunities;
if (!api) throw new Error('VestraMarketOpportunities API unavailable');
if (typeof api.rankLens !== 'function') throw new Error('canonical rankLens API unavailable');

const lenses = ['all', 'low52', 'emerging', 'recovery', 'value'];
const topN = Number(process.argv[2] || 12);
const ranked = {};
for (const lens of lenses) {
  ranked[lens] = api.rankLens(stocks, lens, { limit: topN })
    .map(stock => String(stock?.ticker || '').trim())
    .filter(Boolean);
}

function shortlistDiagnostics(rows) {
  const counts = key => rows.reduce((acc, stock) => {
    const value = String(stock?.[key] || 'Unknown').trim() || 'Unknown';
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
  const maxShare = countsObj => {
    const values = Object.values(countsObj);
    return rows.length && values.length ? Number((Math.max(...values) / rows.length * 100).toFixed(1)) : 0;
  };
  const sectors = counts('sector');
  const industries = counts('industry');
  const drivers = rows.reduce((acc, stock) => {
    const sleeves = api.sleeveScores?.(stock) || {};
    const entries = Object.entries(sleeves).filter(([, value]) => Number.isFinite(Number(value)));
    const driver = entries.sort((a, b) => Number(b[1]) - Number(a[1]))[0]?.[0] || 'unknown';
    acc[driver] = (acc[driver] || 0) + 1;
    return acc;
  }, {});
  const sleeveValues = rows.map(stock => api.sleeveScores?.(stock) || {});
  const sleeveSummary = Object.fromEntries(['strength', 'asymmetry', 'inflection'].map(key => {
    const values = sleeveValues.map(x => Number(x[key])).filter(Number.isFinite).sort((a, b) => a - b);
    const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    const median = values.length ? (values.length % 2 ? values[(values.length - 1) / 2] : (values[values.length / 2 - 1] + values[values.length / 2]) / 2) : null;
    return [key, {
      mean: mean == null ? null : Number(mean.toFixed(1)),
      median: median == null ? null : Number(median.toFixed(1)),
      min: values.length ? Number(values[0].toFixed(1)) : null,
      max: values.length ? Number(values[values.length - 1].toFixed(1)) : null,
    }];
  }));
  const archetypes = Object.fromEntries(
    ['low52', 'emerging', 'recovery', 'value'].map(lens => [
      lens, rows.filter(stock => api.lensEligible(stock, lens)).length,
    ])
  );
  return {
    sector_counts: sectors,
    industry_counts: industries,
    dominant_sleeve_counts: drivers,
    sleeve_score_summary: sleeveSummary,
    archetype_counts: archetypes,
    max_sector_share_pct: maxShare(sectors),
    max_industry_share_pct: maxShare(industries),
    distinct_sectors: Object.keys(sectors).length,
    distinct_industries: Object.keys(industries).length,
    distinct_dominant_sleeves: Object.keys(drivers).filter(x => x !== 'unknown').length,
  };
}

function overlap(a, b) {
  const A = new Set(ranked[a]);
  const B = new Set(ranked[b]);
  const shared = [...A].filter(x => B.has(x));
  const union = new Set([...A, ...B]);
  return {
    shared_count: shared.length,
    overlap_of_top_n_pct: topN ? Number((shared.length / topN * 100).toFixed(1)) : 0,
    jaccard_pct: union.size ? Number((shared.length / union.size * 100).toFixed(1)) : 0,
    shared,
  };
}

const pairs = {};
for (let i = 0; i < lenses.length; i += 1) {
  for (let j = i + 1; j < lenses.length; j += 1) {
    pairs[`${lenses[i]}__${lenses[j]}`] = overlap(lenses[i], lenses[j]);
  }
}

const appearances = {};
for (const lens of lenses) {
  for (const ticker of ranked[lens]) appearances[ticker] = (appearances[ticker] || 0) + 1;
}
const repeated = Object.entries(appearances)
  .filter(([, count]) => count >= 3)
  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  .map(([ticker, lens_count]) => ({ ticker, lens_count }));

const eligibleCounts = Object.fromEntries(lenses.map(lens => [lens, stocks.filter(stock => api.lensEligible(stock, lens)).length]));
const allRows = api.rankLens(stocks, 'all', { limit: topN });
const diagnostics = shortlistDiagnostics(allRows);
const scored = stocks
  .filter(stock => Number.isFinite(Number(stock?.score)))
  .slice()
  .sort((a, b) => Number(b.score) - Number(a.score));
const topScoreNames = scored.slice(0, topN).map(stock => String(stock?.ticker || '').trim()).filter(Boolean);
const scoreDecileCount = Math.max(1, Math.ceil(scored.length * 0.10));
const topScoreDecile = new Set(scored.slice(0, scoreDecileCount).map(stock => String(stock?.ticker || '').trim()).filter(Boolean));
const discoveryNames = ranked.all;
const topScoreSet = new Set(topScoreNames);
const overlapTopScore = discoveryNames.filter(ticker => topScoreSet.has(ticker));
const overlapTopDecile = discoveryNames.filter(ticker => topScoreDecile.has(ticker));
const novelty = {
  top_score_ranked: topScoreNames,
  overlap_with_top_score_count: overlapTopScore.length,
  overlap_with_top_score_pct: topN ? Number((overlapTopScore.length / topN * 100).toFixed(1)) : 0,
  overlap_with_top_score: overlapTopScore,
  top_score_decile_size: scoreDecileCount,
  discovery_in_top_score_decile_count: overlapTopDecile.length,
  discovery_in_top_score_decile_pct: topN ? Number((overlapTopDecile.length / topN * 100).toFixed(1)) : 0,
  discovery_in_top_score_decile: overlapTopDecile,
  discovery_novel_count: discoveryNames.filter(ticker => !topScoreDecile.has(ticker)).length,
};
const report = {
  generated_at: payload?.generated_at || null,
  universe_count: stocks.length,
  top_n: topN,
  eligible_counts: eligibleCounts,
  ranked,
  pairs,
  repeated_in_3plus_lenses: repeated,
  general_shortlist_diagnostics: diagnostics,
  discovery_novelty_vs_score: novelty,
};
console.log(JSON.stringify(report, null, 2));
