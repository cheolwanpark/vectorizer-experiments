import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import profile_all


class ProfileAllTest(unittest.TestCase):
    def test_main_uses_arch_and_scope_in_default_db_name(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            with patch("sys.argv", ["profile_all.py"]):
                with patch.object(profile_all.emulate, "repo_root", return_value=root):
                    with patch.object(profile_all.benchmark_sources, "discover_tsvc_benches", return_value=[]):
                        with patch.object(profile_all.emulate, "ensure_image_exists"):
                            with patch.object(profile_all.emulate_all, "load_vfs_data", return_value=({}, {})):
                                with patch.object(profile_all.emulate_all, "resolve_input_path", return_value=root / "artifacts" / "vfs.db"):
                                    profile_all.main()

            aggregate_dbs = list(root.glob("artifacts/profile-result-intel-tsvc-*.sqlite"))

        self.assertEqual(len(aggregate_dbs), 1)


if __name__ == "__main__":
    unittest.main()
