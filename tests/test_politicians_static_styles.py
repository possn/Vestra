from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class PoliticiansStaticStyleTests(unittest.TestCase):
    def test_politicians_use_static_stylesheet_but_keep_dynamic_bar_width(self):
        source = read('politicians.js')
        css = read('politicians.css')

        self.assertIn("document.createElement('link')", source)
        self.assertIn("link.rel='stylesheet'", source)
        self.assertIn("politicians.css?v=1.1", source)
        self.assertNotIn("document.createElement('style')", source)
        self.assertNotIn("s.textContent=", source)

        # Trade magnitude is data-driven presentation and must remain dynamic.
        self.assertIn('style="width:${Math.max(7,amountValue(x.amount)/max*100)}%"', source)

        for selector in (
            '.politician-view-tabs',
            '.politician-profile',
            '.politician-bar',
            '.politician-favourite-grid',
            '.politician-search-field',
            '.politician-search-results',
            '.politician-search-result',
            '@media(max-width:620px)',
        ):
            self.assertIn(selector, css)

    def test_picker_has_live_name_search_and_preserves_full_list(self):
        source = read('politicians.js')
        self.assertIn('data-politician-search', source)
        self.assertIn('data-politician-search-results', source)
        self.assertIn('data-politician-search-result', source)
        self.assertIn('function searchMembers(query)', source)
        self.assertIn('function updateSearchResults(input)', source)
        self.assertIn("document.addEventListener('input'", source)
        self.assertIn("document.addEventListener('keydown'", source)
        self.assertIn('data-politician-select', source)
        self.assertIn("const VERSION='2.1'", source)

    def test_filing_links_allow_only_https_and_future_feed_is_not_fresh(self):
        import subprocess
        source = read('politicians.js')
        safe_fn = 'function safeFilingUrl(v){' + source.split(
            'function safeFilingUrl(v){', 1)[1].split('  const searchText=', 1)[0]
        freshness_fn = 'function politiciansSnapshotFresh(d){' + source.split(
            'function politiciansSnapshotFresh(d){', 1)[1].split('  function enrichMemberCounts(', 1)[0]
        script = """
const assert = require('node:assert/strict');
const t = value => String(value ?? '').trim();
""" + safe_fn + freshness_fn + """
assert.equal(safeFilingUrl('https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/123.pdf'),
  'https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/123.pdf');
for(const url of ['javascript:alert(1)', 'data:text/html,a', 'http://example.org/a',
                  '//example.org/a', 'file:///etc/passwd', '']) {
  assert.equal(safeFilingUrl(url), '', url);
}
const dayOffset = n => new Date(Date.now() + n*86400000).toISOString().slice(0,10);
const feed = day => ({schema_version:2,trades:[],members:[],newest_disclosure:day});
assert.equal(politiciansSnapshotFresh(feed(dayOffset(-2))),true);
assert.equal(politiciansSnapshotFresh(feed(dayOffset(2))),false);
assert.equal(politiciansSnapshotFresh(feed(dayOffset(-62))),false);
"""
        result = subprocess.run(['node', '-e', script], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('safeFilingUrl(x.filing_url)', source)
        self.assertNotIn('href="${esc(x.filing_url)}"', source)

    def test_service_worker_precaches_and_refreshes_politicians_runtime(self):
        sw = read('sw.js')
        self.assertIn('./politicians.js', sw)
        self.assertIn('./politicians.css', sw)
        network_first = sw.split('const BOOTSTRAP_NETWORK_FIRST = new Set([', 1)[1].split(']);', 1)[0]
        self.assertIn('"politicians.js"', network_first)


if __name__ == '__main__':
    unittest.main(verbosity=2)
