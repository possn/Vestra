const fs = require('fs');
const assert = require('assert');

const payload = JSON.parse(fs.readFileSync('data/macro-events.json', 'utf8'));
assert.strictEqual(payload.schema_version, 1);
assert(Array.isArray(payload.events) && payload.events.length >= 30, 'macro snapshot must contain a useful forward calendar');
for (const key of ['fed','bls','bea','ecb','census']) assert(payload.sources?.[key], `missing source ${key}`);

const byKey = new Map(payload.events.map(event => [`${event.date}:${event.short_title}`, event]));
assert(byKey.has('2026-09-10:PPI EUA'));
assert(byKey.has('2026-09-11:CPI EUA'));
assert(byKey.has('2026-09-15:FOMC'));
assert(byKey.has('2026-09-09:BCE'));
assert(byKey.has('2026-09-16:Retail Sales'));
assert(byKey.has('2026-09-30:PCE EUA'));
assert(byKey.has('2026-10-02:NFP EUA'));
assert(byKey.has('2026-09-30:GDP EUA'));

for (const event of payload.events) {
  assert(/^\d{4}-\d{2}-\d{2}$/.test(event.date), `invalid date ${event.date}`);
  assert(['high','critical'].includes(event.importance), `unexpected importance ${event.importance}`);
  assert(event.title && event.short_title && event.category && event.region && event.source, `incomplete macro event ${event.date}`);
  if (event.date_end) assert(event.date_end >= event.date, `date_end before date for ${event.short_title}`);
}

console.log('macro events data contract: ok');
