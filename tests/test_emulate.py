import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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


if __name__ == "__main__":
    unittest.main()
