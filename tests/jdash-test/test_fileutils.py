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

# --- Local Imports ---
# Do this AFTER django.setup()
from jdash.classes import fileutils

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
@patch("os.path.join", side_effect=lambda *args: "/".join(args))
def test_get_json_data_transformations(mock_join, mock_file):
    result = fileutils.get_json_data("StudyX")
    assert result["number_of_subjects"] == 5
    assert result["sensor_size"] == 6  # 2*2 + 2*1

# Test get_all_json_data calls get_json_data for each directory
@patch("jdash.classes.fileutils.get_json_data")
def test_get_all_json_data_calls_get_json_data(mock_get_json_data):
    dirs = ["dir1", "dir2"]
    mock_get_json_data.side_effect = lambda d: { "key": d }
    result = fileutils.get_all_json_data(dirs)
    assert result == {
        "dir1": {"key": "dir1"},
        "dir2": {"key": "dir2"},
    }

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

# Test open_study_json loads JSON
@patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
@patch("os.path.join", return_value="/fake/path/study.json")
def test_open_study_json_returns_json(mock_join, mock_file):
    data = fileutils.open_study_json("study")
    assert data == {"key": "value"}