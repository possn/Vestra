from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.js'
INDEX = ROOT / 'index.html'

START = '/* ─── INFO TIPS (explicações contextuais) ─────────────────── */'
END = '/* ─── PERSISTENCE (IndexedDB + localStorage fallback) ─────── */'
REPLACEMENT = '/* ─── INFO TIPS + TOAST moved to app-feedback.js ───────────── */\n\n'


def patch_app():
    text = APP.read_text(encoding='utf-8')
    if 'INFO TIPS + TOAST moved to app-feedback.js' in text:
        print('app.js feedback block already migrated')
        return False
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError('Unexpected app.js feedback/persistence markers')
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + REPLACEMENT + END + after
    prefix = updated[:updated.index(END)]
    for legacy in ['const TIPS = {', 'function openTip(key)', 'function toast(msg']:
        if legacy in prefix:
            raise RuntimeError(f'Legacy feedback code still present: {legacy}')
    APP.write_text(updated, encoding='utf-8')
    return True


def patch_index():
    text = INDEX.read_text(encoding='utf-8')
    app_tag = '<script defer="" fetchpriority="high" src="app.js?v=20260824v11"></script>'
    util_tag = '<script defer="" src="app-utils.js?v=1.0"></script>'
    feedback_tag = '<script defer="" src="app-feedback.js?v=1.0"></script>'
    if util_tag not in text:
        raise RuntimeError('app-utils.js must already be loaded before stage 2')
    if feedback_tag not in text:
        if text.count(app_tag) != 1:
            raise RuntimeError('Could not locate canonical app.js script tag')
        text = text.replace(app_tag, feedback_tag + '\n' + app_tag, 1)
        INDEX.write_text(text, encoding='utf-8')
        changed = True
    else:
        changed = False
    if not (text.index(util_tag) < text.index(feedback_tag) < text.index(app_tag)):
        raise RuntimeError('Expected order: app-utils.js -> app-feedback.js -> app.js')
    return changed


changed = patch_app() | patch_index()
print('Stage-two app extraction applied' if changed else 'No changes required')
