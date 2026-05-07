from django.test import TestCase

from gui.models import ChangeLog, ChannelSnapshot, ForwardingAggregate


class Phase2ModelTests(TestCase):
    def test_channel_snapshot_has_composite_index(self):
        index_fields = [tuple(index.fields) for index in ChannelSnapshot._meta.indexes]
        self.assertIn(("chan_id", "timestamp"), index_fields)

    def test_forwarding_aggregate_unique_together(self):
        self.assertIn(
            ("window", "chan_id", "window_start"),
            ForwardingAggregate._meta.unique_together,
        )

    def test_change_log_defaults(self):
        entry = ChangeLog.objects.create(change_type="fee_update", actor="manual")
        self.assertEqual(entry.target_chan_id, "")
        self.assertEqual(entry.old_value, {})
        self.assertEqual(entry.new_value, {})
