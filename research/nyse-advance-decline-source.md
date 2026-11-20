# NYSE Advance–Decline · observational contract (2026-11-19)

The Vestra turning-point experiment can accept actual daily advancing and declining **NYSE-listed common-stock issues**. This is a different population from a six-ETF trend proxy, and is **not** reconstructed from those ETFs. The official NYSE historical TAQ product is documented at https://www.nyse.com/market-data/historical/ . Interactive Brokers documents a NYSE advance–decline market-statistics instrument, `AD-NYSE`, at https://www.interactivebrokers.com/docs/tws-api/contracts/market-indicators ; its availability is subject to the appropriate market-data subscriptions. Neither currently supplies this repository with a verified, reproducible daily series.

The published `data/nyse-advance-decline.json` therefore explicitly says unavailable. A licensed/verified ingest may replace it **only** with:

```json
{
  "venue": "NYSE",
  "instrument_scope": "listed_common_stocks",
  "method": "issues_advancers_minus_decliners",
  "source_url": "https://provider.example/actual-source-page",
  "sessions": [
    {"date": "2026-08-20", "advancers": 1500, "decliners": 1200}
  ]
}
```

The example is schema-only, **not observed market data**. Required: >=60 chronological sessions; integers for issue counts; end date equal to the latest closed SPY session; >=45 matching SPY dates; HTTPS provenance. Invalid/missing data cannot vote. The A–D line is a cumulative sum of net advancing issues; absolute level depends on its arbitrary starting date, so only relative differences and divergences are evaluated. In a price lower-low test versus the prior 20 sessions, a higher A–D low with improving five-day net breadth supports a possible bottom; the opposite supports a possible top. These are exploratory thresholds, not established forecasts. Full point-in-time evaluation, source coverage auditing and licensing confirmation are prerequisites to treating this as validated evidence.
