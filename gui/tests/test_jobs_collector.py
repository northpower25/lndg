from asgiref.sync import async_to_sync
from django.test import SimpleTestCase, TestCase

from gui.domain import Channel
from gui.jobs.collector import collect_channel_snapshots, normalize_snapshot_interval_minutes
from gui.models import ChannelSnapshot


class CollectorJobTests(SimpleTestCase):
    def test_uses_default_interval_when_not_set(self):
        self.assertEqual(normalize_snapshot_interval_minutes(None), 15)

    def test_uses_default_interval_when_invalid(self):
        self.assertEqual(normalize_snapshot_interval_minutes(0), 15)

    def test_keeps_positive_configured_interval(self):
        self.assertEqual(normalize_snapshot_interval_minutes(60), 60)


class CollectorSnapshotTests(TestCase):
    class _FakeAdapter:
        def list_channels(self):
            return [
                Channel(
                    channel_id="123",
                    remote_pubkey="02abc",
                    capacity_sat=1_000_000,
                    local_balance_sat=600_000,
                    remote_balance_sat=400_000,
                    is_active=True,
                    is_open=True,
                )
            ]

    def test_collect_channel_snapshots_creates_snapshot_rows(self):
        created = async_to_sync(collect_channel_snapshots)(self._FakeAdapter())
        self.assertEqual(created, 1)
        snapshot = ChannelSnapshot.objects.get(channel_id="123")
        self.assertEqual(snapshot.local_balance_sat, 600_000)
        self.assertTrue(snapshot.is_active)
