"""Callbacks for EMA dashboard figures."""

from dash import Input, Output
from django.utils.translation import gettext_lazy as _

from ..data.ema_data import EMA_FREQUENCY_WINDOW_COMPLETION_CSV, is_optional_only_ema_study, load_ema_quality_csv
from ..data.dashboard_data import first_matching_column, resolve_subject_filter
from ..figures.dashboard_figures import blank_quality_figure, build_live_figure, build_quality_figure
from ..layouts.dashboard_layout import EMA_DATA_QUALITY_CARDS, LIVE_EMA_CARD


def register_ema_callbacks(app):
    @app.callback(
        *[Output(f"{card['id']}-card-container", "style") for card in EMA_DATA_QUALITY_CARDS],
        Input("studies-dropdown", "value"),
    )
    def update_ema_card_visibility(study_name):
        optional_only = is_optional_only_ema_study(study_name)
        visible_optional_cards = {
            "ema-dq-subject-timeline",
            "ema-dq-anytime-question-status",
            "ema-dq-daily-response-activity",
        }
        visible_scheduled_cards = {
            "ema-dq-completion-matrix",
            "ema-dq-missingness",
            "ema-dq-daily-submission-volume",
        }
        visible_cards = visible_optional_cards if optional_only else visible_scheduled_cards
        return [
            {} if card["id"] in visible_cards else {"display": "none"}
            for card in EMA_DATA_QUALITY_CARDS
        ]

    @app.callback(
        Output("ema-frequency-filter", "options"),
        Output("ema-frequency-filter", "value"),
        Input("studies-dropdown", "value"),
    )
    def update_ema_frequency_filter(study_name):
        if not study_name:
            return [], None

        df = load_ema_quality_csv(study_name, EMA_FREQUENCY_WINDOW_COMPLETION_CSV)
        if df is None or df.empty:
            return [], None

        frequency_col = first_matching_column(df.columns, ["Frequency", "frequency"])
        if not frequency_col:
            return [], None

        frequencies = sorted(str(value) for value in df[frequency_col].dropna().unique())
        return [{"label": value, "value": value} for value in frequencies], None

    @app.callback(
        *[Output(card["id"], "figure") for card in EMA_DATA_QUALITY_CARDS],
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
        Input("ema-frequency-filter", "value"),
    )
    def update_ema_figures(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
        frequencies,
    ):
        if not study_name:
            return [blank_quality_figure(str(card["title"])) for card in EMA_DATA_QUALITY_CARDS]

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return [
            build_quality_figure(
                card,
                study_name,
                None,
                subjects,
                frequencies,
                None,
                timeline_axis,
            )
            for card in EMA_DATA_QUALITY_CARDS
        ]

    @app.callback(
        Output(LIVE_EMA_CARD["id"], "figure"),
        Input("studies-dropdown", "value"),
        Input("dq-filter-subject", "value"),
        Input("dq-filter-subject-mode", "value"),
        Input("dq-filter-subject", "options"),
        Input("dq-timeline-x-axis", "value"),
    )
    def update_ema_coverage_figure(
        study_name,
        subjects,
        subject_filter_mode,
        subject_options,
        timeline_axis,
    ):
        if not study_name:
            return blank_quality_figure(str(_("EMA Coverage")))

        subjects = resolve_subject_filter(subjects, subject_filter_mode, subject_options)
        return build_live_figure(LIVE_EMA_CARD, study_name, subjects=subjects, timeline_axis=timeline_axis)
