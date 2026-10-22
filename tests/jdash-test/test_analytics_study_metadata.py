import json

from jdash.analytics.data import study_metadata


def test_analytics_study_metadata_uses_main_studies_folder(tmp_path, monkeypatch):
    study_dir = tmp_path / "studies" / "StudyX"
    study_dir.mkdir(parents=True)
    (study_dir / "StudyX.json").write_text(
        json.dumps({
            "number_of_subjects": 3,
            "sensor-list": ["activity"],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        study_metadata.config,
        "studies_folder",
        str(tmp_path / "studies"),
    )

    result = study_metadata.get_analytics_study_json("StudyX")

    assert result["number_of_subjects"] == 3
    assert result["sensor_list"] == ["activity"]
    assert study_metadata.analytics_study_json_path("StudyX") == str(
        study_dir / "StudyX.json"
    )
