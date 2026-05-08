from django.test import TestCase

from gui.models import Policy


class Phase4PolicyTemplateTests(TestCase):
    def test_default_auto_fee_templates_exist(self):
        expected = {
            "Auto Fee – Conservative",
            "Auto Fee – Balanced",
            "Auto Fee – Revenue Seeking",
        }
        rows = list(Policy.objects.filter(name__in=expected, policy_type=Policy.TYPE_AUTO_FEE))
        self.assertEqual({row.name for row in rows}, expected)
        self.assertTrue(all(row.dry_run for row in rows))
