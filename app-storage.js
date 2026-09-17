/* Vestra persistence layer v1.3 — IndexedDB with recovery-aware localStorage fallback. */
(() => {
  'use strict';

  const STORAGE_KEY = 'PF_STATE_V6';
  const DB_NAME = 'pf_v6';
  const DB_STORE = 'kv';
  const DB_KEY = 'state';
  const IDB_OPEN_TIMEOUT_MS = 1500;
  const IDB_TRANSACTION_TIMEOUT_MS = 1500;

  function idbAvailable(){ return typeof indexedDB !== 'undefined' && indexedDB; }

  function idbFailure(message, cause){
    const error = new Error(message);
    if (cause !== undefined) error.cause = cause;
    return error;
  }

  function stateRichness(raw){
    if (!raw || typeof raw !== 'string') return -1;
    try {
      const p = JSON.parse(raw);
      if (!p || typeof p !== 'object') return -1;
      const broker = p.brokerData && typeof p.brokerData === 'object' ? p.brokerData : {};
      return [
        p.assets, p.liabilities, p.transactions, p.bankTransactions,
        p.dividends, p.divSummaries, p.history,
        broker.files, broker.events, broker.positions,
      ].reduce((sum, rows) => sum + (Array.isArray(rows) ? rows.length : 0), 0);
    } catch (_) {
      return -1;
    }
  }

  function armTransactionTimeout(tx, settle, label){
    return setTimeout(() => {
      try { tx.abort(); } catch (_) {}
      settle(idbFailure(`IndexedDB ${label} timed out after ${IDB_TRANSACTION_TIMEOUT_MS}ms`));
    }, IDB_TRANSACTION_TIMEOUT_MS);
  }

  let _idbConn = null;
  function idbOpen(){
    if (_idbConn) return _idbConn;

    _idbConn = new Promise((res, rej) => {
      let settled = false;
      let timer = null;

      const rejectOpen = (error) => {
        if (settled) return;
        settled = true;
        if (timer !== null) clearTimeout(timer);
        _idbConn = null;
        rej(error);
      };

      let req;
      try {
        req = indexedDB.open(DB_NAME, 1);
      } catch (error) {
        rejectOpen(error);
        return;
      }

      timer = setTimeout(() => {
        rejectOpen(idbFailure(`IndexedDB open timed out after ${IDB_OPEN_TIMEOUT_MS}ms`));
      }, IDB_OPEN_TIMEOUT_MS);

      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains(DB_STORE)) req.result.createObjectStore(DB_STORE);
      };
      req.onsuccess = () => {
        const db = req.result;
        if (settled) {
          try { db.close(); } catch (_) {}
          return;
        }
        settled = true;
        clearTimeout(timer);
        db.onclose = () => { _idbConn = null; };
        db.onversionchange = () => {
          try { db.close(); } catch (_) {}
          _idbConn = null;
        };
        res(db);
      };
      req.onerror = () => rejectOpen(req.error || idbFailure('IndexedDB open failed'));
      req.onblocked = () => rejectOpen(idbFailure('IndexedDB open blocked by another connection'));
    });
    return _idbConn;
  }

  async function idbGet(key){
    const db = await idbOpen();
    return new Promise((res, rej) => {
      const tx = db.transaction(DB_STORE, 'readonly');
      const req = tx.objectStore(DB_STORE).get(key);
      let settled = false;
      let timer = null;
      const settle = (error, value) => {
        if (settled) return;
        settled = true;
        if (timer !== null) clearTimeout(timer);
        if (error) rej(error); else res(value);
      };
      timer = armTransactionTimeout(tx, error => settle(error), 'read');
      req.onsuccess = () => settle(null, req.result);
      req.onerror = () => settle(req.error || idbFailure('IndexedDB read failed'));
      tx.onerror = () => settle(tx.error || idbFailure('IndexedDB read transaction failed'));
      tx.onabort = () => settle(tx.error || idbFailure('IndexedDB read transaction aborted'));
    });
  }

  async function idbSet(key, value){
    const db = await idbOpen();
    return new Promise((res, rej) => {
      const tx = db.transaction(DB_STORE, 'readwrite');
      let settled = false;
      let timer = null;
      const settle = (error) => {
        if (settled) return;
        settled = true;
        if (timer !== null) clearTimeout(timer);
        if (error) rej(error); else res(true);
      };
      timer = armTransactionTimeout(tx, settle, 'write');
      tx.objectStore(DB_STORE).put(value, key);
      tx.oncomplete = () => settle(null);
      tx.onerror = () => settle(tx.error || idbFailure('IndexedDB write failed'));
      tx.onabort = () => settle(tx.error || idbFailure('IndexedDB write transaction aborted'));
    });
  }

  async function idbDel(key){
    const db = await idbOpen();
    return new Promise(res => {
      const tx = db.transaction(DB_STORE, 'readwrite');
      let settled = false;
      let timer = null;
      const settle = (ok) => {
        if (settled) return;
        settled = true;
        if (timer !== null) clearTimeout(timer);
        res(ok);
      };
      timer = armTransactionTimeout(tx, () => settle(false), 'delete');
      tx.objectStore(DB_STORE).delete(key);
      tx.oncomplete = () => settle(true);
      tx.onerror = () => settle(false);
      tx.onabort = () => settle(false);
    });
  }

  async function requestPersistentStorage(){
    try {
      if (navigator.storage && navigator.storage.persist) await navigator.storage.persist();
    } catch (_) {}
  }

  async function storageGet(){
    let idbValue = null;
    let idbError = null;
    if (idbAvailable()) {
      try { idbValue = await idbGet(DB_KEY); }
      catch (error) { idbError = error; }
    }

    let legacyValue = null;
    try { legacyValue = localStorage.getItem(STORAGE_KEY); } catch (_) {}

    const idbScore = stateRichness(idbValue);
    const legacyScore = stateRichness(legacyValue);

    // Recovery rule: an empty/near-empty IndexedDB state must never hide a richer
    // legacy PF_STATE_V6 copy. Reading the legacy copy is intentionally read-only;
    // it is not written back until the normal app has loaded a trusted state.
    if (legacyValue && legacyScore > 0 && idbScore <= 0) return legacyValue;
    if (idbValue) return idbValue;
    if (legacyValue) return legacyValue;
    if (idbError) throw idbError;
    return null;
  }

  async function storageSet(raw){
    if (idbAvailable()) {
      try { await idbSet(DB_KEY, raw); return; } catch (_) {}
    }
    try { localStorage.setItem(STORAGE_KEY, raw); } catch (_) {}
  }

  async function storageClear(){
    if (idbAvailable()) {
      try { await idbDel(DB_KEY); } catch (_) {}
    }
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
  }

  const api = Object.freeze({
    STORAGE_KEY, DB_NAME, DB_STORE, DB_KEY, IDB_OPEN_TIMEOUT_MS, IDB_TRANSACTION_TIMEOUT_MS,
    idbAvailable, idbOpen, idbGet, idbSet, idbDel, stateRichness,
    requestPersistentStorage, storageGet, storageSet, storageClear,
    version: '1.3',
  });

  window.VestraStorage = api;
  Object.assign(window, {
    requestPersistentStorage,
    storageGet,
    storageSet,
    storageClear,
  });
})();