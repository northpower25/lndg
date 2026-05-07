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
            chan_id="old",
            local_balance=1,
            remote_balance=1,
            capacity=2,
        )
        ChannelSnapshot.objects.create(
            timestamp=now,
            chan_id="new",
            local_balance=1,
            remote_balance=1,
            capacity=2,
        )

        deleted = async_to_sync(clean_channel_snapshots)(retention_days=5)
        self.assertEqual(deleted, 1)
        self.assertTrue(ChannelSnapshot.objects.filter(chan_id="new").exists())
