const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'politicians.js'), 'utf8');
assert.match(source, /\}\)\(\);\s*$/);
const instrumented = source.replace(/\}\)\(\);\s*$/, `
  globalThis.__politicianIdentityTest = {
    set(members, trades) {
      memberDirectory = members.map(x => buildMember(x));
      recentTrades = trades.map(x => normalizeTrade(x));
      enrichMemberCounts();
    },
    members() { return memberDirectory.map(m => ({key:m.key,name:m.name,chamber:m.chamber,count:m.count,buys:m.buys,sells:m.sells})); },
    trades(m) { return rowsForMember(m).map(x => x.ticker); },
    member(key) { return memberDirectory.find(m => m.key === key); }
  };
})();`);
const sandbox = { document: { readyState: 'loading', addEventListener() {} }, console };
vm.createContext(sandbox);
vm.runInContext(instrumented, sandbox, {filename:'politicians.js'});
const app = sandbox.__politicianIdentityTest;
assert.ok(app);
app.set([
  {key:'congress:house-a',name:'Alex Example',chamber:'House'},
  {key:'congress:senate-a',name:'Alex Example',chamber:'Senate'}
], [
  {ticker:'AAA',member:'Alex Example',member_key:'congress:house-a',chamber:'House',type:'purchase'},
  {ticker:'BBB',member:'Alex Example',member_key:'congress:senate-a',chamber:'Senate',type:'sale'},
  {ticker:'CCC',member:'Alex Example',chamber:'Congress',type:'purchase'}
]);
const house=app.member('congress:house-a');
const senate=app.member('congress:senate-a');
assert.equal(house.count,1);
assert.equal(house.buys,1);
assert.equal(house.sells,0);
assert.equal(senate.count,1);
assert.equal(senate.buys,0);
assert.equal(senate.sells,1);
assert.deepEqual(Array.from(app.trades(house)),['AAA']);
assert.deepEqual(Array.from(app.trades(senate)),['BBB']);
assert.equal(app.members().length,2,'unkeyed ambiguous event must not invent a new person');
console.log('politician member identity regression: ok');
