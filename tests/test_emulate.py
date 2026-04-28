import unittest
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import emulate


class EmulateDockerCommandTest(unittest.TestCase):
    def test_build_emulate_docker_command_mounts_host_tsvc_src(self):
        root = Path("/repo")
        out_dir = root / "artifacts" / "emulate" / "s111" / "stamp"
        source = root / "emulator" / "run" / "src" / "generated" / "s111.c"

        docker_cmd = emulate.build_emulate_docker_command(
            root=root,
            out_dir=out_dir,
            source=source,
            image="example:latest",
            len_1d=4096,
            lmul=1,
            use_vf="fixed:1",
            effective_timeout=1800,
        )

        self.assertIn(
            f"{root / 'emulator' / 'benchmarks' / 'TSVC_2' / 'src'}:{emulate.CONTAINER_TSVC_SRC_ROOT}:ro",
            docker_cmd,
        )
        self.assertIn("example:latest", docker_cmd)
        self.assertIn(
            f"{emulate.CONTAINER_PROJECT_ROOT / source.relative_to(root)}",
            docker_cmd[-1],
        )
        self.assertIn(
            f"--build-out-dir={emulate.CONTAINER_BUILD_OUTPUT_ROOT}",
            docker_cmd[-1],
        )

    def test_build_emulate_docker_command_passes_extra_opt_flags(self):
        root = Path("/repo")
        out_dir = root / "artifacts" / "emulate" / "s111" / "stamp"
        source = root / "emulator" / "run" / "src" / "generated" / "s111.c"

        docker_cmd = emulate.build_emulate_docker_command(
            root=root,
            out_dir=out_dir,
            source=source,
            image="example:latest",
            len_1d=4096,
            lmul=1,
            use_vf="fixed:1",
            effective_timeout=1800,
            extra_opt_flags="-precise-mem-cost -gather-scatter-overhead=3",
        )

        self.assertIn("--optflags='-precise-mem-cost -gather-scatter-overhead=3'", docker_cmd[-1])

    def test_load_build_artifact_texts_reads_persisted_build_outputs(self):
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            build_dir = out_dir / "build"
            build_dir.mkdir()
            workload = build_dir / "s000_xiangshan.KunminghuV2Config_lmul1_vffixed:4.elf"
            workload.write_text("", encoding="utf-8")
            expected = {
                "opt_ll_text": "opt",
                "asm_text": "asm",
            }
            for field_name, suffix in emulate.BUILD_ARTIFACT_SUFFIXES.items():
                artifact_path = build_dir / f"{workload.stem}{suffix}"
                artifact_path.write_text(expected[field_name], encoding="utf-8")

            texts = emulate.load_build_artifact_texts(
                out_dir,
                str(emulate.CONTAINER_BUILD_OUTPUT_ROOT / workload.name),
            )

        self.assertEqual(texts, expected)

    def test_resolve_source_path_accepts_arbitrary_repo_c_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "emulator" / "run" / "src" / "dlmul-synthesis" / "microbench" / "mb1_switch.c"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("void kernel(void) {}\n", encoding="utf-8")

            resolved = emulate.resolve_source_path(root, source)

        self.assertEqual(resolved, source.resolve())

    def test_resolve_source_path_accepts_arbitrary_repo_assembly_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "emulator" / "run" / "out" / "kernel.s"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(".globl kernel\nkernel:\n\tret\n", encoding="utf-8")

            resolved = emulate.resolve_source_path(root, source)
            emulate.validate_source_suffix(resolved)

        self.assertEqual(resolved, source.resolve())

    def test_main_accepts_source_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "kernel.s"
            source.write_text(".globl kernel\nkernel:\n\tret\n", encoding="utf-8")
            summary = {
                "benchmark": "kernel",
                "simulator_target": emulate.SIM_TARGET,
                "use_vf": "",
                "effective_timeout_s": 1800,
                "kernel_cycles": 1,
                "total_cycles": 2,
                "wall_time_s": 3.0,
                "sim_speed_khz": 4.0,
                "artifact_dir": str(root / "artifacts"),
            }

            with patch.object(emulate, "repo_root", return_value=root):
                with patch.object(
                    emulate,
                    "run_emulate_source",
                    return_value={"summary": summary, "failed": False},
                ) as mocked:
                    with patch("sys.argv", ["emulate.py", "--source", "kernel.s"]):
                        with patch("sys.stdout", new_callable=StringIO):
                            emulate.main()

        mocked.assert_called_once()
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["benchmark"], "kernel")
        self.assertEqual(kwargs["source"], source.resolve())

    def test_resolve_benchmark_input_prefers_manifest_for_manifest_workloads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload_dir = root / "emulator" / "run" / "src" / "npb" / "npb_is_s"
            workload_dir.mkdir(parents=True, exist_ok=True)
            (workload_dir / "is.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (workload_dir / "helper.c").write_text("void helper(void) {}\n", encoding="utf-8")
            manifest = workload_dir / "manifest.yaml"
            manifest.write_text(
                json.dumps(
                    {
                        "name": "npb_is_s",
                        "entry": {"mode": "main", "symbol": "main"},
                        "sources": ["is.c", "helper.c"],
                        "build": {"analysis_source": "is.c"},
                    }
                ),
                encoding="utf-8",
            )

            resolved = emulate.resolve_benchmark_input(root, "npb_is_s")

        self.assertEqual(resolved, manifest.resolve())


if __name__ == "__main__":
    unittest.main()
