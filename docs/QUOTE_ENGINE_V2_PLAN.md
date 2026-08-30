# Quote Engine v2 — identity-first refresh

Temporary implementation branch plan.

1. Resolve each portfolio holding to a canonical instrument before requesting a quote.
2. Prefer authoritative ISIN mappings and broker exchange-qualified symbols over suffix guessing.
3. Deduplicate by canonical instrument/ISIN before network requests.
4. Batch quotes explicitly, with bounded upstream timeouts and cache.
5. Reject cross-listed/wrong-company collisions and implausible price jumps; retain the last trusted quote.
6. Separate FX refresh from equity/ETF quote refresh.
7. Surface diagnostics by canonical instrument, not by raw portfolio row.

Broker evidence used during repair includes Trading 212 exports (2023–2026) and the XTB statement supplied by the portfolio owner. No account identifiers or transaction-level data are committed to the repository.
