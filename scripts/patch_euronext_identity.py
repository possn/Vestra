from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'scripts' / 'esef_enrich_v416.py'
text = p.read_text(encoding='utf-8')

old = 'from lse_identity import resolve_isin as resolve_lse_isin\n'
new = old + 'from euronext_identity import resolve_isin as resolve_euronext_isin\n'
if new not in text:
    if old not in text:
        raise SystemExit('import anchor not found')
    text = text.replace(old, new, 1)

old2 = "    if str(t or '').upper().endswith('.L'):\n"
new2 = "    try:\n        x=resolve_euronext_isin(t,s)\n    except Exception:\n        x=None\n    if x and ISIN_RE.match(str(x).upper()):\n        return str(x).upper(),'Euronext official equities list'\n    if str(t or '').upper().endswith('.L'):\n"
if new2 not in text:
    if old2 not in text:
        raise SystemExit('resolver anchor not found')
    text = text.replace(old2, new2, 1)

p.write_text(text, encoding='utf-8')
print('Euronext identity integration applied.')
