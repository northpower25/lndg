from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from gui.backends.interfaces import BackendCapabilities
from gui.backends.registry import get_active_backend, set_active_backend
from gui.domain import SpliceAction
from gui.models import ChangeLog, Policy, PolicyRun, Recommendation, SpliceLog


class _SpliceBackendStub:
    def __init__(self, can_splice: bool):
        self._can_splice = can_splice

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(can_splice=self._can_splice, supports_plugins=self._can_splice)

    def splice_in(self, channel_id: str, amount_sat: int, fee_rate: int) -> SpliceAction:
        return SpliceAction(
            channel_id=channel_id,
            direction="in",
            amount_sat=amount_sat,
            requested_at=datetime.now(tz=timezone.utc),
        )

    def splice_out(
        self, channel_id: str, amount_sat: int, destination: str, fee_rate: int
    ) -> SpliceAction:
        return SpliceAction(
            channel_id=channel_id,
            direction="out",
            amount_sat=amount_sat,
            requested_at=datetime.now(tz=timezone.utc),
        )

    def get_splice_status(self, splice_id: str) -> SpliceAction:
        return SpliceAction(
            channel_id="1",
            direction="in",
            amount_sat=1,
            requested_at=datetime.now(tz=timezone.utc),
        )


class Phase3ApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="phase3-user", password="phase3-pass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self._previous_backend = get_active_backend()

    def tearDown(self):
        import gui.backends.registry as registry

        registry._active_backend = self._previous_backend

    def test_recommendation_dryrun_endpoint_updates_model(self):
        rec = Recommendation.objects.create(
            rec_type=Recommendation.TYPE_REBALANCE,
            confidence=0.8,
            confidence_label=Recommendation.CONFIDENCE_HEURISTIC,
            risk_level=Recommendation.RISK_LOW,
        )
        response = self.client.post(f"/api/v2/recommendations/{rec.id}/dryrun/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        rec.refresh_from_db()
        self.assertIsInstance(rec.dry_run_result, dict)
        self.assertTrue(rec.dry_run_result["simulate"])

    def test_policy_run_endpoint_creates_run(self):
        policy = Policy.objects.create(name="test", policy_type=Policy.TYPE_NOTIFY, definition={})
        response = self.client.post(
            f"/api/v2/policies/{policy.id}/run/",
            {"simulate": True, "trigger_data": {"source": "test"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PolicyRun.objects.filter(policy=policy).count(), 1)
        self.assertEqual(ChangeLog.objects.filter(change_type="policy_notify", actor="policy:test").count(), 1)

    def test_policy_run_auto_fee_missing_channel_is_blocked(self):
        policy = Policy.objects.create(name="auto-fee", policy_type=Policy.TYPE_AUTO_FEE, definition={})
        response = self.client.post(
            f"/api/v2/policies/{policy.id}/run/",
            {"simulate": False, "trigger_data": {"source": "test"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "blocked")
        self.assertEqual(ChangeLog.objects.filter(change_type="policy_auto_fee", actor="policy:auto-fee").count(), 1)

    def test_splice_endpoints_require_capability(self):
        set_active_backend(_SpliceBackendStub(can_splice=False))
        response = self.client.post(
            "/api/v2/channels/123/splice/in/",
            {"amount_sat": 1000, "fee_rate": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_splice_in_creates_splice_log_and_changelog(self):
        set_active_backend(_SpliceBackendStub(can_splice=True))
        response = self.client.post(
            "/api/v2/channels/123/splice/in/",
            {"amount_sat": 1000, "fee_rate": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SpliceLog.objects.filter(channel_id="123", splice_type="in").count(), 1)
        self.assertEqual(ChangeLog.objects.filter(change_type="splice_in", target_channel_id="123").count(), 1)
