from django.test import (
    RequestFactory,
    SimpleTestCase,
    override_settings,
)
from django.urls import Resolver404, resolve
from django.utils import translation


class LanguageURLTests(SimpleTestCase):
    """
    Tests the internal Django URL structure.

    Important:

    FORCE_SCRIPT_NAME is a deployment prefix.

    Therefore Django should resolve:

        /en/login/
        /de/login/

    and NOT:

        /de/dev/login/
        /en/dev/login/
    """


    # --------------------------------------------------------------
    # Normal language URLs
    # --------------------------------------------------------------

    def test_english_login_url_resolves(self):
        with translation.override("en"):
            match = resolve("/en/login/")

        self.assertIsNotNone(match)


    def test_german_login_url_resolves(self):
        with translation.override("de"):
            match = resolve("/de/login/")

        self.assertIsNotNone(match)


    # --------------------------------------------------------------
    # Duplicate /dev must NEVER become a Django route
    # --------------------------------------------------------------

    def test_english_duplicate_dev_does_not_resolve(self):
        with translation.override("en"):
            with self.assertRaises(Resolver404):
                resolve("/en/dev/login/")


    def test_german_duplicate_dev_does_not_resolve(self):
        with translation.override("de"):
            with self.assertRaises(Resolver404):
                resolve("/de/dev/login/")


    # --------------------------------------------------------------
    # Development deployment
    # --------------------------------------------------------------

    @override_settings(
        FORCE_SCRIPT_NAME="/dev"
    )
    def test_dev_external_path_contains_dev_once(self):
        factory = RequestFactory()

        request = factory.get(
            "/de/login/"
        )

        self.assertEqual(
            request.path_info,
            "/de/login/",
        )

        self.assertEqual(
            request.path,
            "/dev/de/login/",
        )


    @override_settings(
        FORCE_SCRIPT_NAME="/dev"
    )
    def test_dev_english_external_path_contains_dev_once(self):
        factory = RequestFactory()

        request = factory.get(
            "/en/login/"
        )

        self.assertEqual(
            request.path_info,
            "/en/login/",
        )

        self.assertEqual(
            request.path,
            "/dev/en/login/",
        )


    # --------------------------------------------------------------
    # Production deployment
    # --------------------------------------------------------------

    @override_settings(
        FORCE_SCRIPT_NAME=None
    )
    def test_prod_german_has_no_dev_prefix(self):
        factory = RequestFactory()

        request = factory.get(
            "/de/login/"
        )

        self.assertEqual(
            request.path_info,
            "/de/login/",
        )

        self.assertEqual(
            request.path,
            "/de/login/",
        )


    @override_settings(
        FORCE_SCRIPT_NAME=None
    )
    def test_prod_english_has_no_dev_prefix(self):
        factory = RequestFactory()

        request = factory.get(
            "/en/login/"
        )

        self.assertEqual(
            request.path_info,
            "/en/login/",
        )

        self.assertEqual(
            request.path,
            "/en/login/",
        )


    # --------------------------------------------------------------
    # Resolver should work identically in dev and prod
    # --------------------------------------------------------------

    @override_settings(
        FORCE_SCRIPT_NAME="/dev"
    )
    def test_dev_path_info_resolves(self):
        factory = RequestFactory()

        request = factory.get(
            "/de/login/"
        )

        with translation.override("de"):
            match = resolve(
                request.path_info
            )

        self.assertIsNotNone(match)


    @override_settings(
        FORCE_SCRIPT_NAME=None
    )
    def test_prod_path_info_resolves(self):
        factory = RequestFactory()

        request = factory.get(
            "/de/login/"
        )

        with translation.override("de"):
            match = resolve(
                request.path_info
            )

        self.assertIsNotNone(match)
