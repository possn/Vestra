from pathlib import Path

app_path = Path('app.js')
idx_path = Path('index.html')
module_path = Path('app-broker-parsing-core.js')

app = app_path.read_text(encoding='utf-8')
idx = idx_path.read_text(encoding='utf-8')

# Segment 1: primitive identity normalization. Leave stateful repair function in app.js.
s1_start = app.find('function normalizeISIN(v) {')
s1_end_marker = '// v3.3 — Broker identity authority generated from the user\'s original'
s1_end = app.find(s1_end_marker, s1_start)
if s1_start < 0 or s1_end < 0:
    raise RuntimeError('Stage10 segment 1 markers not found')
seg1 = app[s1_start:s1_end].rstrip()

# Segment 2: Yahoo/venue identity inference, from static overrides through makeBrokerSecurityKey.
s2_start = app.find('const KNOWN_BROKER_YAHOO_OVERRIDES = {')
s2_end_marker = 'function detectBrokerRowsFormat(rows) {'
s2_end = app.find(s2_end_marker, s2_start)
if s2_start < 0 or s2_end < 0:
    raise RuntimeError('Stage10 segment 2 markers not found')
seg2 = app[s2_start:s2_end].rstrip()

# Segment 3: format/action/key helpers. Stop before FX-dependent row parsing.
s3_start = s2_end
s3_end_marker = 'function estimateEURFactorFromRow(r, grossLocal, totalEUR, ccy) {'
s3_end = app.find(s3_end_marker, s3_start)
if s3_start < 0 or s3_end < 0:
    raise RuntimeError('Stage10 segment 3 markers not found')
seg3 = app[s3_start:s3_end].rstrip()

required = [
    'function normalizeISIN(', 'function normalizeSecurityNameKey(',
    'const KNOWN_BROKER_YAHOO_OVERRIDES = {', 'function getKnownBrokerYahooOverride(',
    'function canonicalBrokerTickerBase(', 'function inferPreferredVenueTicker(',
    'function venueFromIsinAndCurrency(', 'function inferYahooTickerFromIdentity(',
    'function sameSecurityName(', 'function sameBrokerSecurityIdentity(',
    'function makeBrokerSecurityKey(', 'function detectBrokerRowsFormat(',
    'function detectBrokerTextFormat(', 'function normalizeBrokerNameFromFile(',
    'function normalizeBrokerAction(', 'function brokerPositionClassFromTicker(',
    'function brokerEventKey(', 'function brokerPositionKey('
]
combined = '\n\n'.join([seg1, seg2, seg3])
for token in required:
    if token not in combined:
        raise RuntimeError(f'Missing expected broker parsing token: {token}')

module = """/* Vestra broker parsing core v1.0 — pure identity, format and key helpers. */
(() => {
  'use strict';

  const { normStr, parseNum } = window.VestraUtils || {};
  const { ISIN_YAHOO_MAP } = window.VestraAssetIdentity || {};
  if (typeof normStr !== 'function' || typeof parseNum !== 'function') {
    throw new Error('VestraUtils não foi carregado antes de app-broker-parsing-core.js');
  }
  if (!ISIN_YAHOO_MAP || typeof ISIN_YAHOO_MAP !== 'object') {
    throw new Error('VestraAssetIdentity não foi carregado antes de app-broker-parsing-core.js');
  }

""" + combined + """

  window.VestraBrokerParsingCore = Object.freeze({
    normalizeISIN,
    normalizeSecurityNameKey,
    KNOWN_BROKER_YAHOO_OVERRIDES,
    getKnownBrokerYahooOverride,
    canonicalBrokerTickerBase,
    inferPreferredVenueTicker,
    venueFromIsinAndCurrency,
    inferYahooTickerFromIdentity,
    sameSecurityName,
    sameBrokerSecurityIdentity,
    makeBrokerSecurityKey,
    detectBrokerRowsFormat,
    detectBrokerTextFormat,
    normalizeBrokerNameFromFile,
    normalizeBrokerAction,
    brokerPositionClassFromTicker,
    brokerEventKey,
    brokerPositionKey,
  });
})();
"""
module_path.write_text(module, encoding='utf-8')

bridge = """/* ─── BROKER PARSING CORE — moved to app-broker-parsing-core.js ─── */
const {
  normalizeISIN,
  normalizeSecurityNameKey,
  KNOWN_BROKER_YAHOO_OVERRIDES,
  getKnownBrokerYahooOverride,
  canonicalBrokerTickerBase,
  inferPreferredVenueTicker,
  venueFromIsinAndCurrency,
  inferYahooTickerFromIdentity,
  sameSecurityName,
  sameBrokerSecurityIdentity,
  makeBrokerSecurityKey,
  detectBrokerRowsFormat,
  detectBrokerTextFormat,
  normalizeBrokerNameFromFile,
  normalizeBrokerAction,
  brokerPositionClassFromTicker,
  brokerEventKey,
  brokerPositionKey,
} = window.VestraBrokerParsingCore || {};
if ([normalizeISIN, normalizeSecurityNameKey, getKnownBrokerYahooOverride, canonicalBrokerTickerBase,
     inferPreferredVenueTicker, venueFromIsinAndCurrency, inferYahooTickerFromIdentity, sameSecurityName,
     sameBrokerSecurityIdentity, makeBrokerSecurityKey, detectBrokerRowsFormat, detectBrokerTextFormat,
     normalizeBrokerNameFromFile, normalizeBrokerAction, brokerPositionClassFromTicker, brokerEventKey,
     brokerPositionKey].some(fn => typeof fn !== 'function') || !KNOWN_BROKER_YAHOO_OVERRIDES) {
  throw new Error('VestraBrokerParsingCore não foi carregado antes de app.js');
}

"""

# Apply from back to front to preserve offsets.
app2 = app[:s3_start] + app[s3_end:]
app2 = app2[:s2_start] + app2[s2_end:]
# segment 1 offsets precede segment 2 and remain valid after later removals
app2 = app2[:s1_start] + bridge + app2[s1_end:]

for token in required:
    if token in app2:
        raise RuntimeError(f'Broker parsing implementation remained in app.js: {token}')
if 'function repairBrokerIdentitiesFromHistory()' not in app2:
    raise RuntimeError('Stateful broker identity repair was accidentally removed')

script = '<script defer="" src="app-broker-parsing-core.js?v=1.0"></script>'
if script not in idx:
    anchor = '<script defer="" src="app-broker-identity-data.js?v=1.0"></script>'
    if anchor not in idx:
        raise RuntimeError('Broker identity script anchor missing from index.html')
    idx = idx.replace(anchor, anchor + '\n  ' + script, 1)
if idx.index('app-utils.js') > idx.index('app-broker-parsing-core.js'):
    raise RuntimeError('app-utils.js must load before broker parsing core')
if idx.index('app-asset-identity.js') > idx.index('app-broker-parsing-core.js'):
    raise RuntimeError('app-asset-identity.js must load before broker parsing core')
if idx.index('app-broker-parsing-core.js') > idx.index('app.js'):
    raise RuntimeError('broker parsing core must load before app.js')

app_path.write_text(app2, encoding='utf-8')
idx_path.write_text(idx, encoding='utf-8')
print(f'app.js reduced by {len(app)-len(app2)} bytes; broker parsing core module {len(module)} bytes')
