"""Analytics dashboard cards, controls, and top-level layout."""

from dash import dcc, html
import dash_bootstrap_components as dbc
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from ..data.ema_data import EMA_QUALITY_FOLDER, EMA_SUBJECT_QC_TIMELINE_CSV
from .ema_layout import EMA_DATA_QUALITY_CARDS, ema_tab_cards

DATA_QUALITY_DASHBOARD_CARDS = [
    {
        "id": "dq-adherence-heatmap",
        "filename": "Data_quality_adherence_heatmap.csv",
        "title": _("Adherence Heatmap"),
        "threshold_control": True,
        "xl": 12,
    },
    {
        "id": "dq-daily-coverage",
        "filename": "Data_quality_daily_subject_coverage.csv",
        "title": _("Daily Subject Coverage"),
        "method_note": _("Coverage % = Subjects_with_data / Subjects_selected x 100, computed from subject_qc_timeline after the subject filter."),
        "hidden": True,
    },
    {
        "id": "dq-daily-volume",
        "filename": "Data_quality_daily_data_volume.csv",
        "title": _("Daily Data Volume"),
        "method_note": _("Daily_volume = sum(Data_per_day) from subject_qc_timeline for selected subjects. Each line is one sensor."),
        "device_sensor_method_note": _("Daily_volume = sum(Data_per_day) from device sensor subject_qc_timeline for selected subjects. Each line is one sensor."),
    },
    {
        "id": "dq-subject-retention",
        "filename": "Data_quality_subject_retention.csv",
        "title": _("Subject Retention"),
        "hidden": True,
    },
    {
        "id": "dq-missingness",
        "filename": "Data_quality_missingness_summary.csv",
        "title": _("Missingness Summary"),
        "method_note": _("Missingness % = enrolled subjects with no row or zero data / enrolled subjects × 100. "),
        "device_sensor_method_note": _("Missingness % = enrolled subjects with no row or zero data / enrolled subjects x 100. "),
    },
    {
        "id": "dq-sensor-availability",
        "filename": "Data_quality_sensor_availability_matrix.csv",
        "title": _("Sensor Availability Matrix"),
        "method_note": _("Available % = days with smartphone sensor data / expected days x 100. "),
        "device_sensor_method_note": _("Available % = days with device sensor data / expected days x 100. "),
    },
    {
        "id": "dq-qc-funnel",
        "filename": "Data_quality_qc_exclusion_funnel.csv",
        "title": _("QC Exclusion Funnel"),
        "hidden": True,
    },
    {
        "id": "dq-data-loss",
        "filename": "Data_quality_qc_data_loss_by_stage.csv",
        "title": _("QC Data Loss by Stage"),
        "hidden": True,
    },
    {
        "id": "dq-qc-timeline",
        "filename": "Data_quality_subject_qc_timeline.csv",
        "title": _("Subject QC Timeline"),
    },
    {
        "id": "dq-anomaly-flags",
        "filename": "Data_quality_anomaly_flags.csv",
        "title": _("Anomaly Flags"),
        "method_note": _("Z-score compares a day's value with that sensor's typical values. Each dot represents one flagged sensor-day."),
        "device_sensor_method_note": _("Z-score compares a day's value with that device sensor's typical values. Each dot represents one flagged device sensor-day."),
        "hidden": True,
    },
]


SUBJECT_DATA_QUALITY_CARDS = [
    {
        "id": "overview-subject-status",
        "filename": "Study_overview_subject_sensor_status.csv",
        "title": _("Subject Follow-up Table"),
        "figure_builder": "live",
        "table_download": True,
        "xl": 12,
        "graph_height": "640px",
    },
    {
        "id": "dq-subject-overview",
        "filename": "Data_per_day*.csv",
        "title": _("Subject Activity by Study Day"),
        "timeline_axis_control": True,
        "xl": 12,
        "graph_height": "680px",
    },
]

OVERVIEW_SUBJECT_DETAIL_CARDS = [
    {
        "id": "overview-subject-smartphone-progression",
        "filename": "Data_quality_subject_qc_timeline.csv",
        "title": _("Smartphone Raw Data"),
        "raw_data": True,
        "xl": 12,
        "graph_height": "440px",
    },
    {
        "id": "overview-subject-device-sensor-progression",
        "filename": "Garmin_data_quality_subject_qc_timeline.csv",
        "title": _("Wearable Raw Data"),
        "quality_folder": "garmin_data_quality",
        "raw_data": True,
        "xl": 12,
        "graph_height": "440px",
    },
    {
        "id": "overview-subject-ema-progression",
        "filename": EMA_SUBJECT_QC_TIMELINE_CSV,
        "title": _("EMA Response Activity"),
        "quality_folder": EMA_QUALITY_FOLDER,
        "raw_data": True,
        "xl": 12,
        "graph_height": "440px",
    },
]

SENSOR_DATA_QUALITY_CARDS = [
    DATA_QUALITY_DASHBOARD_CARDS[4],
    DATA_QUALITY_DASHBOARD_CARDS[5],
    DATA_QUALITY_DASHBOARD_CARDS[2],
    DATA_QUALITY_DASHBOARD_CARDS[6],
    DATA_QUALITY_DASHBOARD_CARDS[7],
    DATA_QUALITY_DASHBOARD_CARDS[9],
]


def unique_cards_by_id(cards):
    unique = []
    seen = set()
    for card in cards:
        card_id = card["id"]
        if card_id in seen:
            continue
        seen.add(card_id)
        unique.append(card)
    return unique


def quality_cards_for_folder(cards, id_prefix, quality_folder):
    cloned_cards = []
    for card in cards:
        cloned_card = dict(card)
        cloned_card["id"] = f"{id_prefix}-{card['id']}"
        cloned_card["quality_folder"] = quality_folder
        if quality_folder == "garmin_data_quality" and card.get("device_sensor_method_note"):
            cloned_card["method_note"] = card["device_sensor_method_note"]
        cloned_cards.append(cloned_card)
    return cloned_cards


DEVICE_SENSOR_DATA_QUALITY_CARDS = quality_cards_for_folder(
    SENSOR_DATA_QUALITY_CARDS,
    "device-sensor",
    "garmin_data_quality",
)
QUALITY_DASHBOARD_CARDS = unique_cards_by_id(
    SUBJECT_DATA_QUALITY_CARDS
    + OVERVIEW_SUBJECT_DETAIL_CARDS
    + SENSOR_DATA_QUALITY_CARDS
    + EMA_DATA_QUALITY_CARDS
    + DEVICE_SENSOR_DATA_QUALITY_CARDS
)


LIVE_MONITORING_CARDS = [
    {
        "id": "live-summary",
        "filename": "Study_overview_summary.csv",
        "title": _("Study Summary"),
        "type": "kpi",
        "xl": 12,
    },
    {
        "id": "live-sensor-coverage",
        "filename": "__details_sensor_coverage__",
        "title": _("Sensor Coverage"),
        "source_csv": "dashboard",
        "method_note": _("Coverage % = Subjects_with_data / Subjects_selected x 100 from subject_qc_timeline."),
    },
    {
        "id": "live-ema-coverage",
        "filename": "__details_ema_coverage__",
        "title": _("EMA Coverage"),
        "source_csv": "dashboard",
        "method_note": _("Coverage % = Subjects_with_data / Subjects_selected x 100 from EMA subject_qc_timeline."),
        "xl": 12,
    },
    {
        "id": "live-device-sensor-coverage",
        "filename": "__details_device_sensor_coverage__",
        "title": _("Device Sensor Coverage"),
        "source_csv": "dashboard",
        "method_note": _("Coverage % = Subjects_with_data / Subjects_selected x 100 from device sensor subject_qc_timeline."),
    },
]

LIVE_SUMMARY_CARD = LIVE_MONITORING_CARDS[0]
LIVE_EMA_CARD = LIVE_MONITORING_CARDS[2]
SENSOR_KPI_CARD = {
    "id": "sensor-kpi-summary",
    "filename": "__details_sensor_kpis__",
    "title": _("Smartphone Data Summary"),
    "type": "kpi",
    "xl": 12,
}
DEVICE_SENSOR_KPI_CARD = {
    "id": "device-sensor-kpi-summary",
    "filename": "__details_device_sensor_kpis__",
    "title": _("Device Sensor Summary"),
    "type": "kpi",
    "xl": 12,
}
EMA_KPI_CARD = {
    "id": "ema-kpi-summary",
    "filename": "__details_ema_kpis__",
    "title": _("EMA Summary"),
    "type": "kpi",
    "xl": 12,
}
SENSOR_COVERAGE_CARDS = [LIVE_MONITORING_CARDS[1]]
EMA_TAB_CARDS = ema_tab_cards(LIVE_EMA_CARD)
DEVICE_SENSOR_TAB_CARDS = DEVICE_SENSOR_DATA_QUALITY_CARDS[:3] + [LIVE_MONITORING_CARDS[3]] + DEVICE_SENSOR_DATA_QUALITY_CARDS[3:]
SENSOR_TAB_CARDS = SENSOR_DATA_QUALITY_CARDS[:3] + SENSOR_COVERAGE_CARDS + SENSOR_DATA_QUALITY_CARDS[3:]


ANALYTICS_TAB_STYLE = {
    "display": "inline-flex",
    "flex": "0 0 auto",
    "width": "auto",
    "alignItems": "center",
    "justifyContent": "center",
    "padding": "8px 18px",
    "borderRadius": "999px",
    "border": "1px solid #cfd6dd",
    "backgroundColor": "#ffffff",
    "color": "#495057",
    "fontWeight": "600",
    "marginRight": "10px",
    "lineHeight": "1.2",
    "whiteSpace": "nowrap",
}

ANALYTICS_SELECTED_TAB_STYLE = {
    **ANALYTICS_TAB_STYLE,
    "border": "1px solid #0d6efd",
    "backgroundColor": "#0d6efd",
    "color": "#ffffff",
}

ANALYTICS_HIDDEN_TAB_STYLE = {
    **ANALYTICS_TAB_STYLE,
    "display": "none",
}

ANALYTICS_HIDDEN_SELECTED_TAB_STYLE = {
    **ANALYTICS_SELECTED_TAB_STYLE,
    "display": "none",
}


def _chart_menu_item(icon_class, label, **kwargs):
    return dbc.DropdownMenuItem(
        [
            html.I(className=f"{icon_class} me-2", **{"aria-hidden": "true"}),
            html.Span(label),
        ],
        **kwargs,
    )


def _chart_download_menu(card):
    chart_id = card["id"]
    csv_item_style = {"display": "none"} if card.get("threshold_control") else {}
    download_items = [
        _chart_menu_item(
            "far fa-file-alt",
            _("Download CSV"),
            id=f"{chart_id}-download-csv",
            style=csv_item_style,
        ),
    ]
    if card.get("table_download"):
        download_items.append(
            _chart_menu_item(
                "far fa-file-excel",
                _("Download table as Excel"),
                id=f"{chart_id}-download-excel",
            )
        )
    if not card.get("table_download"):
        download_items.append(
            _chart_menu_item(
                "far fa-image",
                _("Download as image"),
                id=f"{chart_id}-download-image",
            )
        )
    return dbc.DropdownMenu(
        download_items,
        label=[
            html.I(className="fas fa-download me-2", **{"aria-hidden": "true"}),
            html.Span(_("Download")),
        ],
        direction="end",
        caret=True,
        color="link",
        class_name="w-100 analytics-chart-download-menu",
        toggle_class_name="dropdown-item d-flex align-items-center text-dark text-decoration-none w-100 analytics-chart-menu-item",
        toggle_style={"boxShadow": "none"},
    )


def _chart_menu(card):
    menu_items = []
    if card.get("threshold_control"):
        menu_items.append(dbc.DropdownMenuItem(_("Derived from Data_per_day"), disabled=True))
    menu_items.extend(
        [
            _chart_menu_item(
                "fas fa-expand",
                _("Enter fullscreen"),
                id=f"{card['id']}-fullscreen",
            ),
            dbc.DropdownMenuItem(divider=True),
            _chart_download_menu(card),
        ]
    )
    return dbc.DropdownMenu(
        menu_items,
        label="⋮",
        caret=False,
        align_end=True,
        color="link",
        class_name="analytics-chart-menu",
        toggle_class_name="p-0 text-muted text-decoration-none",
        toggle_style={"fontSize": "1.5rem", "lineHeight": "1", "boxShadow": "none"},
    )


def _chart_card(card):
    col_style = {"display": "none"} if card.get("hidden") else None
    if card.get("type") == "kpi":
        return dbc.Col(
            dbc.Card(
                [
                    dbc.CardBody(
                        html.Div(
                            id=card["id"],
                            className="analytics-kpi-grid",
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(auto-fit, minmax(10rem, 1fr))",
                                "gap": "1rem",
                            },
                        ),
                        className="pt-3",
                    ),
                ],
                className="h-100 border-0 shadow-sm analytics-kpi-summary-card",
                style={"borderRadius": "0.45rem"},
            ),
            id=f"{card['id']}-card-container",
            md=12,
            xl=card.get("xl", 6),
            className="mb-4",
            style=col_style,
        )

    body_children = [
        dcc.Download(id=f"{card['id']}-csv-download"),
        html.Div(id=f"{card['id']}-fullscreen-trigger", style={"display": "none"}),
    ]
    if card.get("table_download"):
        body_children.append(dcc.Download(id=f"{card['id']}-excel-download"))
    else:
        body_children.append(
            html.Div(
                id=f"{card['id']}-image-download-trigger",
                style={"display": "none"},
            )
        )
    if card.get("timeline_axis_control"):
        body_children.append(
            html.Div(
                [
                    dbc.Label(
                        _("X axis"),
                        html_for="dq-timeline-x-axis",
                        className="fw-semibold mb-0",
                    ),
                    dcc.Dropdown(
                        id="dq-timeline-x-axis",
                        options=[
                            {"label": _("Study day"), "value": "study_day"},
                            {"label": _("Date"), "value": "date"},
                        ],
                        value="study_day",
                        clearable=False,
                        placeholder=_("Study day"),
                    ),
                ],
                id="dq-timeline-x-axis-control",
                className="analytics-chart-axis-control mb-3",
            )
        )
    if card.get("threshold_control"):
        body_children.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                _("Minimum data per day"),
                                htmlFor="dq-adherence-threshold",
                                className="fw-semibold mb-0",
                            ),
                            html.Span(
                                id="dq-adherence-threshold-label",
                                className="text-muted small",
                                style={"display": "none"},
                            ),
                        ],
                        className="d-flex align-items-center justify-content-between mb-2",
                    ),
                    dcc.Slider(
                        id="dq-adherence-threshold",
                        min=5,
                        max=100,
                        step=1,
                        value=5,
                        marks={5: "5", 100: "100"},
                        included=False,
                        updatemode="drag",
                        tooltip={
                            "always_visible": True,
                            "placement": "bottom",
                            "template": "{value} records/day",
                            "style": {
                                "fontSize": "0.75rem",
                                "fontWeight": 600,
                                "color": "#212529",
                            },
                        },
                    ),
                ],
                className="mb-3",
            )
        )
    if card.get("method_note"):
        body_children.append(
            html.Div(
                card["method_note"],
                className="analytics-method-note text-muted small mb-3",
                style={
                    "borderLeft": "3px solid #ced4da",
                    "padding": "0.55rem 0.75rem",
                    "backgroundColor": "#f8f9fa",
                    "lineHeight": "1.35",
                },
            )
        )
    graph_style = {
        "minHeight": "320px",
        "width": "100%",
    }
    if card.get("graph_height"):
        graph_style["height"] = card["graph_height"]

    body_children.append(
        dcc.Loading(
            dcc.Graph(
                id=card["id"],
                className="analytics-chart-graph",
                config={
                    "displaylogo": False,
                    "displayModeBar": False,
                    "responsive": True,
                    "toImageButtonOptions": {"filename": card["id"]},
                },
                style=graph_style,
            ),
            custom_spinner=html.Div(
                html.Img(
                    src=static_asset_url("icons/jdash-loader-red.svg"),
                    alt=str(_("Loading")),
                    className="analytics-loading-logo",
                ),
                className="analytics-loading-logo-wrap",
            ),
            overlay_style={
                "visibility": "visible",
                "filter": "blur(1px)",
                "backgroundColor": "rgba(255, 255, 255, 0.72)",
            },
            delay_show=150,
            delay_hide=100,
        )
    )
    return dbc.Col(
        dbc.Card(
            [
                dbc.CardHeader(
                    [
                        html.H5(card["title"], className="mb-0"),
                        _chart_menu(card),
                    ],
                    className="analytics-chart-header d-flex align-items-center justify-content-between border-0",
                ),
                dbc.CardBody(
                    body_children,
                    className="pt-2 analytics-chart-body",
                ),
            ],
            className="h-100 border-0 shadow-sm analytics-chart-card",
            style={"borderRadius": "0.45rem"},
        ),
        id=f"{card['id']}-card-container",
        md=12,
        xl=card.get("xl", 6),
        className="mb-4",
        style=col_style,
    )


def _subject_detail_section(title, cards):
    return html.Div(
        [
            html.Div(
                [
                    html.H4(title, className="analytics-subject-section-title mb-0"),
                ],
                className="analytics-subject-section-header",
            ),
            dbc.Row([_chart_card(card) for card in cards]),
        ],
        className="analytics-subject-detail-section",
    )


def _subject_explorer_control(label, control):
    return html.Div(
        [
            dbc.Label(label, className="analytics-subject-explorer-control-label"),
            control,
        ],
        className="analytics-subject-explorer-control",
    )


def _subject_explorer_toolbar(source):
    controls = []
    if source != "ema":
        controls.append(
            _subject_explorer_control(
                _("Sensor"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-sensor",
                    options=[],
                    value=None,
                    placeholder=_("Select sensor"),
                    clearable=False,
                ),
            )
        )
    controls.extend(
        [
            _subject_explorer_control(
                _("Measure"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-metric",
                    options=[],
                    value=None,
                    placeholder=_("Select measure"),
                    clearable=False,
                ),
            ),
            _subject_explorer_control(
                _("Statistic"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-statistic",
                    options=(
                        [{"label": _("Count"), "value": "count"}]
                        if source == "ema"
                        else [
                            {"label": _("Mean"), "value": "mean"},
                            {"label": _("Median"), "value": "median"},
                            {"label": _("Minimum"), "value": "minimum"},
                            {"label": _("Maximum"), "value": "maximum"},
                            {"label": _("Sum"), "value": "sum"},
                            {"label": _("Count"), "value": "count"},
                        ]
                    ),
                    value="count" if source == "ema" else "mean",
                    clearable=False,
                    disabled=source == "ema",
                ),
            ),
            _subject_explorer_control(
                _("Resolution"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-resolution",
                    options=[
                        {"label": _("Minute"), "value": "minute"},
                        {"label": _("Hour"), "value": "hour"},
                        {"label": _("Day"), "value": "day"},
                    ],
                    value="day",
                    clearable=False,
                ),
            ),
            _subject_explorer_control(
                _("Timeline"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-timeline",
                    options=[
                        {"label": _("Study day"), "value": "study_day"},
                        {"label": _("Date"), "value": "date"},
                    ],
                    value="study_day",
                    clearable=False,
                ),
            ),
            _subject_explorer_control(
                _("Period"),
                dcc.Dropdown(
                    id=f"subject-explorer-{source}-period",
                    options=[
                        {"label": _("Last 30 study days"), "value": 30},
                    ],
                    value=30,
                    clearable=False,
                ),
            ),
        ]
    )
    return html.Div(
        controls,
        className=(
            "analytics-subject-explorer-toolbar "
            f"analytics-subject-explorer-toolbar--{source}"
        ),
    )


def _subject_explorer_section(title, source, card):
    return html.Div(
        [
            html.Div(
                html.H4(title, className="mb-0"),
                className="analytics-subject-explorer-section-header",
            ),
            html.Div(
                [
                    _subject_explorer_toolbar(source),
                    dbc.Row(
                        [_chart_card(card)],
                        className="analytics-subject-explorer-chart-row",
                    ),
                ],
                className="analytics-subject-explorer-section-body",
            ),
        ],
        id=f"subject-explorer-{source}-section",
        className="analytics-subject-explorer-section",
        style={"display": "none"},
    )


def _subject_data_explorer():
    return html.Div(
        [
            dcc.Store(id="subject-raw-metadata", data=None),
            html.Div(
                [
                    _subject_explorer_section(
                        _("Smartphone"),
                        "smartphone",
                        OVERVIEW_SUBJECT_DETAIL_CARDS[0],
                    ),
                    _subject_explorer_section(
                        _("Wearables"),
                        "garmin",
                        OVERVIEW_SUBJECT_DETAIL_CARDS[1],
                    ),
                    _subject_explorer_section(
                        _("EMA"),
                        "ema",
                        OVERVIEW_SUBJECT_DETAIL_CARDS[2],
                    ),
                ],
                className="analytics-subject-explorer-sections",
            ),
        ],
        className="analytics-subject-explorer",
    )


def static_asset_url(path):
    return f"{settings.STATIC_URL.rstrip('/')}/{path.lstrip('/')}"


def build_dashboard_layout():
    return dbc.Container(
        [
            html.Div(
                [
                    dcc.Store(id='study-store', data=None),
                    dcc.Store(id='sensor-store', data=None),
                    dcc.Store(id="analytics-drilldown-payloads", data={}),
                    dcc.Store(id="analytics-drilldown-request", data=None),
                    html.Div(id='output-div'),
                    html.Div(id='sensor-output-div'),
                ],
                style={'display': 'none'},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    dbc.Label(_("Choose Study"), html_for="studies-dropdown", className="fw-semibold"),
                                                    dcc.Dropdown(
                                                        id='studies-dropdown',
                                                        options=[],
                                                        value=None,
                                                        placeholder=_("Select study"),
                                                        persistence=True,
                                                        persistence_type='session',
                                                        clearable=True,
                                                    ),
                                                ],
                                                className="analytics-filter-group analytics-control-card",
                                            ),
                                            html.Div(
                                                [
                                                    dbc.Label(
                                                        _("Choose subject for single-subject view"),
                                                        html_for="overview-subject-select",
                                                        className="fw-semibold",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="overview-subject-select",
                                                        options=[],
                                                        value=None,
                                                        multi=False,
                                                        placeholder=_("Select subject"),
                                                        clearable=True,
                                                    ),
                                                ],
                                                className="analytics-filter-group analytics-control-card",
                                            ),
                                        ],
                                        className="analytics-control-grid analytics-control-stack",
                                    ),
                                    html.Div(
                                        dbc.Row(
                                            [_chart_card(LIVE_SUMMARY_CARD)],
                                            id="live-summary-content",
                                            className="g-0",
                                        ),
                                        id="live-summary-pane",
                                        className="analytics-control-kpi-pane",
                                    ),
                                    html.Div(
                                        html.A(
                                            id="subject-raw-data-download",
                                            href=None,
                                            className="analytics-subject-download-button",
                                            title=str(_("Download subject data")),
                                            **{"aria-label": str(_("Download subject data"))},
                                            style={"display": "none"},
                                        ),
                                        id="overview-subject-profile",
                                        className="analytics-control-kpi-pane",
                                        style={"display": "none"},
                                    ),
                                ],
                                className="analytics-control-kpi-row",
                            ),
                            html.Div(id="live-warning-panel"),
                            html.Div(
                                id="analytics-no-data-message",
                                className="alert alert-light border mb-0",
                                style={"display": "none"},
                            ),
                        ],
                        className="analytics-control-panel",
                    ),
                    html.Div(
                        [
                            html.Div(id="dq-dashboard-status", style={"display": "none"}),
                            html.Div(id="live-dashboard-status", style={"display": "none"}),
                            dcc.RadioItems(
                                id="analytics-dashboard-tabs",
                                value="subject-data",
                                options=[
                                    {"label": "overview", "value": "subject-data"},
                                ],
                                inline=True,
                                inputStyle={
                                    "display": "none",
                                    "cursor": "pointer",
                                },
                                labelStyle={
                                    "display": "inline-flex",
                                    "alignItems": "center",
                                    "marginRight": "0",
                                    "fontWeight": "600",
                                    "cursor": "pointer",
                                },
                                style={
                                    "marginBottom": "1.25rem",
                                },
                                className="analytics-dashboard-tabs",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    dbc.Label(
                                                        _("Filter subjects"),
                                                        html_for="dq-filter-subject",
                                                        className="fw-semibold mb-0",
                                                    ),
                                                    dcc.RadioItems(
                                                        id="dq-filter-subject-mode",
                                                        options=[
                                                            {"label": _("Include"), "value": "include"},
                                                            {"label": _("Exclude"), "value": "exclude"},
                                                        ],
                                                        value="include",
                                                        inline=True,
                                                        className="analytics-subject-filter-mode",
                                                    ),
                                                ],
                                                className="analytics-subject-filter-heading",
                                            ),
                                            dcc.Dropdown(
                                                id="dq-filter-subject",
                                                options=[],
                                                value=None,
                                                multi=True,
                                                placeholder=_("All subjects"),
                                            ),
                                        ],
                                        id="dq-filter-subject-control",
                                        className="analytics-tab-filter-control",
                                    ),
                                    html.Div(
                                        [
                                            dbc.Label(
                                                _("Select sensor"),
                                                html_for="dq-filter-sensor",
                                                className="fw-semibold",
                                            ),
                                            dcc.Dropdown(
                                                id="dq-filter-sensor",
                                                options=[],
                                                value=None,
                                                multi=False,
                                                placeholder=_("Select sensor"),
                                            ),
                                        ],
                                        id="dq-filter-sensor-control",
                                        className="analytics-tab-filter-control",
                                    ),
                                    html.Div(
                                        [
                                            dbc.Label(
                                                _("Filter frequency"),
                                                html_for="ema-frequency-filter",
                                                className="fw-semibold",
                                            ),
                                            dcc.Dropdown(
                                                id="ema-frequency-filter",
                                                options=[],
                                                value=None,
                                                multi=True,
                                                placeholder=_("All frequencies"),
                                            ),
                                        ],
                                        id="ema-frequency-filter-control",
                                        className="analytics-tab-filter-control",
                                        style={"display": "none"},
                                    ),
                                ],
                                id="dq-filter-controls",
                                className="analytics-tab-filter-bar",
                                style={"display": "none"},
                            ),
                            html.Div(
                                dbc.Row([_chart_card(card) for card in SUBJECT_DATA_QUALITY_CARDS]),
                                id="subject-dashboard-pane",
                            ),
                            html.Div(
                                _subject_data_explorer(),
                                id="subject-detail-dashboard-pane",
                                style={"display": "none"},
                            ),
                            html.Div(
                                dbc.Row([_chart_card(card) for card in SENSOR_TAB_CARDS]),
                                id="sensor-dashboard-pane",
                                style={"display": "none"},
                            ),
                            html.Div(
                                dbc.Row([_chart_card(card) for card in DEVICE_SENSOR_TAB_CARDS]),
                                id="device-sensor-dashboard-pane",
                                style={"display": "none"},
                            ),
                            html.Div(
                                dbc.Row([_chart_card(card) for card in EMA_TAB_CARDS]),
                                id="ema-dashboard-pane",
                                style={"display": "none"},
                            ),
                        ],
                        id="analytics-results-content",
                        className="analytics-dashboard-content p-4",
                    ),
                ],
                className="analytics-dashboard-shell",
            ),
        ],
        fluid=True,
        className="px-0",
    )
