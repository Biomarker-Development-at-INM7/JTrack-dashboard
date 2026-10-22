import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from jdash.analytics.data.dashboard_data import study_has_analytics_csvs
from jdash.analytics.data.raw_subject_data import (
    RawSubjectDataValidationError,
    subject_raw_metadata,
    subject_sensor_series,
)


class RawSubjectDataTests(SimpleTestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.subject_dir = (
            self.root / "Study_A" / "inputs" / "Study_A_00001"
        )
        self.raw_dir = self.subject_dir / "raw"
        self.raw_dir.mkdir(parents=True)
        joined_at = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp() * 1000
        (self.subject_dir / "Study_A_00001_1.json").write_text(
            json.dumps({"time_joined": joined_at}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_sensor_file(self, sensor, filename_timestamp, records):
        sensor_dir = self.raw_dir / sensor
        sensor_dir.mkdir(exist_ok=True)
        path = sensor_dir / f"Study_A_Study_A_00001_{sensor}_{filename_timestamp}.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        return path

    def test_study_analytics_csv_availability_checks_nested_output_folders(self):
        outputs = self.root / "Empty_Study" / "outputs"
        outputs.mkdir(parents=True)
        with patch(
            "jdash.analytics.data.dashboard_data.config.analytics_storage_folder",
            str(self.root),
        ):
            self.assertFalse(study_has_analytics_csvs("Empty_Study"))
            quality = outputs / "data_quality"
            quality.mkdir()
            (quality / "summary.csv").write_text("Subject_ID\n", encoding="utf-8")
            self.assertTrue(study_has_analytics_csvs("Empty_Study"))

    @override_settings(RAW_DATA_MAX_RANGE_DAYS=31)
    def test_metadata_groups_available_sensor_streams(self):
        self._write_sensor_file(
            "activity",
            "2026-06-10T10-00-00",
            [{"timestamp": 1781085600000, "confidence": 90}],
        )
        self._write_sensor_file(
            "garmin_HEART_RATE",
            "2026-06-10T10-00-00",
            [{"timestamp": 1781085600000, "value": "72"}],
        )
        self._write_sensor_file(
            "ema",
            "2026-06-10T10-00-00",
            [{"timestamp": "1781085600000", "questionId": 1}],
        )

        with self.settings(RAW_DATA_STORAGE_ROOT=str(self.root)):
            payload = subject_raw_metadata("Study_A", "Study_A_00001")

        self.assertEqual(payload["sources"]["smartphone"][0]["name"], "activity")
        self.assertEqual(
            payload["sources"]["wearable"][0]["name"],
            "garmin_HEART_RATE",
        )
        self.assertEqual(
            [metric["value"] for metric in payload["sources"]["ema"][0]["metrics"]],
            ["responses", "submissions"],
        )

    def test_series_aggregates_values_and_calculates_study_day(self):
        timestamp = datetime(2026, 6, 10, 10, tzinfo=timezone.utc).timestamp() * 1000
        self._write_sensor_file(
            "garmin_HEART_RATE",
            "2026-06-10T10-00-00",
            [
                {"timestamp": timestamp, "value": "70"},
                {"timestamp": timestamp + 1000, "value": "74"},
            ],
        )

        with self.settings(RAW_DATA_STORAGE_ROOT=str(self.root)):
            payload = subject_sensor_series(
                "Study_A",
                "Study_A_00001",
                "garmin_HEART_RATE",
                resolution="day",
                period_days=7,
            )

        self.assertEqual(len(payload["points"]), 1)
        self.assertEqual(payload["points"][0]["value"], 72)
        self.assertEqual(payload["points"][0]["study_day"], 9)
        self.assertEqual(payload["points"][0]["records"], 2)

    @override_settings(RAW_DATA_MAX_RANGE_DAYS=31)
    def test_series_without_period_uses_full_available_study_range(self):
        for timestamp in (
            datetime(2026, 6, 2, 10, tzinfo=timezone.utc),
            datetime(2026, 8, 2, 10, tzinfo=timezone.utc),
        ):
            self._write_sensor_file(
                "garmin_HEART_RATE",
                timestamp.strftime("%Y-%m-%dT%H-%M-%S"),
                [{"timestamp": timestamp.timestamp() * 1000, "value": "72"}],
            )

        with self.settings(RAW_DATA_STORAGE_ROOT=str(self.root)):
            payload = subject_sensor_series(
                "Study_A",
                "Study_A_00001",
                "garmin_HEART_RATE",
                resolution="day",
                period_days=None,
            )

        self.assertEqual(payload["start"], "2026-06-01")
        self.assertEqual(payload["end"], datetime.now(timezone.utc).date().isoformat())
        self.assertEqual(payload["joined_at"], "2026-06-01T00:00:00+00:00")
        self.assertEqual(len(payload["points"]), 2)

    def test_ema_submissions_count_unique_submission_timestamps(self):
        timestamp = datetime(2026, 6, 10, 10, tzinfo=timezone.utc).timestamp() * 1000
        self._write_sensor_file(
            "ema",
            "2026-06-10T10-00-00",
            [
                {"timestamp": timestamp, "questionId": 1},
                {"timestamp": timestamp, "questionId": 2},
                {"timestamp": timestamp + 5000, "questionId": 3},
            ],
        )

        with self.settings(RAW_DATA_STORAGE_ROOT=str(self.root)):
            payload = subject_sensor_series(
                "Study_A",
                "Study_A_00001",
                "ema",
                metric="submissions",
                resolution="day",
                period_days=7,
            )

        self.assertEqual(payload["points"][0]["value"], 2)

    def test_series_evenly_samples_files_when_preview_limit_is_exceeded(self):
        for day in range(1, 5):
            timestamp = datetime(2026, 6, day, 10, tzinfo=timezone.utc).timestamp() * 1000
            self._write_sensor_file(
                "activity",
                f"2026-06-{day:02d}T10-00-00",
                [{"timestamp": timestamp, "confidence": day * 10}],
            )

        with self.settings(
            RAW_DATA_STORAGE_ROOT=str(self.root),
            RAW_DATA_MAX_FILES_PER_SERIES=2,
        ):
            payload = subject_sensor_series(
                "Study_A",
                "Study_A_00001",
                "activity",
                resolution="day",
                period_days=7,
            )

        self.assertTrue(payload["preview"]["files_sampled"])
        self.assertEqual(payload["preview"]["files_read"], 2)
        self.assertEqual(len(payload["points"]), 2)

    def test_path_components_cannot_escape_the_raw_data_root(self):
        with self.settings(RAW_DATA_STORAGE_ROOT=str(self.root)):
            with self.assertRaises(RawSubjectDataValidationError):
                subject_raw_metadata("../Study_A", "Study_A_00001")
