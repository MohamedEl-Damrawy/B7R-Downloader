from __future__ import annotations

import importlib
import os
import unittest
from tempfile import TemporaryDirectory


class TestPaths(unittest.TestCase):
    def test_paths_use_localappdata(self):
        with TemporaryDirectory() as td:
            os.environ["LOCALAPPDATA"] = td
            import app.core.paths as paths
            importlib.reload(paths)

            app_dir = paths.get_app_data_dir()
            self.assertEqual(app_dir, paths.Path(td) / "VeloDownloader")
            self.assertTrue(app_dir.exists())
            self.assertEqual(paths.get_database_path(), app_dir / "velo.db")
            self.assertTrue(paths.get_log_dir().exists())
            self.assertTrue(paths.get_cache_dir().exists())
            self.assertTrue(paths.get_temp_dir().exists())
            self.assertTrue(paths.get_default_download_dir().exists())


if __name__ == "__main__":
    unittest.main()
