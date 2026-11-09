import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts/check_prebreakout_publication.py"
spec=importlib.util.spec_from_file_location("publication",p)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class FreshnessContract(unittest.TestCase):
 def test_fresh_with_consistent_observation(self):
  now=datetime(2026,10,28,12,tzinfo=timezone.utc)
  feed={"schema":"vestra_prebreakout_v1","generated_at":now.isoformat(),
        "attempted":300,"eligible_universe":1183,
        "daily_capacity_ceiling":{"max_distinct_daily":1183},
        "scan_slot_telemetry":{"rows_attempted":300},
        "scan_quality_audit":{"observed_24h_coverage_pct":36.86},
        "coverage_audit_24h":{"coverage_pct":36.86}}
  self.assertEqual(mod.assess_freshness(feed,now)["status"],"healthy")
  self.assertEqual(mod.assess_freshness({**feed,"daily_capacity_ceiling":{"max_distinct_daily":600}},now)["status"],"invalid")
  self.assertEqual(mod.assess_freshness(feed,now.replace(hour=23))["status"],"stale")
  self.assertEqual(mod.assess_freshness({**feed,"scan_slot_telemetry":{}},now)["status"],"invalid")
  self.assertEqual(mod.assess_freshness({**feed,"scan_quality_audit":{}},now)["status"],"invalid")
  self.assertEqual(mod.assess_freshness({**feed,"generated_at":"2026-10-28T12:00:00"},now)["status"],"invalid")
  bad={**feed,"coverage_audit_24h":{"coverage_pct":105.18},
       "scan_quality_audit":{"observed_24h_coverage_pct":105.18}}
  self.assertEqual(mod.assess_freshness(bad,now)["reason"],"impossible_coverage_pct")
  coherent={**feed,"eligible_universe":3,
            "daily_capacity_ceiling":{"max_distinct_daily":3},
            "coverage_audit_24h":{"coverage_pct":66.67,"distinct_ohlcv_tickers":4,
              "current_eligible_verified_distinct":2,"outside_current_universe_distinct":2},
            "scan_quality_audit":{"observed_24h_coverage_pct":66.67,
              "full_universe_verified":False}}
  self.assertEqual(mod.assess_freshness(coherent,now)["status"],"healthy")
  impossible={**coherent,"coverage_audit_24h":{**coherent["coverage_audit_24h"],
                "current_eligible_verified_distinct":4,"coverage_pct":133.33},
              "scan_quality_audit":{**coherent["scan_quality_audit"],
                "observed_24h_coverage_pct":133.33,"full_universe_verified":True}}
  self.assertEqual(mod.assess_freshness(impossible,now)["status"],"invalid")



class GateFunnelContract(unittest.TestCase):
 def feed(self):
  return {
   "schema":"vestra_prebreakout_v1",
   "generated_at":"2026-11-09T14:17:00+00:00",
   "attempted":300,"new_signals":1,"eligible_universe":1139,
   "daily_capacity_ceiling":{"max_distinct_daily":1139},
   "scan_slot_telemetry":{"rows_attempted":300},
   "coverage_audit_24h":{"coverage_pct":26.34,
                          "current_eligible_verified_distinct":300,
                          "outside_current_universe_distinct":0,
                          "distinct_ohlcv_tickers":300},
   "scan_quality_audit":{"observed_24h_coverage_pct":26.34,
                         "full_universe_verified":False},
   "gate_funnel":{
     "scope":"current_observed_slot_only",
     "method":"first_failing_gate_in_order_not_independent_gate_intersections",
     "observed_rows":298,
     "first_rejection_counts":{"moving_average_structure":296,
                                "passed_structural_gates":2},
     "structurally_passed":2,
     "currency_or_usd_liquidity_rejections_after_structural_pass":1,
     "missing_downloads_not_negative_evidence":True,
     "probability_or_forward_performance":None},
   "quality_filter_shadow":{"compared":298,"strict_eligible":2}
  }
 def test_coherent_funnel_separates_observed_from_unobserved(self):
  feed=self.feed()
  report=mod.assess_gate_funnel(feed,require=True)
  self.assertEqual(report["status"],"valid")
  self.assertEqual(report["not_observed_rows"],2)
  now=datetime(2026,11,9,15,tzinfo=timezone.utc)
  self.assertEqual(mod.assess_freshness(feed,now)["status"],"healthy")
 def test_modern_coverage_requires_explicit_current_universe_provenance(self):
  now=datetime(2026,11,9,15,tzinfo=timezone.utc)
  for field in ("current_eligible_verified_distinct","outside_current_universe_distinct",
                "distinct_ohlcv_tickers"):
   with self.subTest(field=field):
    feed=self.feed()
    del feed["coverage_audit_24h"][field]
    report=mod.assess_freshness(feed,now)
    self.assertEqual(report["reason"],"missing_modern_current_universe_coverage")
  for bad in (None, "false", 0, 1):
   with self.subTest(full_universe_verified=bad):
    feed=self.feed()
    feed["scan_quality_audit"]["full_universe_verified"]=bad
    self.assertEqual(mod.assess_freshness(feed,now)["reason"],
                     "missing_modern_current_universe_coverage")
  feed=self.feed()
  del feed["coverage_audit_24h"]["coverage_pct"]
  self.assertEqual(mod.assess_freshness(feed,now)["status"],"invalid")
  self.assertEqual(mod.assess_freshness(self.feed(),now)["status"],"healthy")
 def test_legacy_feed_can_still_be_read_without_modern_numerator(self):
  now=datetime(2026,11,7,15,tzinfo=timezone.utc)
  feed=self.feed()
  feed["generated_at"]=now.isoformat()
  del feed["coverage_audit_24h"]["current_eligible_verified_distinct"]
  del feed["coverage_audit_24h"]["outside_current_universe_distinct"]
  del feed["coverage_audit_24h"]["distinct_ohlcv_tickers"]
  self.assertEqual(mod.assess_freshness(feed,now)["status"],"healthy")
 def test_missing_funnel_in_modern_publication_is_unverifiable_not_valid(self):
  feed=self.feed();del feed["gate_funnel"]
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["reason"],"missing_modern_gate_funnel")
  self.assertEqual(mod.assess_freshness(feed,datetime(2026,11,9,15,tzinfo=timezone.utc))["status"],"invalid")
 def test_rejects_fabricated_coverage_and_inconsistent_gate_counts(self):
  for key,value in [("observed_rows",299),("structurally_passed",3),
                    ("currency_or_usd_liquidity_rejections_after_structural_pass",3)]:
   feed=self.feed();feed["gate_funnel"][key]=value
   self.assertEqual(mod.assess_gate_funnel(feed,require=True)["status"],"invalid")
  feed=self.feed();feed["quality_filter_shadow"]["compared"]=300
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["reason"],"inconsistent_gate_funnel_accounting")
  feed=self.feed();feed["gate_funnel"]["first_rejection_counts"]["missing_provider_bars"]=2
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["status"],"invalid")
 def test_unknown_is_not_a_probability_or_negative_signal(self):
  feed=self.feed();feed["gate_funnel"]["probability_or_forward_performance"]=0.87
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["reason"],"gate_funnel_provenance_or_probability")
  feed=self.feed();feed["gate_funnel"]["missing_downloads_not_negative_evidence"]=False
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["status"],"invalid")
  feed=self.feed();feed["new_signals"]=2
  self.assertEqual(mod.assess_gate_funnel(feed,require=True)["status"],"invalid")
 def test_old_archives_remain_readable_but_not_current_evidence(self):
  self.assertEqual(mod.assess_gate_funnel({},require=False)["status"],"legacy_without_gate_funnel")
  feed=self.feed();feed["generated_at"]="2026-11-07T14:17:00+00:00";del feed["gate_funnel"]
  self.assertEqual(mod.assess_freshness(feed,datetime(2026,11,9,15,tzinfo=timezone.utc))["status"],"stale")


class Contract(unittest.TestCase):
 def setup_files(self,root):
  d=root/"data";d.mkdir()
  ts="2026-10-15T14:15:00+00:00"
  signal={"ticker":"TEST","date":"2026-10-14","stage":"compressão"}
  feed={"schema":"vestra_prebreakout_v1","generated_at":ts,"scan_slot_utc":2,"signals":[signal]}
  index={"schema":"vestra_prebreakout_observations_v1","historical_only":True,"slots_considered":1,
         "observations":[{"ticker":"TEST","observed_at":ts,"signal_date":signal["date"],
                          "stage":signal["stage"],"current":False}]}
  slot=d/"prebreakout-history"/"2026"/"slots";slot.mkdir(parents=True)
  (slot/"2026-10-15-slot2.json").write_text(json.dumps(feed))
  (d/"prebreakout-signals.json").write_text(json.dumps(feed))
  (d/"prebreakout-observations.json").write_text(json.dumps(index))
  return d
 def setup_modern_publication(self,root):
  d=self.setup_files(root)
  stamp="2026-11-09T14:17:00+00:00"
  feed=GateFunnelContract().feed()
  feed["generated_at"]=stamp;feed["scan_slot_utc"]=2
  signal={"ticker":"TEST","date":"2026-11-06","stage":"compressão"}
  feed["signals"]=[signal]
  slot=d/"prebreakout-history"/"2026"/"slots"/"2026-11-09-slot2.json"
  slot.write_text(json.dumps(feed))
  (d/"prebreakout-signals.json").write_text(json.dumps(feed))
  index={"schema":"vestra_prebreakout_observations_v1","historical_only":True,
         "slots_considered":1,"observations":[{"ticker":"TEST","observed_at":stamp,
         "signal_date":signal["date"],"stage":signal["stage"],"current":False}]}
  (d/"prebreakout-observations.json").write_text(json.dumps(index))
  return d,feed,slot
 def test_modern_publication_rejects_impossible_coverage_despite_valid_funnel(self):
  with tempfile.TemporaryDirectory() as folder:
   d,feed,slot=self.setup_modern_publication(Path(folder))
   self.assertEqual(mod.verify(Path(folder))["verified_slot"],2)
   feed["coverage_audit_24h"].update({"coverage_pct":105.18,
      "current_eligible_verified_distinct":1198,"outside_current_universe_distinct":0,
      "distinct_ohlcv_tickers":1198})
   feed["scan_quality_audit"].update({"observed_24h_coverage_pct":105.18,
      "full_universe_verified":True})
   (d/"prebreakout-signals.json").write_text(json.dumps(feed))
   slot.write_text(json.dumps(feed))
   with self.assertRaisesRegex(ValueError,"invalid published scanner evidence"):
    mod.verify(Path(folder))
 def test_modern_publisher_blocks_missing_current_universe_evidence(self):
  with tempfile.TemporaryDirectory() as folder:
   d,feed,slot=self.setup_modern_publication(Path(folder))
   del feed["coverage_audit_24h"]["current_eligible_verified_distinct"]
   slot.write_text(json.dumps(feed))
   (d/"prebreakout-signals.json").write_text(json.dumps(feed))
   with self.assertRaisesRegex(ValueError,"missing_modern_current_universe_coverage"):
    mod.verify(Path(folder))
 def test_modern_publication_rejects_unreconciled_rolling_observations(self):
  with tempfile.TemporaryDirectory() as folder:
   d,feed,slot=self.setup_modern_publication(Path(folder))
   feed["coverage_audit_24h"]["outside_current_universe_distinct"]=2
   (d/"prebreakout-signals.json").write_text(json.dumps(feed))
   slot.write_text(json.dumps(feed))
   with self.assertRaisesRegex(ValueError,"inconsistent_current_universe_coverage"):
    mod.verify(Path(folder))
 def test_valid_publication(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.setup_files(root)
   self.assertEqual(mod.verify(root)["verified_slot"],2)
 def test_rejected_when_slot_missing_or_different(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=self.setup_files(root)
   (d/"prebreakout-history"/"2026"/"slots"/"2026-10-15-slot2.json").unlink()
   with self.assertRaises(FileNotFoundError):mod.verify(root)
 def test_rejected_when_history_promoted_or_dated_incorrectly(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=self.setup_files(root)
   file=d/"prebreakout-observations.json"
   data=json.loads(file.read_text());data["observations"][0]["current"]=True
   file.write_text(json.dumps(data))
   with self.assertRaises(ValueError):mod.verify(root)
if __name__=="__main__":unittest.main()
