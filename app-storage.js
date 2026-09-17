/* Vestra persistence layer v1.3 — IndexedDB with bounded localStorage fallback and read-failure write guard. */
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

  function idbAvailable(){ return typeof indexedDB !== 'undefined' && indexedDB; }

  function idbFailure(message, cause){
    const error = new Error(message);
    if (cause !== undefined) error.cause = cause;
    return error;
  }

  function markStateReadTrusted(){
    _stateReadAttempted = true;
    _stateReadTrusted = true;
    _stateReadFailure = '';
  }

  function blockStateWrites(error){
    _stateReadAttempted = true;
    _stateReadTrusted = false;
    _stateReadFailure = String(error?.message || error || 'storage read failed');
  }

  function persistenceStatus(){
    return Object.freeze({
      readAttempted: _stateReadAttempted,
      readTrusted: _stateReadTrusted,
      writeBlocked: !_stateReadTrusted,
      readFailure: _stateReadFailure,
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
    if (idbAvailable()) {
      try {
        const value = await idbGet(DB_KEY);
        markStateReadTrusted();
        if (value) return value;
        const fallback = localStorageGet();
        if (fallback.ok && fallback.value) return fallback.value;
        return null;
      } catch (error) {
        const fallback = localStorageGet();
        if (fallback.ok && fallback.value) {
          markStateReadTrusted();
          return fallback.value;
        }
        blockStateWrites(error);
        return null;
      }
    }

    const fallback = localStorageGet();
    if (fallback.ok) {
      markStateReadTrusted();
      return fallback.value;
    }
    blockStateWrites(fallback.error || idbFailure('localStorage read failed'));
    return null;
  }

  async function storageSet(raw){
    if (!_stateReadTrusted) {
      console.error('[VestraStorage] State write blocked because the current session did not complete a trusted state read.', _stateReadFailure || 'read not completed');
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
    markStateReadTrusted();
  }

  const api = Object.freeze({
    STORAGE_KEY, DB_NAME, DB_STORE, DB_KEY, DB_BACKUP_KEY, IDB_OPEN_TIMEOUT_MS, IDB_TRANSACTION_TIMEOUT_MS,
    idbAvailable, idbOpen, idbGet, idbSet, idbDel,
    requestPersistentStorage, storageGet, storageSet, storageGetBackup, storageClear, persistenceStatus,
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
