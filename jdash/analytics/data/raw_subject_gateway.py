"""Select local or remote access for subject-level raw data."""

from django.conf import settings

from .raw_subject_client import RawSubjectApiClient, RawSubjectApiConfigurationError
from .raw_subject_data import (
    RawSubjectDataError,
    raw_download_target,
    stream_directory_as_zip,
    subject_raw_metadata as local_subject_raw_metadata,
    subject_sensor_series as local_subject_sensor_series,
    zip_command_available,
)


def raw_data_backend():
    backend = str(getattr(settings, "RAW_DATA_BACKEND", "local") or "local").lower()
    if backend not in {"local", "api"}:
        raise RawSubjectApiConfigurationError(
            "RAW_DATA_BACKEND must be either 'local' or 'api'."
        )
    return backend


def _api_client():
    return RawSubjectApiClient.from_settings()


def subject_raw_metadata(study_name, subject_id):
    if raw_data_backend() == "api":
        return _api_client().metadata(study_name, subject_id)
    return local_subject_raw_metadata(study_name, subject_id)


def subject_sensor_series(
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
    if raw_data_backend() == "api":
        return _api_client().series(
            study_name,
            subject_id,
            sensor,
            metric=metric,
            statistic=statistic,
            resolution=resolution,
            start=start,
            end=end,
            period_days=period_days,
        )
    return local_subject_sensor_series(
        study_name,
        subject_id,
        sensor,
        metric=metric,
        statistic=statistic,
        resolution=resolution,
        start=start,
        end=end,
        period_days=period_days,
    )


def subject_raw_download(study_name, subject_id):
    if raw_data_backend() == "api":
        return _api_client().download(study_name, subject_id)
    if not zip_command_available():
        raise RawSubjectDataError("The server ZIP utility is unavailable.")
    directory, filename = raw_download_target(study_name, subject_id)
    return stream_directory_as_zip(directory), filename, "application/zip"
