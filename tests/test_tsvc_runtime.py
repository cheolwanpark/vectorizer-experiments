import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TSVC_RUNTIME = REPO_ROOT / "emulator" / "run" / "common" / "tsvc_runtime.c"


class TSVCRuntimeTest(unittest.TestCase):
    def test_runtime_provides_init_arrays_for_shared_harnesses(self):
        source = TSVC_RUNTIME.read_text(encoding="utf-8")
        self.assertIn("void init_arrays(void)", source)


if __name__ == "__main__":
    unittest.main()
