import unittest

from app.models.download_status import DownloadStatus, assert_transition, can_transition


class TestDownloadStatus(unittest.TestCase):
    def test_valid_transitions(self):
        self.assertTrue(can_transition(DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING))
        self.assertTrue(can_transition(DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED))
        self.assertTrue(can_transition(DownloadStatus.FAILED, DownloadStatus.QUEUED))

    def test_multi_file_and_fast_success_paths(self):
        # Phase 2 amendments: multi-file tasks loop PROCESSING -> DOWNLOADING,
        # and instant/cached successes can go EXTRACTING -> COMPLETED.
        self.assertTrue(can_transition(DownloadStatus.PROCESSING, DownloadStatus.DOWNLOADING))
        self.assertTrue(can_transition(DownloadStatus.EXTRACTING, DownloadStatus.COMPLETED))
        self.assertTrue(can_transition(DownloadStatus.QUEUED, DownloadStatus.EXTRACTING))

    def test_invalid_transition_raises(self):
        self.assertFalse(can_transition(DownloadStatus.COMPLETED, DownloadStatus.DOWNLOADING))
        with self.assertRaises(ValueError):
            assert_transition(DownloadStatus.COMPLETED, DownloadStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
