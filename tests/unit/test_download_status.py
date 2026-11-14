import unittest

from app.models.download_status import DownloadStatus, assert_transition, can_transition


class TestDownloadStatus(unittest.TestCase):
    def test_valid_transitions(self):
        self.assertTrue(can_transition(DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING))
        self.assertTrue(can_transition(DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED))
        self.assertTrue(can_transition(DownloadStatus.FAILED, DownloadStatus.QUEUED))

    def test_invalid_transition_raises(self):
        self.assertFalse(can_transition(DownloadStatus.COMPLETED, DownloadStatus.DOWNLOADING))
        with self.assertRaises(ValueError):
            assert_transition(DownloadStatus.COMPLETED, DownloadStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
