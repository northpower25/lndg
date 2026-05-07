from django.apps import apps
from django.core.management import call_command
from django.test import TestCase

from gui.models import LocalSettings


class ModelConventionsTests(TestCase):
    def test_all_gui_models_use_gui_app_label(self):
        for model in apps.get_app_config("gui").get_models():
            self.assertEqual(model._meta.app_label, "gui")

    def test_fixture_loading_works(self):
        call_command("loaddata", "gui/tests/fixtures/local_settings.json", verbosity=0)
        self.assertTrue(LocalSettings.objects.filter(key="GUI-GraphLinks").exists())
