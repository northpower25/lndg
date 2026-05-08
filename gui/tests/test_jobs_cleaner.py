from datetime import timedelta

from asgiref.sync import async_to_sync
from django.test import TestCase
from django.utils import timezone

from gui.jobs.cleaner import (
    clean_autofee_ml_records,
    clean_channel_snapshots,
    clean_rebalance_ml_records,
)
from gui.models import AutoFeeMLRecord, ChannelSnapshot, RebalanceMLRecord


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

    def test_clean_rebalance_ml_records_removes_old_rows(self):
        now = timezone.now()
        RebalanceMLRecord.objects.create(
            timestamp=now - timedelta(days=20),
            source_chan_id="1",
            target_chan_id="2",
            amount_sat=1000,
            fee_ppm=100,
            hour_of_day=1,
            day_of_week=2,
            success=False,
        )
        RebalanceMLRecord.objects.create(
            timestamp=now,
            source_chan_id="3",
            target_chan_id="4",
            amount_sat=1000,
            fee_ppm=100,
            hour_of_day=1,
            day_of_week=2,
            success=True,
        )

        deleted = async_to_sync(clean_rebalance_ml_records)(retention_days=10)
        self.assertEqual(deleted, 1)
        self.assertTrue(RebalanceMLRecord.objects.filter(source_chan_id="3").exists())

    def test_clean_autofee_ml_records_removes_old_rows(self):
        now = timezone.now()
        AutoFeeMLRecord.objects.create(
            timestamp=now - timedelta(days=20),
            chan_id="1",
            param_name="fee_rate",
            old_value=100,
            new_value=120,
        )
        AutoFeeMLRecord.objects.create(
            timestamp=now,
            chan_id="2",
            param_name="fee_rate",
            old_value=100,
            new_value=110,
        )

        deleted = async_to_sync(clean_autofee_ml_records)(retention_days=10)
        self.assertEqual(deleted, 1)
        self.assertTrue(AutoFeeMLRecord.objects.filter(chan_id="2").exists())
