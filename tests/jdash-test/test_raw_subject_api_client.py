from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from jdash.analytics.data.raw_subject_client import (
    RawSubjectApiAuthenticationError,
    RawSubjectApiClient,
    RawSubjectApiConfigurationError,
)
from jdash.analytics.data.raw_subject_data import (
    RawSubjectDataError,
    RawSubjectDataNotFound,
)
from jdash.analytics.data.raw_subject_gateway import (
    raw_data_backend,
    subject_raw_download,
    subject_raw_metadata,
    subject_sensor_series,
)
from jdash.analytics.callbacks.subject_raw_callbacks import (
    _period_options,
    _source_section_styles,
)
from jdash.analytics.figures.overview_figures import _available_subject_profile_streams
from jdash.views.analytics_views import download_subject_raw_data


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, chunks=None):
        self.status_code = status_code
        self.payload = payload
        self.headers = headers or {}
        self.chunks = chunks or []
        self.closed = False

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def iter_content(self, chunk_size):
        del chunk_size
        yield from self.chunks

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response

    def close(self):
        self.closed = True


class RawSubjectApiClientTests(SimpleTestCase):
    def api_client(self, response):
        self.session = FakeSession(response)
        return RawSubjectApiClient(
            "https://data.example/api/v1",
            "jdash_secret",
            session=self.session,
        )

    def test_metadata_uses_api_key_and_stable_study_name_endpoint(self):
        response = FakeResponse(payload={"study": "Study_A", "sources": {}})

        payload = self.api_client(response).metadata("Study_A", "Study_A_00001")

        self.assertEqual(payload["study"], "Study_A")
        url, kwargs = self.session.calls[0]
        self.assertEqual(
            url,
            "https://data.example/api/v1/raw-data/studies/Study_A/"
            "subjects/Study_A_00001/sensors/",
        )
        self.assertEqual(kwargs["headers"]["X-API-Key"], "jdash_secret")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(response.closed)

    def test_series_forwards_only_supplied_bounded_options(self):
        response = FakeResponse(payload={"points": []})

        self.api_client(response).series(
            "Study_A",
            "Study_A_00001",
            "activity",
            metric="confidence",
            statistic="mean",
            resolution="hour",
            period_days=7,
        )

        _url, kwargs = self.session.calls[0]
        self.assertEqual(
            kwargs["params"],
            {
                "sensor": "activity",
                "metric": "confidence",
                "statistic": "mean",
                "resolution": "hour",
                "days": 7,
            },
        )

    def test_remote_not_found_and_authentication_errors_are_mapped(self):
        missing = self.api_client(
            FakeResponse(status_code=404, payload={"detail": "No raw data."})
        )
        with self.assertRaisesRegex(RawSubjectDataNotFound, "No raw data"):
            missing.metadata("Study_A", "Study_A_00001")

        forbidden = self.api_client(
            FakeResponse(status_code=403, payload={"detail": "Denied"})
        )
        with self.assertRaises(RawSubjectApiAuthenticationError):
            forbidden.metadata("Study_A", "Study_A_00001")

    def test_invalid_json_is_rejected(self):
        client = self.api_client(FakeResponse(payload=ValueError("not json")))

        with self.assertRaisesRegex(RawSubjectDataError, "invalid JSON"):
            client.metadata("Study_A", "Study_A_00001")

    def test_download_is_streamed_and_response_is_closed_after_iteration(self):
        response = FakeResponse(
            payload=None,
            headers={
                "Content-Disposition": "attachment; filename=subject_raw.zip",
                "Content-Type": "application/zip",
            },
            chunks=[b"first", b"", b"second"],
        )
        client = self.api_client(response)

        stream, filename, content_type = client.download(
            "Study_A",
            "Study_A_00001",
        )

        self.assertEqual(filename, "subject_raw.zip")
        self.assertEqual(content_type, "application/zip")
        self.assertEqual(list(stream), [b"first", b"second"])
        self.assertTrue(response.closed)

    def test_configuration_requires_absolute_url_and_key(self):
        with self.assertRaises(RawSubjectApiConfigurationError):
            RawSubjectApiClient("/api/v1", "secret")
        with self.assertRaises(RawSubjectApiConfigurationError):
            RawSubjectApiClient("https://data.example/api/v1", "")


class RawSubjectGatewayTests(SimpleTestCase):
    def test_period_options_default_to_30_days_and_reach_study_duration(self):
        self.assertEqual(
            _period_options(14),
            [{"label": "Last 30 study days", "value": 30}],
        )
        self.assertEqual(
            [option["value"] for option in _period_options(95)],
            [30, 60, 90, 95],
        )

    def test_subject_source_sections_match_study_sensor_types(self):
        sensors = {
            "Mixed_Study": ["accelerometer", "garmin_HEART_RATE", "ema"],
            "Phone_Study": ["activity"],
        }

        self.assertEqual(
            _source_section_styles(sensors, "Mixed_Study"),
            ({"display": "block"}, {"display": "block"}, {"display": "block"}),
        )
        self.assertEqual(
            _source_section_styles(sensors, "Phone_Study"),
            ({"display": "block"}, {"display": "none"}, {"display": "none"}),
        )
        self.assertEqual(
            _available_subject_profile_streams(sensors, "Mixed_Study"),
            {"smartphone", "device_sensor", "ema"},
        )
        self.assertEqual(
            _available_subject_profile_streams(sensors, "Phone_Study"),
            {"smartphone"},
        )

    @override_settings(RAW_DATA_BACKEND="invalid")
    def test_backend_rejects_unknown_value(self):
        with self.assertRaises(RawSubjectApiConfigurationError):
            raw_data_backend()

    @override_settings(
        RAW_DATA_BACKEND="api",
        RAW_DATA_API_BASE_URL="https://data.example/api/v1",
        RAW_DATA_API_KEY="secret",
    )
    @patch("jdash.analytics.data.raw_subject_gateway.RawSubjectApiClient.from_settings")
    def test_api_backend_routes_metadata_and_series_to_remote_client(self, factory):
        client = factory.return_value
        client.metadata.return_value = {"sources": {}}
        client.series.return_value = {"points": []}

        metadata = subject_raw_metadata("Study_A", "Study_A_00001")
        series = subject_sensor_series(
            "Study_A",
            "Study_A_00001",
            "activity",
            metric="confidence",
        )

        self.assertEqual(metadata, {"sources": {}})
        self.assertEqual(series, {"points": []})
        client.metadata.assert_called_once_with("Study_A", "Study_A_00001")
        client.series.assert_called_once_with(
            "Study_A",
            "Study_A_00001",
            "activity",
            metric="confidence",
            statistic="mean",
            resolution="day",
            start=None,
            end=None,
            period_days=None,
        )

    @override_settings(
        RAW_DATA_BACKEND="api",
        RAW_DATA_API_BASE_URL="https://data.example/api/v1",
        RAW_DATA_API_KEY="secret",
    )
    @patch("jdash.analytics.data.raw_subject_gateway.RawSubjectApiClient.from_settings")
    def test_api_backend_routes_archive_download_to_remote_client(self, factory):
        factory.return_value.download.return_value = (
            iter([b"zip"]),
            "subject.zip",
            "application/zip",
        )

        result = subject_raw_download("Study_A", "Study_A_00001")

        self.assertEqual(result[1:], ("subject.zip", "application/zip"))
        factory.return_value.download.assert_called_once_with(
            "Study_A",
            "Study_A_00001",
        )


class RawSubjectDownloadViewTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get(
            "/en/analytics/Study_A/subject/Study_A_00001/raw-download/"
        )
        self.request.user = type(
            "User",
            (),
            {"is_authenticated": True},
        )()

    @patch("jdash.views.analytics_views.subject_raw_download")
    @patch("jdash.views.analytics_views.visible_studies_for_user")
    def test_dashboard_download_proxies_the_gateway_stream(self, visible, download):
        visible.return_value.filter.return_value.exists.return_value = True
        download.return_value = (
            iter([b"first", b"second"]),
            "subject.zip",
            "application/zip",
        )

        response = download_subject_raw_data(
            self.request,
            "Study_A",
            "Study_A_00001",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"firstsecond")
        self.assertIn("subject.zip", response["Content-Disposition"])
        download.assert_called_once_with("Study_A", "Study_A_00001")

    @patch("jdash.views.analytics_views.subject_raw_download")
    @patch("jdash.views.analytics_views.visible_studies_for_user")
    def test_dashboard_download_returns_503_when_remote_api_is_unavailable(
        self,
        visible,
        download,
    ):
        visible.return_value.filter.return_value.exists.return_value = True
        download.side_effect = RawSubjectDataError("Remote unavailable")

        response = download_subject_raw_data(
            self.request,
            "Study_A",
            "Study_A_00001",
        )

        self.assertEqual(response.status_code, 503)
