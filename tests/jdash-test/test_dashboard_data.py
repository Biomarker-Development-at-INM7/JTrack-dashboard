import pandas as pd

from jdash.analytics.data.dashboard_data import apply_filter, resolve_subject_filter


SUBJECT_OPTIONS = [
    {"label": "Subject 1", "value": "1"},
    {"label": "Subject 2", "value": "2"},
    {"label": "Subject 3", "value": "3"},
]


def test_subject_filter_include_returns_selected_subjects():
    assert resolve_subject_filter(["1", "3"], "include", SUBJECT_OPTIONS) == ["1", "3"]


def test_subject_filter_exclude_returns_unselected_subjects():
    assert resolve_subject_filter(["1", "3"], "exclude", SUBJECT_OPTIONS) == ["2"]


def test_subject_filter_with_no_selection_keeps_all_subjects():
    assert resolve_subject_filter([], "exclude", SUBJECT_OPTIONS) is None


def test_subject_filter_can_exclude_every_subject():
    selected = resolve_subject_filter(["1", "2", "3"], "exclude", SUBJECT_OPTIONS)
    frame = pd.DataFrame({"Subject_ID": ["1", "2", "3"]})

    assert apply_filter(frame, "Subject_ID", selected).empty
