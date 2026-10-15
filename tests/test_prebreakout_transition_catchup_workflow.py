from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/refresh-prebreakout-forward-evidence.yml"


class PrebreakoutTransitionCatchupWorkflowTests(unittest.TestCase):
    def test_catchup_rebuild_is_archive_only_and_verified_before_publish(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        rebuild = source.index("python scripts/build_prebreakout_transitions.py")
        verify = source.index("python scripts/check_prebreakout_transitions.py", rebuild)
        evaluate = source.index("python scripts/refresh_prebreakout_forward_evidence.py", verify)
        stage = source.index("git add data/prebreakout-forward-evidence.json data/prebreakout-transitions.json", evaluate)
        publish = source.index("bash scripts/publish_with_retry.sh origin main", stage)
        self.assertLess(rebuild, verify)
        self.assertLess(verify, evaluate)
        self.assertLess(evaluate, stage)
        self.assertLess(stage, publish)
        self.assertIn("if: steps.publish_window.outputs.defer != 'true'", source)
        self.assertIn("python scripts/defer_main_publish_if_code_pr.py", source)

    def test_transition_builder_is_backed_by_immutable_slots(self):
        builder = (ROOT / "scripts/build_prebreakout_transitions.py").read_text(encoding="utf-8")
        self.assertIn('archive.glob("*/slots/*-slot*.json")', builder)
        self.assertIn('"historical_only":True', builder)


if __name__ == "__main__":
    unittest.main()
