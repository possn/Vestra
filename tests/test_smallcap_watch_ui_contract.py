"""Small-cap partial geometry must stay separate from verified setups."""
from pathlib import Path
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/"market-opportunities.js").read_text()


class SmallcapWatchContractTests(unittest.TestCase):
    def test_partial_watch_never_enters_verified_signal_map(self):
        verified=SOURCE.split("const found=new Map();",1)[1].split("smallcapFeed=found;",1)[0]
        watch=SOURCE.split("smallcapGeometryWatch=(",1)[1]
        self.assertNotIn("geometry_watch_observations",verified)
        self.assertIn("partial_geometry_observation_not_signal",watch)
        self.assertIn("smallcapFeedStatus==='ready'?smallcapGeometryWatch:[]",SOURCE)


if __name__=="__main__":unittest.main()
