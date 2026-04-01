import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import vplan_explain


class VPlanExplainTest(unittest.TestCase):
    def test_run_vplan_explain_uses_simplified_kernel_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "emulator" / "run" / "src" / "s123.c"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('#include "common.h"\nvoid kernel(void) { a[0] = b[0]; }\n', encoding="utf-8")

            captured_command = {}

            def fake_run_container(command, log_path, *, echo_output=False):
                del log_path, echo_output
                captured_command["command"] = command
                return 0, "LV: VF=4 cost=8\nLV: selected VF=4 plan=0\n"

            with patch.object(vplan_explain, "repo_root", return_value=root):
                with patch.object(vplan_explain, "run_container_and_capture", side_effect=fake_run_container):
                    result = vplan_explain.run_vplan_explain(
                        bench="s123",
                        image="example:latest",
                        ensure_image=False,
                        output_root=str(root / "artifacts" / "vplan"),
                    )

        inner_command = captured_command["command"][-1]
        self.assertIn("--func=kernel", inner_command)
        self.assertIn("-I /workspace/host-project/emulator/run/common", inner_command)
        self.assertEqual(result["source"], str(source))
        self.assertEqual(result["source_kind"], "manual")
        self.assertEqual(result["function_name"], "kernel")


if __name__ == "__main__":
    unittest.main()
