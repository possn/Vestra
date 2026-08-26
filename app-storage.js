/* Vestra persistence layer v1.0 — IndexedDB with localStorage fallback. */
(() => {
  'use strict';

  const STORAGE_KEY = 'PF_STATE_V6';
  const DB_NAME = 'pf_v6';
  const DB_STORE = 'kv';
  const DB_KEY = 'state';

  function idbAvailable(){ return typeof indexedDB !== 'undefined' && indexedDB; }

  let _idbConn = null;
  function idbOpen(){
    if (_idbConn) return _idbConn;
    _idbConn = new Promise((res, rej) => {
      try {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => {
          if (!req.result.objectStoreNames.contains(DB_STORE)) req.result.createObjectStore(DB_STORE);
        };
        req.onsuccess = () => {
          const db = req.result;
          db.onclose = () => { _idbConn = null; };
          res(db);
        };
        req.onerror = () => { _idbConn = null; rej(req.error); };
      } catch (e) {
        _idbConn = null;
        rej(e);
      }
    });
    return _idbConn;
  }

  async function idbGet(key){
    const db = await idbOpen();
    return new Promise((res, rej) => {
      const tx = db.transaction(DB_STORE, 'readonly');
      const req = tx.objectStore(DB_STORE).get(key);
      req.onsuccess = () => res(req.result);
      req.onerror = () => rej(req.error);
    });
  }

  async function idbSet(key, value){
    const db = await idbOpen();
    return new Promise((res, rej) => {
      const tx = db.transaction(DB_STORE, 'readwrite');
      tx.objectStore(DB_STORE).put(value, key);
      tx.oncomplete = () => res(true);
      tx.onerror = () => rej(tx.error);
    });
  }

  async function idbDel(key){
    const db = await idbOpen();
    return new Promise(res => {
      const tx = db.transaction(DB_STORE, 'readwrite');
      tx.objectStore(DB_STORE).delete(key);
      tx.oncomplete = () => res(true);
      tx.onerror = () => res(false);
    });
  }

  async function requestPersistentStorage(){
    try {
      if (navigator.storage && navigator.storage.persist) await navigator.storage.persist();
    } catch (_) {}
  }

  async function storageGet(){
    if (idbAvailable()) {
      try {
        const v = await idbGet(DB_KEY);
        if (v) return v;
      } catch (_) {}
    }
    try { return localStorage.getItem(STORAGE_KEY); } catch (_) { return null; }
  }

  async function storageSet(raw){
    if (idbAvailable()) {
      try { await idbSet(DB_KEY, raw); return; } catch (_) {}
    }
    try { localStorage.setItem(STORAGE_KEY, raw); } catch (_) {}
  }

  async function storageClear(){
    if (idbAvailable()) await idbDel(DB_KEY);
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
  }

  const api = Object.freeze({
    STORAGE_KEY, DB_NAME, DB_STORE, DB_KEY,
    idbAvailable, idbOpen, idbGet, idbSet, idbDel,
    requestPersistentStorage, storageGet, storageSet, storageClear,
  });

  window.VestraStorage = api;
  Object.assign(window, {
    requestPersistentStorage,
    storageGet,
    storageSet,
    storageClear,
  });
})();
