/* Vestra persistence layer v1.4 — IndexedDB with backups, recovery and read-failure write guard. */
(() => {
  'use strict';

  const STORAGE_KEY = 'PF_STATE_V6';
  const DB_NAME = 'pf_v6';
  const DB_STORE = 'kv';
  const DB_KEY = 'state';
  const DB_BACKUP_KEY = 'state_backup';
  const IDB_OPEN_TIMEOUT_MS = 1500;
  const IDB_TRANSACTION_TIMEOUT_MS = 1500;

  let _stateReadAttempted = false;
  let _stateReadTrusted = false;
  let _stateReadFailure = '';
  let _recoverySource = '';

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

  function markStateReadTrusted(source = ''){
    _stateReadAttempted = true;
    _stateReadTrusted = true;
    _stateReadFailure = '';
    _recoverySource = source;
  }

  function blockStateWrites(error){
    _stateReadAttempted = true;
    _stateReadTrusted = false;
    _stateReadFailure = String(error?.message || error || 'storage read failed');
    _recoverySource = '';
  }

  function persistenceStatus(){
    return Object.freeze({
      readAttempted: _stateReadAttempted,
      readTrusted: _stateReadTrusted,
      writeBlocked: _stateReadAttempted && !_stateReadTrusted,
      readFailure: _stateReadFailure,
      recoverySource: _recoverySource,
    });
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

  function localStorageGet(){
    try { return { ok: true, value: localStorage.getItem(STORAGE_KEY) }; }
    catch (error) { return { ok: false, value: null, error }; }
  }

  async function storageGet(){
    let primary = null;
    let backup = null;
    let idbError = null;

    if (idbAvailable()) {
      try {
        primary = await idbGet(DB_KEY);
        try { backup = await idbGet(DB_BACKUP_KEY); } catch (_) {}
      } catch (error) {
        idbError = error;
      }
    }

    const fallback = localStorageGet();
    const localValue = fallback.ok ? fallback.value : null;
    const primaryScore = stateRichness(primary);
    const backupScore = stateRichness(backup);
    const localScore = stateRichness(localValue);

    // Recovery is conservative: a valid non-empty primary is always authoritative.
    // Preserved copies are considered only when primary is absent/empty.
    if (primaryScore <= 0) {
      const recoveryCandidates = [
        { source: 'indexeddb-backup', value: backup, score: backupScore },
        { source: 'localstorage', value: localValue, score: localScore },
      ].filter(candidate => candidate.value && candidate.score > 0)
        .sort((a, b) => b.score - a.score);
      if (recoveryCandidates.length) {
        const recovered = recoveryCandidates[0];
        markStateReadTrusted(recovered.source);
        return recovered.value;
      }
    }

    if (primary) {
      markStateReadTrusted('indexeddb');
      return primary;
    }
    if (backup) {
      markStateReadTrusted('indexeddb-backup');
      return backup;
    }
    if (localValue) {
      markStateReadTrusted('localstorage');
      return localValue;
    }

    if (idbError) {
      blockStateWrites(idbError);
      return null;
    }
    if (!fallback.ok) {
      blockStateWrites(fallback.error || idbFailure('localStorage read failed'));
      return null;
    }

    markStateReadTrusted('empty');
    return null;
  }

  async function storageSet(raw){
    if (_stateReadAttempted && !_stateReadTrusted) {
      console.error('[VestraStorage] State write blocked because the current session had a failed state read.', _stateReadFailure || 'read failed');
      return false;
    }

    if (idbAvailable()) {
      try {
        let previous = null;
        try { previous = await idbGet(DB_KEY); } catch (_) {}
        if (previous && previous !== raw) {
          try { await idbSet(DB_BACKUP_KEY, previous); } catch (_) {}
        }
        await idbSet(DB_KEY, raw);
        return true;
      } catch (_) {}
    }
    try { localStorage.setItem(STORAGE_KEY, raw); return true; } catch (_) { return false; }
  }

  async function storageGetBackup(){
    if (!idbAvailable()) return null;
    try { return await idbGet(DB_BACKUP_KEY) || null; } catch (_) { return null; }
  }

  async function storageClear(){
    if (idbAvailable()) {
      try { await idbDel(DB_KEY); } catch (_) {}
    }
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
    markStateReadTrusted('cleared');
  }

  const api = Object.freeze({
    STORAGE_KEY, DB_NAME, DB_STORE, DB_KEY, DB_BACKUP_KEY, IDB_OPEN_TIMEOUT_MS, IDB_TRANSACTION_TIMEOUT_MS,
    idbAvailable, idbOpen, idbGet, idbSet, idbDel, stateRichness,
    requestPersistentStorage, storageGet, storageSet, storageGetBackup, storageClear, persistenceStatus,
    version: '1.4',
  });

  window.VestraStorage = api;
  Object.assign(window, {
    requestPersistentStorage,
    storageGet,
    storageSet,
    storageGetBackup,
    storageClear,
  });
})();