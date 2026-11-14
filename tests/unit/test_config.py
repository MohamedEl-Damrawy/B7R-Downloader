from __future__ import annotations

import importlib
import unittest


class TestConfig(unittest.TestCase):
    def test_config_load_save_roundtrip(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            import os
            os.environ["LOCALAPPDATA"] = td
            import app.core.config as config
            import app.core.paths as paths

            importlib.reload(paths)
            importlib.reload(config)

            cfg = config.AppConfig.load()
            cfg.set("max_concurrent_downloads", "3")
            cfg.save()

            cfg2 = config.AppConfig.load()
            self.assertEqual(cfg2.get("max_concurrent_downloads"), "3")
            self.assertTrue(cfg2.config_path.exists())


if __name__ == "__main__":
    unittest.main()
