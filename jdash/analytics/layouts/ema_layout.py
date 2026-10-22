"""EMA-specific dashboard card definitions."""

from django.utils.translation import gettext_lazy as _

from jdash.analytics.data.ema_data import (
    EMA_ANYTIME_QUESTION_STATUS_CSV,
    EMA_COMPLETION_MATRIX_CSV,
    EMA_DAILY_SUBMISSION_VOLUME_CSV,
    EMA_FREQUENCY_WINDOW_COMPLETION_CSV,
    EMA_MISSINGNESS_SUMMARY_CSV,
    EMA_QUALITY_FOLDER,
    EMA_SUBJECT_QC_TIMELINE_CSV,
)


EMA_DATA_QUALITY_CARDS = [
    {
        "id": "ema-dq-completion-matrix",
        "filename": EMA_COMPLETION_MATRIX_CSV,
        "title": _("EMA Completion Matrix"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Each cell is question completion percent for a subject and scheduled EMA frequency window."),
        "xl": 12,
    },
    {
        "id": "ema-dq-missingness",
        "filename": EMA_MISSINGNESS_SUMMARY_CSV,
        "title": _("EMA Subject Risk Ranking"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Question completion % = answered EMA questions / expected EMA questions x 100."),
        "xl": 6,
    },
    {
        "id": "ema-dq-daily-submission-volume",
        "filename": EMA_DAILY_SUBMISSION_VOLUME_CSV,
        "title": _("EMA Daily Response Volume"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Bars show scheduled EMA answers and additional responses; the line shows subjects with any answer."),
        "xl": 6,
    },
    {
        "id": "ema-dq-frequency-window-detail",
        "filename": EMA_FREQUENCY_WINDOW_COMPLETION_CSV,
        "title": _("EMA Frequency Window Detail"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Question completion percent per subject and frequency window."),
        "xl": 12,
        "hidden": True,
    },
    {
        "id": "ema-dq-subject-timeline",
        "filename": EMA_SUBJECT_QC_TIMELINE_CSV,
        "title": _("Subject Response Timeline"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Dots show actual EMA response days; size and color show questions answered."),
        "xl": 12,
        "hidden": True,
    },
    {
        "id": "ema-dq-anytime-question-status",
        "filename": EMA_ANYTIME_QUESTION_STATUS_CSV,
        "title": _("EMA Question Response Status"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Cells show how many study days each subject answered each EMA question."),
        "xl": 12,
        "hidden": True,
    },
    {
        "id": "ema-dq-daily-response-activity",
        "filename": EMA_DAILY_SUBMISSION_VOLUME_CSV,
        "title": _("Daily EMA Response Volume"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "method_note": _("Bars show EMA questions answered by study day; the line shows subjects with any answer."),
        "xl": 12,
        "hidden": True,
    },
]


def ema_tab_cards(live_ema_card=None):
    cards = list(EMA_DATA_QUALITY_CARDS)
    if live_ema_card:
        hidden_live_card = dict(live_ema_card)
        hidden_live_card["hidden"] = True
        cards.append(hidden_live_card)
    return cards
