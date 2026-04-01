import unittest
from pathlib import Path

from scripts import emulate


class EmulateDockerCommandTest(unittest.TestCase):
    def test_build_emulate_docker_command_mounts_host_tsvc_src(self):
        root = Path("/repo")
        out_dir = root / "artifacts" / "emulate" / "s111" / "stamp"
        source = root / "artifacts" / "generated-tsvc-kernels" / "s111.c"

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


if __name__ == "__main__":
    unittest.main()
