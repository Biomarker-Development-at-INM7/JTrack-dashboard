# tests/test_settings.py
from django.test import SimpleTestCase
from django.conf import settings

class SettingsTests(SimpleTestCase):
    def test_language_setting(self):
        self.assertIn(settings.LANGUAGE_CODE, ['en', 'de'])

    def test_installed_apps(self):
        self.assertIn('jdash', settings.INSTALLED_APPS)