# --- Environment Setup ---
import os
import sys
import json

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Set the Django settings module BEFORE importing Django stuff
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin.settings")

# Setup Django
import django
django.setup()

# --- Django ---
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.models import User, Group, Permission

# --- Third-party ---
import pytest
from unittest.mock import patch, mock_open

# --- Standard Library ---
import pandas as pd

# --- Local Imports ---
# Do this AFTER django.setup()
from jdash.utils import fileutils

# Test create_download_file_log writes header and row when file does not exist
@patch("os.path.isfile", return_value=False)
@patch("builtins.open", new_callable=mock_open)
def test_create_download_file_log_creates_file_with_header_and_row(mock_file, mock_isfile):
    row = ['dataset1', 'John', 'john@example.com', 'link', 'status', 'req', 'emailed', 'downloaded']
    fileutils.create_download_file_log(row)

    handle = mock_file()
    # header + row => two writes
    calls = handle.write.call_args_list
    header_written = any("dataset" in call[0][0] for call in calls)
    row_written = any("dataset1" in call[0][0] for call in calls)

    assert header_written
    assert row_written

# Test updated_status updates rows correctly
@patch("builtins.open", new_callable=mock_open, read_data="dataset,FirstName,Email,Link,Status,Requested,Emailed,Downloaded\nstudy1,John,john@example.com,link,sent email,req,emailed,olddate\n")
def test_updated_status_updates_sent_email_row(mock_file):
    file_path = "fake_path"
    # Patch os.path.join to return file_path
    with patch("os.path.join", return_value=file_path):
        fileutils.updated_status()

    handle = mock_file()
    written_content = "".join(call[0][0] for call in handle.write.call_args_list)

    # The 'sent email' should be replaced with 'downlaoded' (typo as per original)
    assert "downlaoded" in written_content
    assert "sent email" not in written_content

# Test get_json_data returns parsed and transformed JSON data
@patch("builtins.open", new_callable=mock_open, read_data=json.dumps({
    "number_of_subjects": 5,
    "sensor_list": ["sensor1", "sensor2"],
    "sensor_list_limited": ["sensor3"]
}))
@patch("jdash.utils.fileutils.sync_enrolled_subjects_count")
@patch("jdash.utils.fileutils.get_user_list", return_value=["StudyX_001", "StudyX_002"])
@patch("jdash.utils.fileutils.read_study_df", return_value=pd.DataFrame({"subject_name": ["StudyX_001_1"]}))
@patch("os.path.join", side_effect=lambda *args: "/".join(args))
def test_get_json_data_transformations(mock_join, mock_read_df, mock_get_user_list, mock_sync_count, mock_file):
    result = fileutils.get_json_data("StudyX")
    assert result["number_of_subjects"] == 5
    assert result["sensor_size"] == 6  # 2*2 + 2*1
    assert result["number_of_enrolled_subjects"] == 2
    mock_sync_count.assert_called_once_with("StudyX", 2)


# Test get_all_json_data calls get_json_data for each directory
@patch("jdash.utils.fileutils.get_json_data")
def test_get_all_json_data_calls_get_json_data(mock_get_json_data):
    dirs = ["dir1", "dir2"]
    mock_get_json_data.side_effect = lambda d: { "key": d }
    result = fileutils.get_all_json_data(dirs)
    assert result == {
        "dir1": {"key": "dir1"},
        "dir2": {"key": "dir2"},
    }


def test_list_study_json_versions_includes_current_and_backups(tmp_path, monkeypatch):
    study_name = "StudyX"
    study_directory = tmp_path / study_name
    study_directory.mkdir()
    (study_directory / f"{study_name}.json").write_text(
        json.dumps({"version": 3}),
        encoding="utf-8",
    )
    (study_directory / f"{study_name}_v1_20260101090000.json").write_text(
        json.dumps({"version": 1}),
        encoding="utf-8",
    )
    (study_directory / f"{study_name}_v2_20260201100000.json").write_text(
        json.dumps({"version": 2}),
        encoding="utf-8",
    )
    (study_directory / "unrelated.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fileutils.config, "studies_folder", str(tmp_path))

    versions = fileutils.list_study_json_versions(study_name)

    assert [version["key"] for version in versions] == [
        "current",
        "v2_20260201100000",
        "v1_20260101090000",
    ]
    assert versions[0]["version"] == 3
    assert versions[0]["is_current"] is True


def test_list_study_json_versions_hides_archive_matching_current_version(tmp_path, monkeypatch):
    study_name = "StudyX"
    study_directory = tmp_path / study_name
    study_directory.mkdir()
    (study_directory / f"{study_name}.json").write_text(
        json.dumps({"version": 3}),
        encoding="utf-8",
    )
    (study_directory / f"{study_name}_v3_20260301120000.json").write_text(
        json.dumps({"version": 3}),
        encoding="utf-8",
    )
    (study_directory / f"{study_name}_v2_20260201100000.json").write_text(
        json.dumps({"version": 2}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fileutils.config, "studies_folder", str(tmp_path))

    versions = fileutils.list_study_json_versions(study_name)

    assert [version["key"] for version in versions] == [
        "current",
        "v2_20260201100000",
    ]


def test_resolve_study_json_version_path_rejects_invalid_keys(tmp_path, monkeypatch):
    study_name = "StudyX"
    study_directory = tmp_path / study_name
    study_directory.mkdir()
    version_path = study_directory / f"{study_name}_v1_20260101090000.json"
    version_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fileutils.config, "studies_folder", str(tmp_path))

    assert fileutils.resolve_study_json_version_path(
        study_name,
        "v1_20260101090000",
    ) == str(version_path)
    with pytest.raises(ValueError):
        fileutils.resolve_study_json_version_path(study_name, "../secrets")


def test_get_study_json_version_diff_compares_with_immediately_older_version(tmp_path, monkeypatch):
    study_name = "StudyX"
    study_directory = tmp_path / study_name
    study_directory.mkdir()
    (study_directory / f"{study_name}.json").write_text(
        json.dumps({
            "version": 3,
            "title": "Updated",
            "settings": {"enabled": True},
            "items": ["first", "new"],
        }),
        encoding="utf-8",
    )
    (study_directory / f"{study_name}_v2_20260201100000.json").write_text(
        json.dumps({
            "version": 2,
            "title": "Original",
            "settings": {"enabled": False, "legacy": True},
            "items": ["first", "old"],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(fileutils.config, "studies_folder", str(tmp_path))

    comparison = fileutils.get_study_json_version_diff(study_name, "current")

    assert comparison["selected"]["version"] == 3
    assert comparison["previous"]["version"] == 2
    changes_by_path = {change["path"]: change for change in comparison["changes"]}
    assert changes_by_path["title"]["previous"] == "Original"
    assert changes_by_path["title"]["selected"] == "Updated"
    assert changes_by_path["settings.enabled"]["change_type"] == "changed"
    assert changes_by_path["settings.legacy"]["change_type"] == "removed"
    assert changes_by_path["items[1]"]["selected"] == "new"
    assert changes_by_path["version"]["selected"] == 3


def test_get_study_json_version_diff_reports_oldest_version(tmp_path, monkeypatch):
    study_name = "StudyX"
    study_directory = tmp_path / study_name
    study_directory.mkdir()
    (study_directory / f"{study_name}.json").write_text(
        json.dumps({"version": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fileutils.config, "studies_folder", str(tmp_path))

    comparison = fileutils.get_study_json_version_diff(study_name, "current")

    assert comparison["previous"] is None
    assert comparison["changes"] == []

# Test save_study_json writes JSON file
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.join", return_value="/fake/path/study.json")
def test_save_study_json_writes_file(mock_join, mock_file):
    data = {"foo": "bar"}
    fileutils.save_study_json("study_id", data)
    mock_file().write.assert_called()

# Test get_names separates files and directories
@patch("os.listdir", return_value=["file1.txt", "dir1"])
@patch("os.path.isdir", side_effect=lambda path: path.endswith("dir1"))
def test_get_names_lists_files_and_directories(mock_isdir, mock_listdir):
    files, dirs = fileutils.get_names("/fake/dir")
    assert "file1.txt" in files
    assert "dir1" in dirs

# Test change_permissions calls os.chown and os.chmod
@patch("os.chown")
@patch("os.chmod")
def test_change_permissions_calls_chown_and_chmod(mock_chmod, mock_chown):
    fileutils.change_permissions("/some/path")
    mock_chown.assert_called_once_with("/some/path", 33, 3619)
    mock_chmod.assert_called_once()


@patch("jdash.utils.fileutils.grp.getgrnam")
@patch("os.chown")
@patch("os.chmod")
def test_set_download_file_permissions_uses_755_and_jtrack_group(
    mock_chmod,
    mock_chown,
    mock_getgrnam,
):
    mock_getgrnam.return_value.gr_gid = 3619

    fileutils.set_download_file_permissions("/some/download.zip")

    mock_chmod.assert_called_once_with("/some/download.zip", 0o755)
    mock_getgrnam.assert_called_once_with("jtrack")
    mock_chown.assert_called_once_with("/some/download.zip", -1, 3619)

# Test open_study_json loads JSON
@patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
@patch("os.path.join", return_value="/fake/path/study.json")
def test_open_study_json_returns_json(mock_join, mock_file):
    data = fileutils.open_study_json("study")
    assert data == {"key": "value"}


@patch("jdash.utils.fileutils.get_json_data", return_value={"wearables": [{"sensorname": "Garmin"}]})
def test_parse_get_dashboard_csv_merges_wearable_dashboard_csv(mock_get_json_data, tmp_path):
    study_name = "WearableStudy"
    fileutils.config.storage_folder = str(tmp_path)
    fileutils.config.csv_prefix = "jutrack_dashboard_"

    base_df = pd.DataFrame([
        {"subject_name": "subj1_1", "app": "main", "status_code": 0, "activity n_batches": 12}
    ])
    base_df.to_csv(tmp_path / f"jutrack_dashboard_{study_name}.csv", index=False)

    wearable_df = pd.DataFrame([
        {"subject_name": "subj1_1", "app": "main", "GarminSteps n_batches": 33, "GarminSteps last_time_received": "2026-05-19 10:00:00"}
    ])
    wearable_df.to_csv(tmp_path / f"jtrack_wearable_{study_name}.csv", index=False)

    parsed = fileutils.parse_get_dashboard_csv(study_name)

    assert parsed[0]["subject_name"] == "subj1_1"
    assert parsed[0]["activity n_batches"] == 12
    assert parsed[0]["GarminSteps n_batches"] == 33
    assert parsed[0]["GarminSteps last_time_received"] == "2026-05-19 10:00:00"


def test_normalize_wearable_dashboard_columns_leaves_legacy_code_style_names_untouched():
    wearable_df = pd.DataFrame([
        {
            "subject_name": "subj1_1",
            "app": "main",
            "at_n_batches": 21,
            "at_last_time_received": "2026-05-19 12:00:00",
        }
    ])
    wearable = {"sensors": [{"wearable_sensor": "activity"}]}

    normalized = fileutils.normalize_wearable_dashboard_columns(wearable_df, wearable)

    assert "at_n_batches" in normalized.columns
    assert "at_last_time_received" in normalized.columns
    assert normalized.loc[0, "at_n_batches"] == 21


def test_normalize_wearable_dashboard_columns_maps_prefixed_indexed_names():
    wearable_df = pd.DataFrame([
        {
            "subject_name": "subj1_1",
            "app": "main",
            "garmin_ACTIGRAPHY_1 n_batches": 17,
            "garmin_ACTIGRAPHY_1 last_time_received": "2026-05-19 09:30:00",
        }
    ])
    wearable = {
        "sensorname": "Garmin",
        "sensors": [{"wearable_sensor": "ACTIGRAPHY"}],
    }

    normalized = fileutils.normalize_wearable_dashboard_columns(wearable_df, wearable)

    assert "garmin_ACTIGRAPHY n_batches" in normalized.columns
    assert "garmin_ACTIGRAPHY last_time_received" in normalized.columns
    assert normalized.loc[0, "garmin_ACTIGRAPHY n_batches"] == 17


def test_build_wearable_dashboard_sensor_name_normalizes_camel_case():
    assert (
        fileutils.build_wearable_dashboard_sensor_name("Garmin", "HeartRate")
        == "garmin_HEART_RATE"
    )
