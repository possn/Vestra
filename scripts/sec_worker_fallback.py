"""Resilient transport shim for SEC CompanyFacts inside the market pipeline.

The canonical SEC parser remains scripts/sec_enrich.py. This module changes only
how its requests.Session reaches CompanyFacts:

1. use data.sec.gov directly when the runner can reach it;
2. if the direct request is blocked/rate-limited/unavailable, retry the same CIK
   through Vestra's Cloudflare Worker SEC transport;
3. keep sec_enrich's existing validated ticker-map snapshot fallback unchanged.

The Worker route is a transport proxy only. It still serves sec.gov payloads and
marks them with X-Vestra-Sec-Source: sec.gov, so this does not create a new
fundamental evidence family and does not alter Score Vestra semantics.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlencode

CANONICAL_WORKER_URL = "https://delicate-bar-cc80.pedrossnunes.workers.dev"
DEFAULT_SEC_USER_AGENT = "Vestra/4.0 (+https://github.com/possn/Vestra)"
_COMPANYFACTS_RE = re.compile(r"/api/xbrl/companyfacts/CIK(\d{10})\.json(?:$|[?#])", re.I)
_FALLBACK_STATUSES = {403, 429}
_DIAG_MILESTONES = {1, 5, 10, 25, 50, 100, 250, 500}


def _worker_url(direct_url: str, base: str) -> str | None:
    match = _COMPANYFACTS_RE.search(str(direct_url or ""))
    if not match:
        return None
    cik = str(int(match.group(1)))
    return f"{base.rstrip('/')}/sec/companyfacts?{urlencode({'cik': cik})}"


def _should_fallback(response) -> bool:
    status = int(getattr(response, "status_code", 0) or 0)
    return status in _FALLBACK_STATUSES or status >= 500


def _status_key(response) -> str:
    try:
        return str(int(getattr(response, "status_code", 0) or 0))
    except (TypeError, ValueError):
        return "0"


def _inc(mapping: dict, key: str) -> None:
    mapping[key] = int(mapping.get(key, 0) or 0) + 1


def _payload_state(response) -> str:
    """Classify a successful response without mutating/consuming it.

    requests.Response.json() is repeatable because it parses response.content on
    each call, so sec_enrich can still call .json() normally afterwards.
    Test doubles without .json() return 'unchecked'.
    """
    if not bool(getattr(response, "ok", False)):
        return "not_ok"
    parser = getattr(response, "json", None)
    if not callable(parser):
        return "unchecked"
    try:
        payload = parser()
    except Exception:
        return "json_error"
    if not isinstance(payload, dict):
        return "invalid_shape"
    facts = payload.get("facts")
    return "valid_facts" if isinstance(facts, dict) and bool(facts) else "missing_facts"


def install(module=None, *, worker_url: str | None = None):
    """Install the fallback into sec_enrich and return its Session wrapper.

    The SEC connectivity probe historically communicates a broad GitHub-runner
    403 by exporting an empty SEC_USER_AGENT. Convert that signal into
    SEC_DIRECT_BLOCKED=1 rather than allowing sec_enrich to disable the lane.
    This preserves compatibility with the current probe while recovering the
    official payload through the Worker.

    Diagnostics are aggregate-only and observational: no extra SEC request is
    made, no retry policy changes and no parsed value is modified.
    """
    if module is None:
        import sec_enrich as module

    if getattr(module, "_vestra_sec_worker_fallback_installed", False):
        return module.requests.Session

    configured_ua = os.getenv("SEC_USER_AGENT")
    if configured_ua is not None and not configured_ua.strip():
        os.environ["SEC_DIRECT_BLOCKED"] = "1"
        os.environ["SEC_USER_AGENT"] = DEFAULT_SEC_USER_AGENT

    base = (worker_url or os.getenv("VESTRA_WORKER_URL") or CANONICAL_WORKER_URL).strip().rstrip("/")
    original_factory = module.requests.Session
    original_enrich = getattr(module, "enrich", None)
    log = module.log

    class ResilientSecSession:
        def __init__(self, *args, **kwargs):
            self._inner = original_factory(*args, **kwargs)
            self.headers = self._inner.headers
            self._worker_hits = 0
            self._vestra_transport_diag = {
                "companyfacts_direct_attempts": 0,
                "companyfacts_direct_success": 0,
                "companyfacts_direct_exceptions": 0,
                "companyfacts_direct_status": {},
                "companyfacts_direct_payload": {},
                "companyfacts_worker_attempts": 0,
                "companyfacts_worker_success": 0,
                "companyfacts_worker_exceptions": 0,
                "companyfacts_worker_status": {},
                "companyfacts_worker_payload": {},
                "direct_blocked_mode": os.getenv("SEC_DIRECT_BLOCKED", "").strip() == "1",
            }
            module._vestra_last_sec_session = self

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def _record_payload(self, source: str, response) -> None:
            state = _payload_state(response)
            _inc(self._vestra_transport_diag[f"companyfacts_{source}_payload"], state)

        def _log_diag_milestone(self):
            attempts = int(self._vestra_transport_diag["companyfacts_worker_attempts"])
            if attempts in _DIAG_MILESTONES:
                log.warning(
                    "SEC transport diagnostics %s",
                    json.dumps(self._vestra_transport_diag, sort_keys=True, separators=(",", ":")),
                )

        def _via_worker(self, direct_url, timeout=20, **kwargs):
            proxy = _worker_url(direct_url, base)
            if not proxy:
                return None
            diag = self._vestra_transport_diag
            diag["companyfacts_worker_attempts"] += 1
            worker_kwargs = dict(kwargs)
            worker_kwargs.pop("stream", None)
            worker_kwargs.pop("headers", None)
            try:
                response = self._inner.get(
                    proxy,
                    timeout=timeout,
                    headers={"Accept": "application/json", "User-Agent": DEFAULT_SEC_USER_AGENT},
                    **worker_kwargs,
                )
            except Exception:
                diag["companyfacts_worker_exceptions"] += 1
                self._log_diag_milestone()
                raise
            self._worker_hits += 1
            key = _status_key(response)
            _inc(diag["companyfacts_worker_status"], key)
            if bool(getattr(response, "ok", False)):
                diag["companyfacts_worker_success"] += 1
                self._record_payload("worker", response)
            if self._worker_hits == 1:
                log.warning("SEC CompanyFacts using Vestra Worker transport fallback")
            self._log_diag_milestone()
            return response

        def get(self, url, timeout=20, **kwargs):
            proxy = _worker_url(url, base)
            if not proxy:
                return self._inner.get(url, timeout=timeout, **kwargs)

            diag = self._vestra_transport_diag
            if os.getenv("SEC_DIRECT_BLOCKED", "").strip() == "1":
                response = self._via_worker(url, timeout=timeout, **kwargs)
                return response if response is not None else self._inner.get(url, timeout=timeout, **kwargs)

            diag["companyfacts_direct_attempts"] += 1
            try:
                direct = self._inner.get(url, timeout=timeout, **kwargs)
            except Exception:
                diag["companyfacts_direct_exceptions"] += 1
                response = self._via_worker(url, timeout=timeout, **kwargs)
                if response is not None:
                    return response
                raise

            key = _status_key(direct)
            _inc(diag["companyfacts_direct_status"], key)
            if bool(getattr(direct, "ok", False)):
                diag["companyfacts_direct_success"] += 1
                self._record_payload("direct", direct)

            if _should_fallback(direct):
                try:
                    response = self._via_worker(url, timeout=timeout, **kwargs)
                    if response is not None and bool(getattr(response, "ok", False)):
                        return response
                except Exception as exc:
                    log.debug("SEC Worker fallback failed: %s", exc)
            return direct

    module._vestra_original_requests_session = original_factory
    module.requests.Session = ResilientSecSession

    if callable(original_enrich):
        def diagnostic_enrich(raw, *args, **kwargs):
            rows = list(raw) if not isinstance(raw, list) else raw
            before = sum(bool(getattr(row, "sec_edgar_enriched", False)) for row in rows)
            result = original_enrich(rows, *args, **kwargs)
            after = sum(bool(getattr(row, "sec_edgar_enriched", False)) for row in result)
            session = getattr(module, "_vestra_last_sec_session", None)
            transport = getattr(session, "_vestra_transport_diag", {}) if session is not None else {}
            summary = {
                "input_rows": len(rows),
                "newly_enriched_rows": max(0, after - before),
                "total_enriched_rows": after,
                "transport": transport,
            }
            log.info("SEC enrichment runtime diagnostics %s", json.dumps(summary, sort_keys=True, separators=(",", ":")))
            return result

        module._vestra_original_enrich = original_enrich
        module.enrich = diagnostic_enrich

    module._vestra_sec_worker_fallback_installed = True
    module._vestra_sec_worker_url = base
    return ResilientSecSession
