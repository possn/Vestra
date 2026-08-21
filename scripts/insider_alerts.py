"""Background SEC Form 4 watcher -> ntfy push notifications.

Designed for the lightweight hourly GitHub Actions workflow. It does NOT rebuild
Finscanner's full dataset. It checks SEC submissions metadata for the user's
portfolio universe, fetches structured Form 4 XML only for newly-seen filings,
and sends one ntfy notification per open-market buy/sell group.

First run is baseline-only (no historical flood). Manual workflow runs may set
FINSCANNER_ALERT_TEST=1 to send a connectivity test notification.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests

# Reuse the SEC client/parsing logic already hardened for the main pipeline.
from insiders import (
    _fetch_structured_filing,
    _load_ticker_cik_map,
    _recent_form4_rows,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRA_TICKERS = ROOT / "data" / "extra_tickers.json"
ALERT_WATCHLIST = ROOT / "data" / "alert_watchlist.json"
ALERT_CONFIG = ROOT / "data" / "insider_alert_config.json"
STATE_PATH = ROOT / "data" / "insider_alert_state.json"
STOCKS_PATH = ROOT / "data" / "stocks.json"

LOOKBACK_DAYS = max(3, min(30, int(os.getenv("FINSCANNER_INSIDER_ALERT_LOOKBACK_DAYS", "10"))))
MAX_NEW_FILINGS_PER_TICKER = max(1, min(20, int(os.getenv("FINSCANNER_INSIDER_ALERT_MAX_NEW", "8"))))
NTFY_SERVER = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = (os.getenv("NTFY_TOPIC") or "").strip().strip("/")
NTFY_TOKEN = (os.getenv("NTFY_TOKEN") or "").strip()
SEND_TEST = (os.getenv("FINSCANNER_ALERT_TEST") or "").lower() in {"1", "true", "yes", "on"}
SEND_HEARTBEAT = (os.getenv("FINSCANNER_ALERT_HEARTBEAT") or "").lower() in {"1", "true", "yes", "on"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("insider-alerts")


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _load_alert_config() -> dict:
    defaults = {
        "alert_buys": True,
        "alert_sells": True,
        "min_buy_value_usd": 0,
        "min_sell_value_usd": 100000,
        "strong_buy_value_usd": 500000,
        "large_sale_value_usd": 1000000,
        "cluster_window_days": 14,
        "reversal_window_days": 90,
        "senior_roles": ["CEO", "Chief Executive", "CFO", "Chief Financial", "President", "Chairman", "Director"],
    }
    raw = _load_json(ALERT_CONFIG, {})
    if isinstance(raw, dict):
        defaults.update(raw)
    return defaults


def _event_date(value: str | None):
    try:
        return dt.date.fromisoformat(str(value or "")[:10])
    except Exception:
        return None


def _is_senior(role: str | None, cfg: dict) -> bool:
    text = str(role or "").lower()
    return any(str(x).lower() in text for x in (cfg.get("senior_roles") or []))



def _current_price_map() -> dict[str, float]:
    raw = _load_json(STOCKS_PATH, {})
    rows = raw.get("stocks") if isinstance(raw, dict) else []
    out = {}
    for r in rows or []:
        try:
            price = float(r.get("current_price"))
            if price > 0:
                out[str(r.get("ticker") or "").upper()] = price
        except Exception:
            pass
    return out


def _near_low_candidates() -> dict[str, dict]:
    """Full rows (not just price) for the near-52-week-low check — same
    quality gate as the Home 'Perto de mínimos, boa qualidade' lane and
    the 'near-low' discovery preset (score>=50, within 15% of the 52-week
    low, not a zombie, thesis not weakening) so an alert and the in-app
    ranking never disagree about what counts as a real opportunity vs a
    falling knife."""
    raw = _load_json(STOCKS_PATH, {})
    rows = raw.get("stocks") if isinstance(raw, dict) else []
    out = {}
    for r in rows or []:
        ticker = str(r.get("ticker") or "").upper()
        if not ticker:
            continue
        try:
            score = float(r.get("score"))
            px = float(r.get("current_price"))
        except Exception:
            continue
        if not (score >= 50) or not (px > 0):
            continue
        if r.get("zombie") == "yes" or r.get("thesis_direction") == "weakening":
            continue
        hist = r.get("price_history_1y") or []
        vals = [v for v in (
            (h.get("close") if isinstance(h, dict) else None) for h in hist
        ) if isinstance(v, (int, float))]
        if not vals:
            continue
        lo = min(vals)
        if lo <= 0:
            continue
        dist_pct = (px / lo - 1) * 100
        out[ticker] = {
            "in_zone": dist_pct <= 15,
            "dist_pct": round(dist_pct, 1),
            "score": round(score, 1),
            "price": px,
            "name": r.get("name") or ticker,
        }
    return out


def _check_price_alerts(watchlist: list[str], state: dict) -> tuple[int, bool]:
    """Alert once per 'episode' of a watchlist/portfolio ticker entering
    the near-52-week-low quality zone — not on every hourly run while it
    stays there. An episode ends (and can re-alert later) once the ticker
    leaves the zone, e.g. the price recovers or the thesis turns."""
    if not watchlist:
        return 0, False
    candidates = _near_low_candidates()
    price_state = state["price_alerts"]
    sent = 0
    changed = False
    for ticker in watchlist:
        info = candidates.get(ticker)
        was_in_zone = bool(price_state.get(ticker, {}).get("in_zone"))
        now_in_zone = bool(info and info["in_zone"])
        if now_in_zone and not was_in_zone:
            _post_ntfy(
                f"{ticker} perto do mínimo de 52 semanas",
                f"{info['name']} está a {info['dist_pct']:.1f}% do mínimo anual, com score {info['score']:.0f}/100 e tese estável ou a reforçar. "
                f"Preço atual: {info['price']:.2f}.",
                priority=3,
                tags="chart_with_downwards_trend,mag",
                click=f"https://possn.github.io/Finscanner/#ticker={ticker}",
            )
            sent += 1
        if now_in_zone != was_in_zone:
            price_state[ticker] = {"in_zone": now_in_zone}
            changed = True
    return sent, changed


def _conviction_score(group: dict, history: list[dict], cfg: dict, current_price: float | None = None) -> tuple[int, list[str]]:
    value = float(group.get("value") or 0) if group.get("known_value") else 0.0
    role = str(group.get("role") or "")
    when = _event_date(group.get("date")) or dt.date.today()
    age = max(0, (dt.date.today() - when).days)
    score = 0
    reasons: list[str] = []
    if value >= 2_000_000: score += 35; reasons.append("$2M+")
    elif value >= 1_000_000: score += 32; reasons.append("$1M+")
    elif value >= 500_000: score += 28; reasons.append("$500k+")
    elif value >= 100_000: score += 22; reasons.append("$100k+")
    elif value >= 50_000: score += 16; reasons.append("$50k+")
    elif value > 0: score += 9
    else: score += 5
    if _is_senior(role, cfg): score += 20; reasons.append("senior")
    elif "director" in role.lower(): score += 13; reasons.append("director")
    else: score += 7
    if age <= 7: score += 15; reasons.append("≤7d")
    elif age <= 30: score += 11; reasons.append("≤30d")
    elif age <= 90: score += 6
    owner = str(group.get("owner") or "Insider")
    if group.get("type") == "buy":
        buyers = {owner}
        window = int(cfg.get("cluster_window_days") or 14)
        for e in history:
            d = _event_date(e.get("date"))
            if e.get("type") == "buy" and d and 0 <= (when-d).days <= window:
                buyers.add(str(e.get("owner") or "Insider"))
        if len(buyers) >= 2: score += 18; reasons.append("cluster")
    rev_days = int(cfg.get("reversal_window_days") or 90)
    for e in reversed(history):
        if str(e.get("owner") or "") != owner or e.get("type") == group.get("type"): continue
        d = _event_date(e.get("date"))
        if d and 0 <= (when-d).days <= rev_days:
            score += 9; reasons.append("reversal"); break
    prices = group.get("prices") or []
    tx_price = sum(prices)/len(prices) if prices else None
    if tx_price and current_price and tx_price > 0 and current_price > 0:
        gap = abs(current_price/tx_price - 1)
        if gap <= .05: score += 10; reasons.append("price ±5%")
        elif gap <= .10: score += 7; reasons.append("price ±10%")
        elif gap <= .20: score += 4
    return min(100, int(round(score))), reasons


def _signal_for_group(ticker: str, group: dict, history: list[dict], cfg: dict) -> dict:
    is_buy = group.get("type") == "buy"
    value = float(group.get("value") or 0) if group.get("known_value") else 0.0
    owner = str(group.get("owner") or "Insider")
    role = str(group.get("role") or "")
    today = _event_date(group.get("date")) or dt.date.today()

    # Previous opposite-side action by the same insider = behavioural reversal.
    reversal = False
    rev_days = int(cfg.get("reversal_window_days") or 90)
    for e in reversed(history):
        if str(e.get("owner") or "") != owner or e.get("type") == group.get("type"):
            continue
        d = _event_date(e.get("date"))
        if d and 0 <= (today-d).days <= rev_days:
            reversal = True
            break

    # Cluster buying = at least two unique insiders buying within the configured window.
    cluster = False
    cluster_days = int(cfg.get("cluster_window_days") or 14)
    if is_buy:
        buyers = {owner}
        for e in history:
            if e.get("type") != "buy":
                continue
            d = _event_date(e.get("date"))
            if d and 0 <= (today-d).days <= cluster_days:
                buyers.add(str(e.get("owner") or "Insider"))
        cluster = len(buyers) >= 2

    if is_buy and cluster:
        return {"code":"cluster_buy", "label":"CLUSTER BUYING", "priority":5, "tags":"people_holding_hands,chart_with_upwards_trend"}
    if is_buy and _is_senior(role, cfg) and value >= float(cfg.get("strong_buy_value_usd") or 500000):
        return {"code":"strong_buy", "label":"STRONG BUY SIGNAL", "priority":5, "tags":"large_green_circle,moneybag"}
    if reversal and is_buy:
        return {"code":"buy_reversal", "label":"INSIDER REVERSAL → BUY", "priority":5, "tags":"arrows_counterclockwise,chart_with_upwards_trend"}
    if reversal and not is_buy:
        return {"code":"sell_reversal", "label":"INSIDER REVERSAL → SELL", "priority":4, "tags":"arrows_counterclockwise,warning"}
    if (not is_buy) and value >= float(cfg.get("large_sale_value_usd") or 1000000):
        return {"code":"large_sale", "label":"LARGE INSIDER SALE", "priority":4, "tags":"large_red_circle,money_with_wings"}
    return {"code":"buy" if is_buy else "sell", "label":"INSIDER BUY" if is_buy else "INSIDER SELL", "priority":4 if is_buy else 3, "tags":"chart_with_upwards_trend,moneybag" if is_buy else "chart_with_downwards_trend,money_with_wings"}


def _should_alert(group: dict, cfg: dict) -> bool:
    value = float(group.get("value") or 0) if group.get("known_value") else 0.0
    if group.get("type") == "buy":
        return bool(cfg.get("alert_buys", True)) and value >= float(cfg.get("min_buy_value_usd") or 0)
    return bool(cfg.get("alert_sells", True)) and value >= float(cfg.get("min_sell_value_usd") or 0)


def _load_alert_tickers() -> list[str]:
    """Portfolio from extra_tickers + optional repository-side watchlist.

    Browser localStorage cannot be read by GitHub Actions, so background watchlist
    symbols can optionally be mirrored in data/alert_watchlist.json.
    """
    extra = _load_json(EXTRA_TICKERS, {})
    if isinstance(extra, dict):
        tickers = extra.get("tickers") or []
    elif isinstance(extra, list):
        tickers = extra
    else:
        tickers = []

    wl = _load_json(ALERT_WATCHLIST, {})
    if isinstance(wl, dict):
        watch = wl.get("tickers") or []
    elif isinstance(wl, list):
        watch = wl
    else:
        watch = []

    out = []
    seen = set()
    for tk in [*tickers, *watch]:
        s = str(tk or "").strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _load_state() -> dict:
    state = _load_json(STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    if not isinstance(state.get("tickers"), dict):
        state["tickers"] = {}
    if not isinstance(state.get("price_alerts"), dict):
        state["price_alerts"] = {}
    state.setdefault("schema_version", 1)
    return state


def _save_state(state: dict) -> None:
    state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _money(v) -> str:
    if not isinstance(v, (int, float)):
        return "valor não indicado"
    a = abs(float(v))
    if a >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if a >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if a >= 1_000:
        return f"${v/1_000:.0f}k"
    return f"${v:,.0f}"


def _number(v) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return f"{v:,.0f}".replace(",", " ")


def _post_ntfy(title: str, message: str, *, priority: int = 3, tags: str = "chart_with_upwards_trend", click: str | None = None) -> None:
    """Publish through ntfy's JSON API.

    Do not put user-visible Unicode text in HTTP headers: Python's http.client
    encodes header values as latin-1, so characters such as ✓/→ raise
    UnicodeEncodeError before the request even leaves GitHub Actions.
    JSON is UTF-8 and safely carries Portuguese text and symbols.
    """
    if not NTFY_TOPIC:
        raise RuntimeError("NTFY_TOPIC is not configured")

    headers = {"Content-Type": "application/json; charset=utf-8"}
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    payload = {
        "topic": NTFY_TOPIC,
        "title": title,
        "message": message,
        "priority": int(priority),
        "tags": [t.strip() for t in str(tags).split(",") if t.strip()],
    }
    if click:
        payload["click"] = click

    r = requests.post(NTFY_SERVER, json=payload, headers=headers, timeout=20)
    r.raise_for_status()


def _filing_url(cik: str, filing: dict) -> str | None:
    acc = str(filing.get("accession") or "").replace("-", "")
    doc = str(filing.get("primary_document") or "").strip()
    if not acc or not doc:
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"


def _group_transactions(transactions: Iterable[dict]) -> list[dict]:
    """Aggregate multiple same-side rows in one Form 4 into concise alerts."""
    groups: dict[tuple, dict] = {}
    for tx in transactions:
        kind = tx.get("type")
        if kind not in {"buy", "sell"}:
            continue
        key = (kind, tx.get("owner") or "Insider", tx.get("role") or "", tx.get("date") or "")
        g = groups.setdefault(key, {
            "type": kind,
            "owner": tx.get("owner") or "Insider",
            "role": tx.get("role") or "",
            "date": tx.get("date") or "",
            "shares": 0.0,
            "value": 0.0,
            "known_shares": False,
            "known_value": False,
            "prices": [],
        })
        if isinstance(tx.get("shares"), (int, float)):
            g["shares"] += float(tx["shares"])
            g["known_shares"] = True
        if isinstance(tx.get("value"), (int, float)):
            g["value"] += float(tx["value"])
            g["known_value"] = True
        if isinstance(tx.get("price"), (int, float)):
            g["prices"].append(float(tx["price"]))
    return list(groups.values())


def _send_transaction_alert(ticker: str, group: dict, filing_url: str | None, signal: dict, conviction: int, reasons: list[str]) -> None:
    is_buy = group["type"] == "buy"
    verb = "COMPROU" if is_buy else "VENDEU"
    role = f" · {group['role']}" if group.get("role") else ""
    shares = _number(group["shares"]) if group.get("known_shares") else "—"
    value = _money(group["value"]) if group.get("known_value") else "valor não indicado"
    prices = group.get("prices") or []
    if prices:
        if min(prices) == max(prices):
            price_txt = f"${prices[0]:,.2f}/ação"
        else:
            price_txt = f"${min(prices):,.2f}–${max(prices):,.2f}/ação"
    else:
        price_txt = "preço não indicado"
    message = (
        f"{group['owner']}{role}\n"
        f"{shares} ações · {value} · {price_txt}\n"
        f"Data da transação: {group.get('date') or '—'} · Form 4 SEC\n"
        f"Conviction: {conviction}/100"
    )
    _post_ntfy(
        f"{signal.get('label', 'INSIDER ACTIVITY')} · {ticker}",
        f"{message}\nClassificação: {signal.get('label', '—')} · {' · '.join(reasons[:3])}",
        priority=int(signal.get("priority") or (4 if is_buy else 3)),
        tags=str(signal.get("tags") or ("chart_with_upwards_trend,moneybag" if is_buy else "chart_with_downwards_trend,money_with_wings")),
        click=filing_url,
    )


def run() -> int:
    if not NTFY_TOPIC:
        log.error("NTFY_TOPIC secret is missing. Configure it in GitHub Actions secrets.")
        return 2

    if SEND_TEST:
        _post_ntfy(
            "Finscanner Insider Alerts ✓",
            "Ligação GitHub Actions → ntfy ativa. O Finscanner vai verificar novos Form 4 de hora a hora.",
            priority=3,
            tags="white_check_mark,chart_with_upwards_trend",
        )
        log.info("ntfy test notification sent")

    all_requested = _load_alert_tickers()
    cik_map = _load_ticker_cik_map()
    us_tickers = [tk for tk in all_requested if tk in cik_map]
    state = _load_state()
    cfg = _load_alert_config()
    price_map = _current_price_map()
    per_ticker = state["tickers"]
    state_changed = False

    # Near-52-week-low alerts: separate concern from the Form 4 monitoring
    # above (doesn't need a CIK, so it runs against ALL requested tickers,
    # not just SEC-matched US issuers) but shares this same hourly job,
    # state file, and ntfy topic rather than a whole second workflow.
    price_alerts_sent, price_state_changed = _check_price_alerts(all_requested, state)
    if price_state_changed:
        state_changed = True

    log.info("alert universe: %d requested · %d SEC/US issuers", len(all_requested), len(us_tickers))
    new_filings = alerts_sent = detail_failures = 0
    baselined = 0

    for idx, ticker in enumerate(us_tickers, 1):
        cik = cik_map[ticker]
        try:
            filings = _recent_form4_rows(cik, LOOKBACK_DAYS)
        except Exception as e:
            log.warning("%s submissions unavailable: %s", ticker, e)
            continue

        current = {str(f.get("accession") or ""): f for f in filings if f.get("accession")}
        previous = per_ticker.get(ticker)
        if not isinstance(previous, dict):
            # First observation: baseline current filings, never send historical flood.
            per_ticker[ticker] = {
                "seen_accessions": sorted(current.keys()),
                "last_checked": dt.datetime.now(dt.timezone.utc).isoformat(),
                "event_history": [],
            }
            baselined += 1
            state_changed = True
            continue

        seen = set(previous.get("seen_accessions") or [])
        unseen = [current[a] for a in sorted(current.keys()) if a not in seen]
        unseen = unseen[-MAX_NEW_FILINGS_PER_TICKER:]

        for filing in unseen:
            accession = filing["accession"]
            new_filings += 1
            txs, raw_count, detail = _fetch_structured_filing(cik, filing, ticker)
            if raw_count <= 0:
                detail_failures += 1
                log.warning("%s %s structured Form 4 unavailable; will retry next run (%s)", ticker, accession, detail)
                continue

            url = _filing_url(cik, filing)
            groups = _group_transactions(txs)
            try:
                history = previous.get("event_history") if isinstance(previous.get("event_history"), list) else []
                for group in groups:
                    signal = _signal_for_group(ticker, group, history, cfg)
                    conviction, conviction_reasons = _conviction_score(group, history, cfg, price_map.get(ticker))
                    event = {
                        "type": group.get("type"), "owner": group.get("owner"), "role": group.get("role"),
                        "date": group.get("date"), "value": group.get("value"), "signal": signal.get("code"), "conviction": conviction,
                    }
                    if _should_alert(group, cfg):
                        _send_transaction_alert(ticker, group, url, signal, conviction, conviction_reasons)
                        alerts_sent += 1
                    else:
                        log.info("%s %s suppressed by alert thresholds (%s)", ticker, accession, group.get("type"))
                    history.append(event)
                # Keep only a bounded intelligence history for cluster/reversal detection.
                previous["event_history"] = history[-120:]
                per_ticker[ticker] = previous
                # Mark seen after notifications succeed. A Form 4 with no P/S (award,
                # option, gift...) is also safely marked seen once parsed.
                seen.add(accession)
                state_changed = True
            except Exception as e:
                log.error("%s %s ntfy publish failed; filing remains unseen: %s", ticker, accession, e)
                continue

        # Keep bounded state; accessions are tiny but no reason to grow forever.
        merged = list(dict.fromkeys([*(previous.get("seen_accessions") or []), *sorted(seen)]))
        bounded = merged[-120:]
        if bounded != (previous.get("seen_accessions") or []):
            previous["seen_accessions"] = bounded
            per_ticker[ticker] = previous
            state_changed = True

        if idx % 50 == 0:
            log.info("checked %d/%d SEC issuers", idx, len(us_tickers))

    if state_changed:
        state["last_change"] = {
            "requested": len(all_requested),
            "sec_issuers": len(us_tickers),
            "baselined": baselined,
            "new_filings": new_filings,
            "alerts_sent": alerts_sent,
            "detail_failures": detail_failures,
            "lookback_days": LOOKBACK_DAYS,
            "price_alerts_sent": price_alerts_sent,
        }
        _save_state(state)
    else:
        log.info("no alert-state changes; repository will not be committed")
    log.info(
        "done: baseline %d · new filings %d · alerts %d · detail retries %d · price alerts %d",
        baselined, new_filings, alerts_sent, detail_failures, price_alerts_sent,
    )
    if SEND_HEARTBEAT:
        _post_ntfy(
            "Finscanner · monitor insider ativo",
            f"Verificação automática concluída. {len(us_tickers)} emissores SEC verificados · {new_filings} novos Form 4 · {alerts_sent} alertas insider · {price_alerts_sent} alertas de mínimos 52s.",
            priority=2,
            tags="white_check_mark,clock1",
        )
        log.info("daily automatic heartbeat sent")
    return 0


if __name__ == "__main__":
    sys.exit(run())
