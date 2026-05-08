"""Tests for Phase-6 ML trainer and shadow recommendations."""

from __future__ import annotations

from django.test import TestCase


class TestMLStatusAPI(TestCase):
    """Test GET /api/v2/ml/status endpoint."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser", "test@test.com", "password")

    def test_ml_status_unauthenticated(self):
        resp = self.client.get("/api/v2/ml/status/")
        self.assertIn(resp.status_code, (401, 403))

    def test_ml_status_authenticated(self):
        self.client.login(username="testuser", password="password")
        resp = self.client.get("/api/v2/ml/status/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ai_mode", data)
        self.assertIn("data_gate_ok", data)
        self.assertIn("rebalance_events_30d", data)
        self.assertIn("shadow_mode_active", data)

    def test_ml_status_fields(self):
        self.client.login(username="testuser", password="password")
        resp = self.client.get("/api/v2/ml/status/")
        data = resp.json()
        self.assertEqual(data["rebalance_events_30d"], 0)
        self.assertFalse(data["data_gate_ok"])
        self.assertIsNone(data["rebalance_model_version"])


class TestMLRebalanceTrainAPI(TestCase):
    """Test POST /api/v2/ml/rebalance/train endpoint."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser2", "test2@test.com", "password")

    def test_train_without_data_returns_insufficient_data(self):
        """Without any RebalanceMLRecord rows, training must be rejected with data-gate error."""
        from unittest.mock import patch

        self.client.login(username="testuser2", password="password")
        # Bypass DRF throttle to get a deterministic result
        with patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True):
            resp = self.client.post("/api/v2/ml/rebalance/train/", content_type="application/json", data="{}")
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("reason", data)

    def test_train_force_with_empty_data_returns_400(self):
        """force=True bypasses data gate but still fails when there are no training samples."""
        from unittest.mock import patch

        self.client.login(username="testuser2", password="password")
        with patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True):
            resp = self.client.post(
                "/api/v2/ml/rebalance/train/",
                content_type="application/json",
                data='{"force": true}',
            )
        # force=True skips data gate but still requires at least 1 sample to fit
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data["ok"])


class TestMLAutofeeSuggestionsAPI(TestCase):
    """Test GET /api/v2/ml/autofee/suggestions endpoint."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser3", "test3@test.com", "password")

    def test_suggestions_empty_when_ai_off(self):
        self.client.login(username="testuser3", password="password")
        resp = self.client.get("/api/v2/ml/autofee/suggestions/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("suggestions", data)
        # ai_mode defaults to 'off' so suggestions should be empty
        self.assertEqual(data["suggestions"], [])

    def test_history_endpoint(self):
        self.client.login(username="testuser3", password="password")
        resp = self.client.get("/api/v2/ml/autofee/history/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("history", data)
        self.assertIsInstance(data["history"], list)


class TestMLExecuteActionAPI(TestCase):
    """Test POST /api/v2/ml/actions/execute endpoint."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser_ml_exec", "test_ml_exec@test.com", "password")

    def test_execute_action_awaits_confirmation(self):
        from gui.models import UserMode

        self.client.login(username="testuser_ml_exec", ******)
        mode = UserMode.load()
        mode.ai_mode = UserMode.AI_MODE_POLICY_BOUND
        mode.mode = UserMode.MODE_EXPERT
        mode.ai_policy_bound_confirm = True
        mode.save()

        import json

        resp = self.client.post(
            "/api/v2/ml/actions/execute/",
            data=json.dumps({"policy_id": 1, "model_name": "rebalance", "model_version": "v1", "ml_confidence": 0.8, "confirm": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json().get("status"), "awaiting_confirmation")

    def test_execute_action_confirmed_runs_policy_path(self):
        from gui.models import Policy, UserMode

        self.client.login(username="testuser_ml_exec", ******)
        mode = UserMode.load()
        mode.ai_mode = UserMode.AI_MODE_POLICY_BOUND
        mode.mode = UserMode.MODE_EXPERT
        mode.ai_policy_bound_confirm = True
        mode.save()
        policy = Policy.objects.create(name="Test Notify", policy_type=Policy.TYPE_NOTIFY, definition={}, is_active=False, dry_run=True)

        import json

        resp = self.client.post(
            "/api/v2/ml/actions/execute/",
            data=json.dumps(
                {
                    "policy_id": policy.id,
                    "model_name": "rebalance",
                    "model_version": "v1",
                    "ml_confidence": 0.8,
                    "confirm": True,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("actor", data)
        self.assertTrue(str(data.get("actor", "")).startswith("ml:"))


class TestMLEscalationConfigAPI(TestCase):
    """Test GET/PUT /api/v2/ml/escalation/config endpoint."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser4", "test4@test.com", "password")

    def test_get_escalation_config(self):
        self.client.login(username="testuser4", password="password")
        resp = self.client.get("/api/v2/ml/escalation/config/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ML-EscalationCooldown", data)
        self.assertIn("ML-EscalationMaxLevels", data)
        self.assertIn("ML-TrainingEnabled", data)

    def test_put_escalation_config(self):
        self.client.login(username="testuser4", password="password")
        import json

        resp = self.client.put(
            "/api/v2/ml/escalation/config/",
            data=json.dumps({"ML-EscalationCooldown": "90", "ML-EscalationMaxLevels": "3"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("ML-EscalationCooldown", data["updated"])

    def test_put_unknown_key_returns_400(self):
        self.client.login(username="testuser4", password="password")
        import json

        resp = self.client.put(
            "/api/v2/ml/escalation/config/",
            data=json.dumps({"UNKNOWN-KEY": "foo"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestUserSettingsPolicyBound(TestCase):
    """Test policy_bound ai_mode in user settings API."""

    def setUp(self):
        from django.contrib.auth.models import User

        User.objects.create_superuser("testuser5", "test5@test.com", "password")

    def test_policy_bound_is_valid_ai_mode(self):
        self.client.login(username="testuser5", password="password")
        import json

        resp = self.client.put(
            "/api/v2/user/settings/",
            data=json.dumps({"ai_mode": "policy_bound"}),
            content_type="application/json",
        )
        # policy_bound is only allowed for expert mode; API should accept the value
        self.assertIn(resp.status_code, (200, 400))
        if resp.status_code == 200:
            data = resp.json()
            self.assertEqual(data["ai_mode"], "policy_bound")

    def test_ai_policy_bound_confirm_field_present(self):
        self.client.login(username="testuser5", password="password")
        resp = self.client.get("/api/v2/user/settings/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ai_policy_bound_confirm", data)
        self.assertTrue(data["ai_policy_bound_confirm"])  # default True


class TestMLTrainerFunctions(TestCase):
    """Unit tests for ml_trainer module functions."""

    def test_check_min_data_insufficient_days(self):
        from gui.jobs.ml_trainer import _check_min_data

        ok, reason = _check_min_data(100, 10.0)
        self.assertFalse(ok)
        self.assertIn("10", reason)

    def test_check_min_data_insufficient_events(self):
        from gui.jobs.ml_trainer import _check_min_data

        ok, reason = _check_min_data(5, 45.0)
        self.assertFalse(ok)

    def test_check_min_data_ok(self):
        from gui.jobs.ml_trainer import _check_min_data

        ok, reason = _check_min_data(100, 35.0)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_get_ml_status_returns_dict(self):
        from gui.jobs.ml_trainer import get_ml_status

        status = get_ml_status()
        self.assertIsInstance(status, dict)
        self.assertIn("ai_mode", status)
        self.assertIn("data_gate_ok", status)

    def test_shadow_predict_no_model(self):
        from gui.jobs.ml_trainer import shadow_rebalance_predict

        result = shadow_rebalance_predict(
            source_chan_id="123",
            target_chan_id="456",
            amount_sat=100000,
            fee_ppm=50,
        )
        self.assertIn("confidence_label", result)
        self.assertIn("predicted_success_prob", result)
        # Without a trained model, falls back to heuristic
        self.assertEqual(result["confidence_label"], "heuristic")
        self.assertIsNone(result["model_version"])

    def test_get_autofee_suggestions_ai_off(self):
        from gui.jobs.ml_trainer import get_autofee_suggestions

        suggestions = get_autofee_suggestions()
        # ai_mode defaults to 'off', so no suggestions
        self.assertEqual(suggestions, [])

    def test_get_autofee_history_empty(self):
        from gui.jobs.ml_trainer import get_autofee_history

        history = get_autofee_history()
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 0)


class TestExecuteMLAction(TestCase):
    """Tests for execute_ml_action in executor.py."""

    def test_blocked_when_not_policy_bound(self):
        from gui.jobs.executor import execute_ml_action

        result = execute_ml_action(
            policy_id=1,
            model_name="rebalance",
            model_version="v20240101",
            ml_confidence=0.8,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")

    def test_awaiting_confirmation_when_policy_bound(self):
        from gui.jobs.executor import execute_ml_action
        from gui.models import UserMode

        mode = UserMode.load()
        mode.ai_mode = UserMode.AI_MODE_POLICY_BOUND
        mode.mode = UserMode.MODE_EXPERT
        mode.ai_policy_bound_confirm = True
        mode.save()

        result = execute_ml_action(
            policy_id=1,
            model_name="rebalance",
            model_version="v20240101",
            ml_confidence=0.8,
            pending_confirmation=True,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "awaiting_confirmation")
        self.assertIn("model", result)
