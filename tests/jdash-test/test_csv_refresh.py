import os
import time

from jdash.config import runtime_config as config
from jdash.services.csv_refresh import request_study_csv_refresh


def _configure_paths(monkeypatch, tmp_path):
    storage = tmp_path / "storage"
    studies = tmp_path / "studies"
    requests = storage / "csv_requests"
    storage.mkdir()
    studies.mkdir()
    requests.mkdir()
    (studies / "study1").mkdir()
    monkeypatch.setattr(config, "storage_folder", str(storage))
    monkeypatch.setattr(config, "studies_folder", str(studies))
    monkeypatch.setattr(config, "csv_prefix", "dashboard_")
    return storage, requests


def test_recent_csv_does_not_request_refresh(monkeypatch, tmp_path):
    storage, requests = _configure_paths(monkeypatch, tmp_path)
    (storage / "dashboard_study1.csv").write_text("subject_name\n", encoding="utf-8")

    assert request_study_csv_refresh("study1") is True
    assert not (requests / "study1").exists()


def test_stale_csv_requests_refresh_without_waiting(monkeypatch, tmp_path):
    storage, requests = _configure_paths(monkeypatch, tmp_path)
    csv_path = storage / "dashboard_study1.csv"
    csv_path.write_text("subject_name\n", encoding="utf-8")
    stale_time = time.time() - 120
    os.utime(csv_path, (stale_time, stale_time))

    started = time.monotonic()
    result = request_study_csv_refresh("study1", timeout_seconds=60)

    assert result is False
    assert (requests / "study1").exists()
    assert time.monotonic() - started < 1


def test_existing_refresh_request_returns_immediately(monkeypatch, tmp_path):
    storage, requests = _configure_paths(monkeypatch, tmp_path)
    (storage / "dashboard_study1.csv").write_text("subject_name\n", encoding="utf-8")
    marker = requests / "study1"
    marker.write_text("", encoding="utf-8")
    stale_time = time.time() - 120
    os.utime(storage / "dashboard_study1.csv", (stale_time, stale_time))

    assert request_study_csv_refresh("study1") is False
    assert marker.exists()
