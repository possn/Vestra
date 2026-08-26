from pathlib import Path

p = Path("scripts/run.py")
s = p.read_text(encoding="utf-8")
old = '        if row.get("congress_trades"): row["data_sources"].append("STOCK Act / Bargo")\n'
new = '        if row.get("congress_trades"): row["data_sources"].append("U.S. House Clerk / STOCK Act")\n'
if s.count(old) != 1:
    raise SystemExit(f"expected exactly one legacy Congress provenance line, found {s.count(old)}")
s = s.replace(old, new, 1)
if "STOCK Act / Bargo" in s:
    raise SystemExit("legacy Congress provenance still remains in scripts/run.py")
p.write_text(s, encoding="utf-8")
print("Congress provenance now names the canonical official House Clerk source")
