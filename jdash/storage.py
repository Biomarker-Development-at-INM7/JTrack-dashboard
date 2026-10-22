from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class JDashManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """Fingerprint static assets without resolving optional source maps.

    Some bundled Dash dependencies reference source-map files that their
    packages do not ship. Source maps are debugging aids and are not required
    by the browser, so they should not make production ``collectstatic`` fail.
    """

    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            # Temporary fallback for legacy/static references
            return name

    patterns = (
        (
            "*.css",
            (
                r"(?P<matched>url\(['\"]{0,1}\s*(?P<url>.*?)[\"']{0,1}\))",
                (
                    r"(?P<matched>@import\s*[\"']\s*(?P<url>.*?)[\"'])",
                    '@import url("%(url)s")',
                ),
            ),
        ),
    )