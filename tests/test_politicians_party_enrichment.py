"""Party metadata is filled only from a unique legislator match; never guessed."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for module in ("pdfplumber", "requests"):
    if module not in sys.modules:
        try:
            __import__(module)
        except ImportError:
            sys.modules[module] = types.ModuleType(module)
_spec = importlib.util.spec_from_file_location("bpf_party_tests", ROOT / "scripts" / "build_politicians_feed.py")
bpf = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bpf
_spec.loader.exec_module(bpf)


def leg(first, last, kind, state, party, nickname="", official=""):
    name = {"first": first, "last": last}
    if nickname:
        name["nickname"] = nickname
    if official:
        name["official_full"] = official
    return {"name": name, "terms": [{"type": kind, "state": state, "party": party}]}


LEGS = [
    leg("Gilbert", "Cisneros", "rep", "CA", "Democrat"),
    leg("April", "McClain Delaney", "rep", "MD", "Democrat"),
    leg("Lisa", "McClain", "rep", "MI", "Republican"),
    leg("Addison Mitchell", "McConnell", "sen", "KY", "Republican", nickname="Mitch"),
    leg("Rafael Edward", "Cruz", "sen", "TX", "Republican", nickname="Ted"),
    leg("John", "Boozman", "sen", "AR", "Republican"),
    leg("Mike", "Rulli", "rep", "OH", "Republican", official="Michael Rulli"),
    leg("Jonathan", "Jackson", "rep", "IL", "Democrat"),
    leg("Jonathan", "Jackson", "rep", "NC", "Republican"),  # same name, other state
    leg("Sheldon", "Whitehouse", "sen", "RI", "Democrat"),
]


def member(name, chamber, state=""):
    return {"name": name, "chamber": chamber, "state": state, "party": ""}


class PartyEnrichmentTests(unittest.TestCase):
    def run_one(self, name, chamber, state="", legs=LEGS):
        out = bpf.enrich_party([member(name, chamber, state)], legs)[0]
        return out["party"], out["state"]

    def test_messy_disclosure_names_match_uniquely(self):
        self.assertEqual(self.run_one("Hon. Gilbert Cisneros", "House", "CA"), ("Democrat", "CA"))
        self.assertEqual(self.run_one("A. Mitchell McConnell, Jr.", "Senate"), ("Republican", "KY"))
        self.assertEqual(self.run_one("Rafael E Cruz", "Senate"), ("Republican", "TX"))
        self.assertEqual(self.run_one("Hon. Michael Rulli", "House", "OH"), ("Republican", "OH"))

    def test_compound_surname_does_not_collide_with_shorter_one(self):
        self.assertEqual(self.run_one("Hon. April McClain Delaney", "House", "MD")[0], "Democrat")
        self.assertEqual(self.run_one("Hon. Lisa McClain", "House", "MI")[0], "Republican")

    def test_state_disambiguates_same_name_and_ambiguity_stays_blank(self):
        self.assertEqual(self.run_one("Hon. Jonathan Jackson", "House", "IL")[0], "Democrat")
        self.assertEqual(self.run_one("Hon. Jonathan Jackson", "House", "")[0], "")  # ambiguous

    def test_wrong_chamber_unknown_name_and_existing_party_untouched(self):
        self.assertEqual(self.run_one("Sheldon Whitehouse", "House")[0], "")
        self.assertEqual(self.run_one("Alan Armstrong", "Senate")[0], "")
        keep = bpf.enrich_party([{"name": "John Boozman", "chamber": "Senate", "state": "AR", "party": "Independent"}], LEGS)
        self.assertEqual(keep[0]["party"], "Independent")

    def test_empty_metadata_leaves_party_blank(self):
        self.assertEqual(self.run_one("John Boozman", "Senate", legs=[])[0], "")


if __name__ == "__main__":
    unittest.main()
