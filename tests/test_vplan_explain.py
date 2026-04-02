import unittest
from pathlib import Path
from io import StringIO
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

    def test_main_keeps_summary_only_by_default(self):
        with patch(
            "sys.argv",
            ["vplan_explain.py", "--bench", "s000"],
        ):
            with patch.object(
                vplan_explain,
                "run_vplan_explain",
                return_value={"bench": "s000", "exit_code": 0, "vf_candidates": [1, 2]},
            ) as run_mock:
                with patch("sys.stdout", new_callable=StringIO) as stdout:
                    vplan_explain.main()

        self.assertFalse(run_mock.call_args.kwargs["echo_output"])
        self.assertEqual(stdout.getvalue().strip(), "s000: 2 VF(s)")

    def test_main_enables_full_output_when_verbose_requested(self):
        with patch(
            "sys.argv",
            ["vplan_explain.py", "--bench", "s000", "--verbose"],
        ):
            with patch.object(
                vplan_explain,
                "run_vplan_explain",
                return_value={"bench": "s000", "exit_code": 0, "vf_candidates": [1]},
            ) as run_mock:
                with patch("sys.stdout", new_callable=StringIO):
                    vplan_explain.main()

        self.assertTrue(run_mock.call_args.kwargs["echo_output"])


if __name__ == "__main__":
    unittest.main()
