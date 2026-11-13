"""Pipeline telemetry must not change feed payloads or failure semantics."""
import ast
import logging
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_task():
    tree = ast.parse((ROOT / "scripts/run.py").read_text(encoding="utf-8"))
    target = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == "_timed_pipeline_task")
    namespace = {"time": __import__("time"), "log": logging.getLogger("test_pipeline_task")}
    exec(compile(ast.Module(body=[target], type_ignores=[]), "run.py", "exec"), namespace)
    return namespace["_timed_pipeline_task"]


class PipelineTaskTelemetryTests(unittest.TestCase):
    def test_preserves_return_identity_and_arguments(self):
        task = load_task()
        result = {"verified": [1, 2]}
        self.assertIs(task("insiders", lambda a, b=0: result if (a, b) == (7, 8) else None,
                           7, b=8), result)

    def test_preserves_exception_type_and_message(self):
        task = load_task()
        def broken():
            raise TimeoutError("upstream timed out")
        with self.assertRaisesRegex(TimeoutError, "upstream timed out"):
            task("congress", broken)

    def test_independent_feeds_and_news_have_names(self):
        source = (ROOT / "scripts/run.py").read_text(encoding="utf-8")
        for name in ('"analyst"', '"insiders"', '"congress"', '"news"'):
            self.assertIn(name, source)
        self.assertIn('PIPELINE_TASK done %s elapsed=%.1fs', source)


if __name__ == "__main__":
    unittest.main()
