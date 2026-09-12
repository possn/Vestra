from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class VestraAiBriefStyleTests(unittest.TestCase):
    def test_ai_brief_uses_static_stylesheet_without_changing_evidence_runtime(self):
        js = read('vestra-ai-brief.js')
        css = read('vestra-ai-brief.css')
        self.assertIn("const VERSION='1.1'", js)
        self.assertIn("vestra-ai-brief.css?v=1.0", js)
        self.assertIn("link.rel='stylesheet'", js)
        self.assertNotIn("document.createElement('style')", js)
        self.assertNotIn('x.textContent=', js)
        for token in ('function evidence(', 'function payload(', '/ai-brief', 'x-vestra-session', 'window.VestraAiBrief'):
            self.assertIn(token, js)
        self.assertIn('.ai459-card{', css)
        self.assertIn('.ai459-grid{', css)
        self.assertIn('@media(max-width:620px)', css)

    def test_service_worker_precaches_ai_brief_stylesheet(self):
        sw = read('sw.js')
        self.assertIn('"./vestra-ai-brief.js"', sw)
        self.assertIn('"./vestra-ai-brief.css"', sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
