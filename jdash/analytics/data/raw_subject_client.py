"""HTTP client for raw subject data hosted by another JDash instance."""

import os
from email.message import Message
from urllib.parse import quote, urlparse

import requests
from django.conf import settings

from .raw_subject_data import (
    RawSubjectDataError,
    RawSubjectDataNotFound,
    RawSubjectDataValidationError,
)


class RawSubjectApiConfigurationError(RawSubjectDataError):
    """Raised when remote raw-data access is not configured correctly."""


class RawSubjectApiAuthenticationError(RawSubjectDataError):
    """Raised when the remote API rejects the configured credentials."""


class RawSubjectApiClient:
    """Retrieve bounded raw-data payloads without exposing the API key."""

    def __init__(
        self,
        base_url,
        api_key,
        connect_timeout=5,
        read_timeout=30,
        download_read_timeout=300,
        verify_ssl=True,
        chunk_size=1024 * 1024,
        session=None,
    ):
        self.base_url = str(base_url or "").rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.connect_timeout = float(connect_timeout)
        self.read_timeout = float(read_timeout)
        self.download_read_timeout = float(download_read_timeout)
        self.verify_ssl = bool(verify_ssl)
        self.chunk_size = max(8192, int(chunk_size))
        self._session = session
        self._validate_configuration()

    @classmethod
    def from_settings(cls):
        return cls(
            base_url=getattr(settings, "RAW_DATA_API_BASE_URL", ""),
            api_key=getattr(settings, "RAW_DATA_API_KEY", ""),
            connect_timeout=getattr(
                settings,
                "RAW_DATA_API_CONNECT_TIMEOUT_SECONDS",
                5,
            ),
            read_timeout=getattr(settings, "RAW_DATA_API_READ_TIMEOUT_SECONDS", 30),
            download_read_timeout=getattr(
                settings,
                "RAW_DATA_API_DOWNLOAD_TIMEOUT_SECONDS",
                300,
            ),
            verify_ssl=getattr(settings, "RAW_DATA_API_VERIFY_SSL", True),
            chunk_size=getattr(
                settings,
                "RAW_DATA_API_DOWNLOAD_CHUNK_SIZE",
                1024 * 1024,
            ),
        )

    def _validate_configuration(self):
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RawSubjectApiConfigurationError(
                "RAW_DATA_API_BASE_URL must be an absolute HTTP(S) URL."
            )
        if not self.api_key:
            raise RawSubjectApiConfigurationError("RAW_DATA_API_KEY is not configured.")
        if self.connect_timeout <= 0 or self.read_timeout <= 0:
            raise RawSubjectApiConfigurationError("Raw-data API timeouts must be positive.")
        if self.download_read_timeout <= 0:
            raise RawSubjectApiConfigurationError(
                "The raw-data download timeout must be positive."
            )

    def _endpoint(self, study_name, subject_id, operation):
        study = quote(str(study_name or ""), safe="")
        subject = quote(str(subject_id or ""), safe="")
        return (
            f"{self.base_url}/raw-data/studies/{study}/subjects/"
            f"{subject}/{operation}/"
        )

    def _headers(self):
        return {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }

    def _open_session(self):
        if self._session is not None:
            return self._session, False
        return requests.Session(), True

    @staticmethod
    def _error_detail(response):
        try:
            payload = response.json()
        except (ValueError, TypeError):
            return ""
        if isinstance(payload, dict):
            return str(payload.get("detail") or "").strip()
        return ""

    def _raise_for_response(self, response):
        if 200 <= response.status_code < 300:
            return
        detail = self._error_detail(response)
        if response.status_code == 400:
            raise RawSubjectDataValidationError(
                detail or "The raw-data API rejected the request."
            )
        if response.status_code == 404:
            raise RawSubjectDataNotFound(
                detail or "Raw data was not found for this subject."
            )
        if response.status_code in {401, 403}:
            raise RawSubjectApiAuthenticationError(
                "The raw-data API credentials or permissions were rejected."
            )
        raise RawSubjectDataError(
            detail or f"The raw-data API returned HTTP {response.status_code}."
        )

    def _request_json(self, url, params=None):
        session, owns_session = self._open_session()
        response = None
        try:
            response = session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=(self.connect_timeout, self.read_timeout),
                verify=self.verify_ssl,
                allow_redirects=False,
            )
            self._raise_for_response(response)
            try:
                payload = response.json()
            except (ValueError, TypeError) as exc:
                raise RawSubjectDataError(
                    "The raw-data API returned an invalid JSON response."
                ) from exc
            if not isinstance(payload, dict):
                raise RawSubjectDataError(
                    "The raw-data API returned an unexpected response."
                )
            return payload
        except requests.Timeout as exc:
            raise RawSubjectDataError("The raw-data API request timed out.") from exc
        except requests.RequestException as exc:
            raise RawSubjectDataError("The raw-data API could not be reached.") from exc
        finally:
            if response is not None:
                response.close()
            if owns_session:
                session.close()

    def metadata(self, study_name, subject_id):
        return self._request_json(
            self._endpoint(study_name, subject_id, "sensors")
        )

    def series(
        self,
        study_name,
        subject_id,
        sensor,
        metric=None,
        statistic="mean",
        resolution="day",
        start=None,
        end=None,
        period_days=None,
    ):
        params = {
            "sensor": sensor,
            "metric": metric,
            "statistic": statistic,
            "resolution": resolution,
            "start": start,
            "end": end,
            "days": period_days,
        }
        return self._request_json(
            self._endpoint(study_name, subject_id, "series"),
            params={key: value for key, value in params.items() if value is not None},
        )

    @staticmethod
    def _download_filename(response, subject_id):
        disposition = response.headers.get("Content-Disposition", "")
        message = Message()
        message["Content-Disposition"] = disposition
        filename = message.get_filename()
        filename = os.path.basename(str(filename or "").strip())
        return filename or f"{subject_id}_raw_data.zip"

    def download(self, study_name, subject_id):
        session, owns_session = self._open_session()
        response = None
        try:
            response = session.get(
                self._endpoint(study_name, subject_id, "download"),
                headers={"Accept": "application/zip", "X-API-Key": self.api_key},
                timeout=(self.connect_timeout, self.download_read_timeout),
                verify=self.verify_ssl,
                allow_redirects=False,
                stream=True,
            )
            self._raise_for_response(response)
        except requests.Timeout as exc:
            if response is not None:
                response.close()
            if owns_session:
                session.close()
            raise RawSubjectDataError("The raw-data API download timed out.") from exc
        except requests.RequestException as exc:
            if response is not None:
                response.close()
            if owns_session:
                session.close()
            raise RawSubjectDataError("The raw-data API could not be reached.") from exc
        except RawSubjectDataError:
            if response is not None:
                response.close()
            if owns_session:
                session.close()
            raise

        filename = self._download_filename(response, subject_id)
        content_type = response.headers.get("Content-Type") or "application/zip"

        def chunks():
            try:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        yield chunk
            except requests.RequestException as exc:
                raise RawSubjectDataError(
                    "The raw-data API download was interrupted."
                ) from exc
            finally:
                response.close()
                if owns_session:
                    session.close()

        return chunks(), filename, content_type
