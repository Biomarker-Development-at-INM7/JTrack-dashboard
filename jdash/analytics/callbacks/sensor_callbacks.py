"""Callbacks for subject-data and sensor-data dashboard figures."""

from dash import Input, Output
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import resolve_subject_filter
from ..figures.dashboard_figures import blank_quality_figure, build_live_figure, build_quality_figure
from ..layouts.dashboard_layout import (
    LIVE_MONITORING_CARDS,
    SENSOR_DATA_QUALITY_CARDS,
    SUBJECT_DATA_QUALITY_CARDS,
)


LIVE_SENSOR_COVERAGE_CARD = next(
    card for card in LIVE_MONITORING_CARDS if card["id"] == "live-sensor-coverage"
)


def register_sensor_callbacks(app):
    @app.callback(
        *[Output(card["id"], "figure") for card in SUBJECT_DATA_QUALITY_CARDS],
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_subject_data_figures(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return [blank_quality_figure(str(card["title"])) for card in SUBJECT_DATA_QUALITY_CARDS]

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return [
            build_live_figure(card, study_name, None, subjects)
            if card.get("figure_builder") == "live"
            else build_quality_figure(
                    card,
                    study_name,
                    None,
                    subjects,
                    None,
                    None,
                    timeline_axis,
                )
            for card in SUBJECT_DATA_QUALITY_CARDS
        ]

    @app.callback(
        *[Output(card["id"], "figure") for card in SENSOR_DATA_QUALITY_CARDS],
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_sensor_data_figures(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return [blank_quality_figure(str(card["title"])) for card in SENSOR_DATA_QUALITY_CARDS]

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return [
            build_quality_figure(
                card,
                study_name,
                None,
                subjects,
                None,
                None,
                timeline_axis,
            )
            for card in SENSOR_DATA_QUALITY_CARDS
        ]

    @app.callback(
        Output(LIVE_SENSOR_COVERAGE_CARD["id"], "figure"),
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_sensor_coverage_figure(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return blank_quality_figure(str(_("Sensor Coverage")))

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return build_live_figure(LIVE_SENSOR_COVERAGE_CARD, study_name, None, subjects, timeline_axis=timeline_axis)
