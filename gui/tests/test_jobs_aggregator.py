from asgiref.sync import async_to_sync
from django.test import TestCase
from django.utils import timezone

from gui.jobs.aggregator import aggregate_forwarding_windows
from gui.models import FailedHTLCs, ForwardingAggregate, Forwards


class AggregatorJobTests(TestCase):
    def setUp(self):
        now = timezone.now()
        Forwards.objects.create(
            forward_date=now,
            chan_id_in="111",
            chan_id_out="222",
            chan_in_alias="in",
            chan_out_alias="out",
            amt_in_msat=1200,
            amt_out_msat=1000,
            fee=2.0,
            inbound_fee=0.0,
        )
        FailedHTLCs.objects.create(
            timestamp=now,
            amount=100,
            chan_id_in="111",
            chan_id_out="222",
            wire_failure=0,
            failure_detail=0,
            missed_fee=0.0,
        )

    def test_aggregate_forwarding_windows_creates_rows(self):
        upserted = async_to_sync(aggregate_forwarding_windows)(windows=("1d",))
        self.assertEqual(upserted, 1)
        aggregate = ForwardingAggregate.objects.get(window="1d", channel_id="222")
        self.assertEqual(aggregate.in_msat, 1200)
        self.assertEqual(aggregate.out_msat, 1000)
        self.assertEqual(aggregate.fees_msat, 2000)
        self.assertEqual(aggregate.forward_count, 1)
        self.assertEqual(aggregate.fail_count, 1)

    def test_aggregate_forwarding_windows_is_idempotent(self):
        async_to_sync(aggregate_forwarding_windows)(windows=("1d",))
        async_to_sync(aggregate_forwarding_windows)(windows=("1d",))
        self.assertEqual(ForwardingAggregate.objects.count(), 1)
