from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class EditorialCardRadius(unittest.TestCase):
 def test_shared_tokens_consumed_by_market_and_portfolio(self):
  base=(ROOT/"vestra-design-v2.css").read_text()
  market=(ROOT/"vestra-market-surfaces-v2.css").read_text()
  portfolio=(ROOT/"vestra-portfolio-v2.css").read_text()
  self.assertIn("--vestra-card-radius: 20px",base)
  self.assertIn("--vestra-card-radius-compact: 10px",base)
  self.assertIn("border-radius:var(--vestra-card-radius)",market)
  self.assertIn("border-radius:var(--vestra-card-radius-compact)",portfolio)
 def test_cache_revisions(self):
  html=(ROOT/"index.html").read_text()
  for ref in ["vestra-design-v2.css?v=4","vestra-portfolio-v2.css?v=6","vestra-market-surfaces-v2.css?v=5"]:
   self.assertIn(ref,html)
