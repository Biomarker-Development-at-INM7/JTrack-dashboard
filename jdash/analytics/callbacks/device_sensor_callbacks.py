"""Callbacks for device-sensor dashboard figures."""

from dash import Input, Output
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import resolve_subject_filter
from ..figures.dashboard_figures import blank_quality_figure, build_live_figure, build_quality_figure
from ..layouts.dashboard_layout import (
    DEVICE_SENSOR_DATA_QUALITY_CARDS,
    LIVE_MONITORING_CARDS,
)


LIVE_DEVICE_SENSOR_COVERAGE_CARD = next(
    card for card in LIVE_MONITORING_CARDS if card["id"] == "live-device-sensor-coverage"
)


def register_device_sensor_callbacks(app):
    @app.callback(
        *[Output(card["id"], "figure") for card in DEVICE_SENSOR_DATA_QUALITY_CARDS],
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_device_sensor_figures(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return [blank_quality_figure(str(card["title"])) for card in DEVICE_SENSOR_DATA_QUALITY_CARDS]

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
            for card in DEVICE_SENSOR_DATA_QUALITY_CARDS
        ]

    @app.callback(
        Output(LIVE_DEVICE_SENSOR_COVERAGE_CARD["id"], "figure"),
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_device_sensor_coverage_figure(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return blank_quality_figure(str(_("Device Sensor Coverage")))

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return build_live_figure(LIVE_DEVICE_SENSOR_COVERAGE_CARD, study_name, None, subjects, timeline_axis=timeline_axis)
