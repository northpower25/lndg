from django.test import SimpleTestCase

from gui.jobs.collector import normalize_snapshot_interval_minutes


class CollectorJobTests(SimpleTestCase):
    def test_uses_default_interval_when_not_set(self):
        self.assertEqual(normalize_snapshot_interval_minutes(None), 15)

    def test_uses_default_interval_when_invalid(self):
        self.assertEqual(normalize_snapshot_interval_minutes(0), 15)

    def test_keeps_positive_configured_interval(self):
        self.assertEqual(normalize_snapshot_interval_minutes(60), 60)
