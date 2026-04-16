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
                return 0, "LV: VPlan[0] VFs={4}\nLV: VF=4 cost=8 compare=2000\nLV: selected VF=4 plan=0\n"

            with patch.object(vplan_explain, "repo_root", return_value=root):
                with patch.object(vplan_explain, "run_container_and_capture", side_effect=fake_run_container):
                    result = vplan_explain.run_vplan_explain(
                        bench="s123",
                        image="example:latest",
                        ensure_image=False,
                        output_root=str(root / "artifacts" / "vplan"),
                    )

        inner_command = captured_command["command"][-1]
        self.assertIn("llvm_pipeline.py", inner_command)
        self.assertIn("emit-prevec", inner_command)
        self.assertIn("--source /workspace/host-project/emulator/run/src/s123.c", inner_command)
        self.assertIn("--compile-flag=-I", inner_command)
        self.assertIn("/workspace/host-project/emulator/run/common", inner_command)
        self.assertEqual(result["source"], str(source))
        self.assertEqual(result["source_kind"], "manual")
        self.assertEqual(result["function_name"], "kernel")
        self.assertEqual(result["vf_candidates"][0]["compare"], "2000")

    def test_run_vplan_explain_passes_extra_opt_flags_to_opt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "emulator" / "run" / "src" / "s123.c"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('#include "common.h"\nvoid kernel(void) { a[0] = b[0]; }\n', encoding="utf-8")

            captured_command = {}

            def fake_run_container(command, log_path, *, echo_output=False):
                del log_path, echo_output
                captured_command["command"] = command
                return 0, "LV: VPlan[0] VFs={4}\nLV: VF=4 cost=8 compare=2000\nLV: selected VF=4 plan=0\n"

            with patch.object(vplan_explain, "repo_root", return_value=root):
                with patch.object(vplan_explain, "run_container_and_capture", side_effect=fake_run_container):
                    vplan_explain.run_vplan_explain(
                        bench="s123",
                        image="example:latest",
                        ensure_image=False,
                        output_root=str(root / "artifacts" / "vplan"),
                        extra_opt_flags="-precise-mem-cost -gather-scatter-overhead=3",
                    )

        inner_command = captured_command["command"][-1]
        self.assertIn('"$OPT_BIN" -precise-mem-cost -gather-scatter-overhead=3 -passes=loop-vectorize -vplan-explain -disable-output', inner_command)

    def test_parse_vplan_vfs_reads_compare_when_present(self):
        parsed = vplan_explain.parse_vplan_vfs(
            "\n".join(
                [
                    "LV: VPlan[1] VFs={2,4}",
                    "LV: VF=2 cost=7 compare=3500",
                    "LV: VF=4 cost=7 compare=1750",
                    "LV: selected VF=4 plan=1",
                ]
            )
        )

        self.assertEqual(
            parsed,
            [
                {
                    "raw_vf": "2",
                    "use_vf": "fixed:2",
                    "cost": "7",
                    "compare": "3500",
                    "plan_index": 1,
                    "selected": False,
                },
                {
                    "raw_vf": "4",
                    "use_vf": "fixed:4",
                    "cost": "7",
                    "compare": "1750",
                    "plan_index": 1,
                    "selected": True,
                },
            ],
        )

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
