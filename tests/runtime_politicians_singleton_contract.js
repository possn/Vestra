const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'..','politicians.js'),'utf8');
let domBootListeners=0;
const sandbox={
  document:{readyState:'loading',addEventListener(type,handler){
    if(type==='DOMContentLoaded')domBootListeners+=1;
  }},
  console,
};
vm.createContext(sandbox);
vm.runInContext(source,sandbox,{filename:'politicians-first.js'});
vm.runInContext(source,sandbox,{filename:'politicians-second.js'});
assert.equal(domBootListeners,1,
  'duplicate script must not create two politician modules and competing search listeners');
assert.equal(sandbox.__vestraPoliticiansSingletonV1,true);
console.log('politicians double-injection singleton: ok');
