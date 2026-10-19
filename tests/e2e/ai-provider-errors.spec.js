const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../app.js'), 'utf8');
const start = source.indexOf('function classifyAIProviderError(');
const end = source.indexOf('\nasync function runAIAnalysis()', start);
if (start < 0 || end < 0) throw new Error('AI provider adapter missing');
const code = source.slice(start, end);
function adapter(fetch) {
  const sandbox = { fetch };
  vm.runInNewContext(code + '\nthis.call = callAIProvider;', sandbox);
  return sandbox.call;
}
const groq = { format: 'openai', model: 'llama-3.3-70b-versatile', url: 'https://mock.test/groq' };
const claude = { format: 'anthropic', model: 'claude-sonnet-4-6', url: 'https://mock.test/claude' };

test('Anthropic uses active Sonnet model, not retired Sonnet 4', () => {
  expect(source).toContain('model: "claude-sonnet-4-6"');
  expect(source).not.toContain('model: "claude-sonnet-4-20250514"');
});

test('AI provider HTTP failures classify credentials, credits, model and rate limits', async () => {
  for (const [status, pattern] of [
    [401, /chave API|Chave API/i],
    [402, /créditos/i],
    [403, /acesso/i],
    [404, /modelo/i],
    [429, /limite/i],
    [503, /indisponível/i]
  ]) {
    const call = adapter(async () => ({ok:false,status,json:async()=>({error:{message:'internal unsafe details'}})}));
    await expect(call(claude,'secret','system','question')).rejects.toThrow(pattern);
    await expect(call(groq,'secret','system','question')).rejects.toThrow(pattern);
    await expect(call(claude,'secret','system','question')).rejects.not.toThrow(/internal unsafe details|secret/);
  }
});

test('AI provider network failures and empty replies are explicit', async () => {
  const offline = adapter(async () => {throw new TypeError('Failed to fetch');});
  await expect(offline(claude,'secret','s','u')).rejects.toThrow(/ligação/);
  const empty = adapter(async () => ({ok:true,json:async()=>({content:[]})}));
  await expect(empty(claude,'secret','s','u')).rejects.toThrow(/resposta vazia/);
});

test('AI provider decodes real success shapes for both APIs', async () => {
  const a = adapter(async () => ({ok:true,json:async()=>({content:[{type:'text',text:'Primeira'},{type:'text',text:'Segunda'}]})}));
  expect(await a(claude,'secret','s','u')).toBe('Primeira\nSegunda');
  const g = adapter(async () => ({ok:true,json:async()=>({choices:[{message:{content:'Resposta Groq'}}]})}));
  expect(await g(groq,'secret','s','u')).toBe('Resposta Groq');
});
