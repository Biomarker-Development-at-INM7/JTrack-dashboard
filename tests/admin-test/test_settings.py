# tests/test_settings.py
from django.test import RequestFactory, SimpleTestCase
from django.conf import settings

from jdash.maintenance_middleware import MaintenanceModeMiddleware
from jdash.views.core_views import _password_reset_has_eligible_user

class SettingsTests(SimpleTestCase):
    def test_language_setting(self):
        self.assertIn(settings.LANGUAGE_CODE, ['en', 'de'])

    def test_installed_apps(self):
        self.assertIn('jdash', settings.INSTALLED_APPS)


class MaintenanceModeMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MaintenanceModeMiddleware(lambda request: None)

    def test_password_reset_paths_are_exempt(self):
        paths = [
            "/password-reset/",
            "/password-reset/done/",
            "/reset/MQ/sample-token/",
            "/reset/done/",
            "/en/password-reset/",
            "/en/reset/MQ/sample-token/",
            "/jdash/password-reset/",
            "/jdash/reset/MQ/sample-token/",
            "/en/jdash/reset/MQ/sample-token/",
        ]

        for path in paths:
            with self.subTest(path=path):
                request = self.factory.get(path)
                self.assertTrue(self.middleware._is_exempt_path(request))


class PasswordResetEligibilityTests(SimpleTestCase):
    class FakePasswordResetForm:
        def __init__(self, email, users):
            self.cleaned_data = {"email": email}
            self.users = users

        def get_users(self, email):
            return iter(self.users)

    def test_password_reset_requires_eligible_user_for_email(self):
        form = self.FakePasswordResetForm("known@example.com", [object()])
        self.assertTrue(_password_reset_has_eligible_user(form))

    def test_password_reset_rejects_unknown_email(self):
        form = self.FakePasswordResetForm("unknown@example.com", [])
        self.assertFalse(_password_reset_has_eligible_user(form))
