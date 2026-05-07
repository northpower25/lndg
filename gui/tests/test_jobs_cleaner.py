from datetime import timedelta

from asgiref.sync import async_to_sync
from django.test import TestCase
from django.utils import timezone

from gui.jobs.cleaner import clean_channel_snapshots
from gui.models import ChannelSnapshot


class CleanerJobTests(TestCase):
    def test_clean_channel_snapshots_removes_old_rows(self):
        now = timezone.now()
        ChannelSnapshot.objects.create(
            timestamp=now - timedelta(days=10),
            channel_id="old",
            local_balance_sat=1,
            remote_balance_sat=1,
            capacity_sat=2,
        )
        ChannelSnapshot.objects.create(
            timestamp=now,
            channel_id="new",
            local_balance_sat=1,
            remote_balance_sat=1,
            capacity_sat=2,
        )

        deleted = async_to_sync(clean_channel_snapshots)(retention_days=5)
        self.assertEqual(deleted, 1)
        self.assertTrue(ChannelSnapshot.objects.filter(channel_id="new").exists())
