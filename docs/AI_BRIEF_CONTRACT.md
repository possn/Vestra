# Vestra AI Brief — Worker contract v1

The frontend never receives an LLM provider API key.

## Endpoint

`POST /ai-brief`

The existing Vestra Worker should authenticate/rate-limit as appropriate, call the configured LLM provider server-side, and return JSON only.

## Request

```json
{
  "type": "company_brief",
  "version": "1",
  "data": {
    "ticker": "ADI",
    "name": "Analog Devices, Inc.",
    "sector": "Technology",
    "industry": "Semiconductors",
    "score": 73,
    "confidence": 82,
    "coverage": 78,
    "critical_coverage": 69,
    "roe": 0.122,
    "revenue_growth": 0.396,
    "earnings_growth": null,
    "fcf_yield": null,
    "forward_pe": 22.7,
    "price_to_book": null,
    "debt_to_equity": null,
    "timing": 64,
    "recovery_score": 64,
    "recovery_status": "recovering",
    "estimate_signal": "improving",
    "thesis_direction": "up",
    "fair_value_upside_pct": null,
    "analyst_price_target_upside_pct": null,
    "business_summary": "..."
  }
}
```

## Response

```json
{
  "brief": {
    "thesis": "...",
    "why_now": "...",
    "risks": ["...", "..."],
    "catalysts": ["...", "..."],
    "what_changes_the_thesis": "..."
  }
}
```

## Prompt rules

- Use only the supplied Vestra evidence.
- Never invent missing metrics, news, prices, filings, targets or management commentary.
- Explicitly distinguish missing data from weak data.
- Do not create a new investment score.
- Do not output `buy`, `sell` or position-sizing instructions.
- Explain uncertainty when coverage/confidence is limited.
- Keep output concise and decision-oriented.
- Prefer Portuguese (Portugal) for the user-facing response.

## Operational safeguards

- Provider key only in Worker secret/environment storage.
- Cache by ticker + dataset generation + relevant metric hash.
- Invalidate cache when score, estimates, recovery, filing/news evidence or material price state changes.
- Rate-limit per client/session.
- Set a short model timeout; frontend keeps the deterministic local brief if the LLM fails.
