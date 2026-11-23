"""Helpers that compute WCAG contrast from the CSS actually shipped.

Replaces brittle exact-hex string pins: tests resolve var() tokens and assert
the ink/surface ratio, so palette refactors do not break them but a real
contrast regression does.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tokens():
    out = {}
    for name in ("vestra-design-v2.css",):
        for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", (ROOT / name).read_text()):
            out[k] = v.strip()
    return out


def resolve(value, toks):
    value = value.strip().replace("!important", "").strip()
    for _ in range(5):
        m = re.fullmatch(r"var\((--[\w-]+)(?:,[^)]*)?\)", value)
        if not m:
            break
        value = toks.get(m.group(1), value)
    return value


def _rgb(hexv):
    h = hexv.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(hexv):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hexv)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def declared_ink(css, selector, prop="color"):
    """Return the last hex colour declared for `prop` in a rule whose selector
    list contains `selector` (exact comma-separated item, `body:has(...)` prefix
    tolerated). None if absent."""
    toks = tokens()
    found = None
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        items = [s.strip() for s in sel.split(",")]
        if not any(i == selector or i.endswith(" " + selector) for i in items):
            continue
        m = re.findall(r"(?<![-\w])" + prop + r"\s*:\s*([^;]+)", body)
        if m:
            v = resolve(m[-1], toks)
            if re.fullmatch(r"#[0-9a-fA-F]{3,6}", v):
                found = v
    return found


def assert_contrast(testcase, css, selector, background, minimum=4.5):
    ink = declared_ink(css, selector)
    testcase.assertIsNotNone(ink, f"no resolvable colour declared for {selector}")
    ratio = contrast(ink, background)
    testcase.assertGreaterEqual(ratio, minimum, f"{selector}: {ink} on {background} = {ratio:.2f}")
