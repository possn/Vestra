"""The independent OHLCV feed must own the Small Caps research timestamp."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"market-opportunities.js").read_text(encoding="utf-8")
UI=(ROOT/"market.js").read_text(encoding="utf-8")

class SmallcapSourceDateContract(unittest.TestCase):
 def test_research_date_is_never_inherited_from_market_universe(self):
  self.assertIn("smallcapFeedGeneratedAt=payload.generated_at",JS)
  self.assertIn("function smallcapProvenanceLabel()",JS)
  self.assertIn("activeLens==='smallcap_breakout'",JS)
  self.assertIn("? smallcapProvenanceLabel()",JS)
  self.assertIn("data-smallcap-original-market-age",JS)
  self.assertIn("OHLCV · fonte indisponível",JS)
  self.assertIn(" · desatualizado",JS)
  self.assertIn('timeZone:\'Europe/Lisbon\'',JS)
  self.assertIn('<span class="market-data-age">${ageText()}</span>',UI)
 def test_an_invalid_feed_cannot_retain_a_prior_verified_date(self):
  self.assertIn("smallcapFeedGeneratedAt=null;",JS)
  self.assertIn("smallcapFeedStatus='unavailable';",JS)
  self.assertIn("smallcapFeedStatus='outdated';",JS)

if __name__=="__main__": unittest.main()
