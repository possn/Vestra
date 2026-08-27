from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "run.py"
WF = ROOT / ".github" / "workflows" / "integrate-derived-fundamentals.yml"
SELF = ROOT / "scripts" / "integrate_derived_fundamentals.py"

text = RUN.read_text(encoding="utf-8")

import_marker = "from quarterly_gap_retrieval import enrich as enrich_quarterly_gap_retrieval\n"
import_line = "from derived_fundamentals import enrich as enrich_derived_fundamentals\n"
if import_line not in text:
    if import_marker not in text:
        raise SystemExit("guard failed: quarterly gap import marker missing")
    text = text.replace(import_marker, import_marker + import_line, 1)

call_marker = "    raw = enrich_quarterly_gap_retrieval(raw, priority=portfolio_set)\n    raw = enrich_capital_risk(raw, priority=portfolio_set)\n"
replacement = "    raw = enrich_quarterly_gap_retrieval(raw, priority=portfolio_set)\n    raw = enrich_derived_fundamentals(raw)\n    raw = enrich_capital_risk(raw, priority=portfolio_set)\n"
if "raw = enrich_derived_fundamentals(raw)" not in text:
    if call_marker not in text:
        raise SystemExit("guard failed: enrichment sequence marker missing")
    text = text.replace(call_marker, replacement, 1)

prov_marker = "        row[\"data_sources\"] = [\"Yahoo Finance\"]\n"
prov_add = (
    "        row[\"data_sources\"] = [\"Yahoo Finance\"]\n"
    "        _derived_metrics = list(getattr(rm, \"derived_metrics\", []) or []) if rm is not None else []\n"
    "        if _derived_metrics:\n"
    "            row[\"derived_metrics\"] = _derived_metrics\n"
    "            row[\"derived_metric_note\"] = \"Calculated only from observed inputs; never an independent source\"\n"
)
if "row[\"derived_metrics\"]" not in text:
    if prov_marker not in text:
        raise SystemExit("guard failed: provenance marker missing")
    text = text.replace(prov_marker, prov_add, 1)

log_marker = 'for _name in ("run", "universe", "fundamentals", "sec_enrich", "esef_enrich", "capital_risk",'
if log_marker in text and '"derived_fundamentals"' not in text.split("log = logging.getLogger",1)[0]:
    text = text.replace('"esef_enrich", "capital_risk"', '"esef_enrich", "derived_fundamentals", "capital_risk"', 1)

RUN.write_text(text, encoding="utf-8")

# Self-clean the one-shot integration machinery.
for path in (WF, SELF):
    if path.exists():
        path.unlink()
