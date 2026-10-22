"""Main callback registrar for the analytics dashboard."""

import os
import time
import zipfile
from html.parser import HTMLParser

import pandas as pd
from dash import ALL, Input, Output, State, dcc, no_update
from dash.exceptions import PreventUpdate
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import (
    DEFAULT_DATA_QUALITY_FOLDER,
    analytics_tab_options,
    first_matching_column,
    live_download_frame,
    load_data_per_day_overview,
    load_quality_csv,
    load_subject_timeline_data,
    quality_download_frame,
    resolve_subject_filter,
    safe_download_filename,
    sensors_for_study_from_store,
    source_csv_path,
    study_has_analytics_csvs,
    update_selector,
    visible_analytics_tabs,
)
from ..data.ema_data import is_optional_only_ema_study
from ..figures.activity_summary_figures import build_connected_dashboard_summary
from ..figures.overview_figures import build_subject_profile_summary
from ..layouts.dashboard_layout import (
    LIVE_MONITORING_CARDS,
    LIVE_SUMMARY_CARD,
    QUALITY_DASHBOARD_CARDS,
)
from .device_sensor_callbacks import register_device_sensor_callbacks
from .ema_callbacks import register_ema_callbacks
from .sensor_callbacks import register_sensor_callbacks
from .subject_raw_callbacks import register_subject_raw_callbacks


def subject_dropdown_option(value):
    return {
        "label": value,
        "value": value,
    }


def add_subjects_from_frame(subjects, df):
    if df is None or df.empty:
        return
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    if subject_col:
        subjects.update(str(value) for value in df[subject_col].dropna().unique())


def sensor_filter_for_download(card, active_tab, selected_sensors):
    return None


def send_source_csv_files(paths, study_name, chart_id):
    if isinstance(paths, str):
        return dcc.send_file(paths, filename=os.path.basename(paths))

    source_paths = [path for path in paths or [] if path and os.path.isfile(path)]
    if not source_paths:
        return None

    filename = safe_download_filename(study_name, chart_id, "source_csvs", extension="zip")

    def write_zip(buffer):
        used_names = set()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in source_paths:
                archive_name = os.path.basename(path)
                if archive_name in used_names:
                    name, extension = os.path.splitext(archive_name)
                    index = 2
                    while f"{name}_{index}{extension}" in used_names:
                        index += 1
                    archive_name = f"{name}_{index}{extension}"
                used_names.add(archive_name)
                archive.write(path, archive_name)

    return dcc.send_bytes(write_zip, filename)


class TableHeaderParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "br":
            self.parts.append(" ")

    def text(self):
        return " ".join("".join(self.parts).split())


def table_figure_download_frame(figure):
    if not isinstance(figure, dict):
        return pd.DataFrame()

    table_trace = next(
        (
            trace
            for trace in figure.get("data", [])
            if isinstance(trace, dict) and trace.get("type") == "table"
        ),
        None,
    )
    if not table_trace:
        return pd.DataFrame()

    header_values = table_trace.get("header", {}).get("values", [])
    cell_values = table_trace.get("cells", {}).get("values", [])
    table_columns = {}
    for index, values in enumerate(cell_values):
        parser = TableHeaderParser()
        parser.feed(str(header_values[index]) if index < len(header_values) else "")
        column_name = parser.text() or str(_("Column %(number)s")) % {"number": index + 1}
        table_columns[column_name] = list(values) if isinstance(values, (list, tuple)) else [values]

    return pd.DataFrame(table_columns)


class DashboardCallbacks:
    """Register dashboard-wide callbacks and delegate tab-specific figures."""

    def __init__(self, app):
        self.app = app

    def register(self):
        self.register_study_callbacks()
        self.register_filter_callbacks()
        self.register_tab_callbacks()
        self.register_status_callbacks()
        register_sensor_callbacks(self.app)
        register_device_sensor_callbacks(self.app)
        register_ema_callbacks(self.app)
        register_subject_raw_callbacks(self.app)
        self.register_download_callbacks()

    def register_study_callbacks(self):
        app = self.app

        @app.callback(
            [
                Output("studies-dropdown", "options"),
                Output("studies-dropdown", "value"),
                Output("studies-dropdown", "style"),
            ],
            Input("study-store", "data"),
        )
        def update_studies_tabs(studies):
            combined_studies = []

            for study in list(studies or []):
                if study and study not in combined_studies:
                    combined_studies.append(study)

            if not combined_studies:
                return no_update, no_update, no_update

            studies_list = [{"label": study, "value": study} for study in combined_studies]
            return studies_list, studies_list[0]["value"], {}

    def register_filter_callbacks(self):
        app = self.app

        @app.callback(
            Output("dq-filter-sensor", "options"),
            Output("dq-filter-sensor", "value"),
            Input("studies-dropdown", "value"),
            Input("sensor-store", "data"),
        )
        def update_sensor_filter_options(study_name, sensors_map):
            if isinstance(sensors_map, dict):
                sensor_values = sensors_for_study_from_store(sensors_map, study_name)
                sensor_options = [{"label": value, "value": value} for value in sensor_values]
                sensor_value = sensor_values[0] if sensor_values else None
                return sensor_options, sensor_value

            return no_update, no_update

        @app.callback(
            Output("dq-filter-subject", "options"),
            Output("dq-filter-subject", "value"),
            Output("overview-subject-select", "options"),
            Output("overview-subject-select", "value"),
            Output("dq-filter-subject-mode", "value"),
            Input("studies-dropdown", "value"),
            Input("analytics-drilldown-request", "data"),
        )
        def update_subject_filter_options(study_name, drilldown_request):
            subjects = set()

            add_subjects_from_frame(subjects, load_data_per_day_overview(study_name))

            for quality_folder in (
                DEFAULT_DATA_QUALITY_FOLDER,
                "garmin_data_quality",
                "ema_data_quality",
            ):
                add_subjects_from_frame(subjects, load_subject_timeline_data(study_name, quality_folder))

            for card in QUALITY_DASHBOARD_CARDS + LIVE_MONITORING_CARDS:
                add_subjects_from_frame(
                    subjects,
                    load_quality_csv(
                        study_name,
                        card["filename"],
                        card.get("quality_folder", DEFAULT_DATA_QUALITY_FOLDER),
                    ),
                )

            subject_options = [subject_dropdown_option(value) for value in sorted(subjects)]
            selected_subjects = None
            if (
                isinstance(drilldown_request, dict)
                and drilldown_request.get("study") == study_name
            ):
                requested_subjects = drilldown_request.get("subjects") or []
                selected_subjects = [
                    str(subject)
                    for subject in requested_subjects
                    if str(subject) in subjects
                ] or None

            subject_mode = "include" if selected_subjects else no_update
            return subject_options, selected_subjects, subject_options, None, subject_mode

        @app.callback(
            Output("analytics-drilldown-request", "data"),
            Input(
                {"type": "analytics-drilldown", "key": ALL},
                "n_clicks_timestamp",
            ),
            State({"type": "analytics-drilldown", "key": ALL}, "id"),
            State("analytics-drilldown-payloads", "data"),
            State("studies-dropdown", "value"),
            prevent_initial_call=True,
        )
        def request_analytics_drilldown(
            click_timestamps,
            button_ids,
            payloads,
            study_name,
        ):
            if not isinstance(payloads, dict) or not click_timestamps or not button_ids:
                raise PreventUpdate

            timestamps = [int(value or -1) for value in click_timestamps]
            latest_index = max(range(len(timestamps)), key=timestamps.__getitem__)
            if timestamps[latest_index] <= 0 or latest_index >= len(button_ids):
                raise PreventUpdate

            clicked_id = button_ids[latest_index]
            clicked_key = clicked_id.get("key") if isinstance(clicked_id, dict) else None
            payload = payloads.get(clicked_key)
            if not isinstance(payload, dict) or not payload.get("subjects"):
                raise PreventUpdate

            request = dict(payload)
            request["study"] = study_name
            request["request_id"] = time.time_ns()
            return request

    def register_tab_callbacks(self):
        app = self.app

        @app.callback(
            Output("analytics-dashboard-tabs", "value"),
            Input("studies-dropdown", "value"),
            Input("sensor-store", "data"),
            Input("overview-subject-select", "value"),
            Input("analytics-drilldown-request", "data"),
            State("analytics-dashboard-tabs", "value"),
        )
        def update_dashboard_tabs(
            study_name,
            sensors_map,
            selected_subject,
            drilldown_request,
            active_tab,
        ):
            if selected_subject:
                return "subject-data"
            valid_tabs = visible_analytics_tabs(sensors_map, study_name)
            if (
                isinstance(drilldown_request, dict)
                and drilldown_request.get("study") == study_name
                and drilldown_request.get("tab") in valid_tabs
            ):
                return drilldown_request["tab"]
            return active_tab if active_tab in valid_tabs else "subject-data"

        @app.callback(
            Output("analytics-dashboard-tabs", "options"),
            Input("studies-dropdown", "value"),
            Input("sensor-store", "data"),
        )
        def update_dashboard_tab_options(study_name, sensors_map):
            return analytics_tab_options(sensors_map, study_name)

        @app.callback(
            Output("dq-filter-sensor-control", "style"),
            Output("dq-filter-controls", "style"),
            Output("dq-timeline-x-axis-control", "style"),
            Output("live-summary-pane", "style"),
            Output("overview-subject-profile", "style"),
            Output("analytics-dashboard-tabs", "style"),
            Output("dq-filter-subject-control", "style"),
            Output("subject-dashboard-pane", "style"),
            Output("subject-detail-dashboard-pane", "style"),
            Output("sensor-dashboard-pane", "style"),
            Output("device-sensor-dashboard-pane", "style"),
            Output("ema-dashboard-pane", "style"),
            Output("ema-frequency-filter-control", "style"),
            Input("analytics-dashboard-tabs", "value"),
            Input("studies-dropdown", "value"),
            Input("overview-subject-select", "value"),
        )
        def switch_dashboard_tab(active_tab, study_name, selected_subject):
            tab_style = {"marginBottom": "1.25rem"}
            overview_kpi_style = {"display": "block"}
            subject_kpi_style = {"display": "none"}
            timeline_axis_style = {"display": "grid"}
            subject_filter_style = {"display": "grid"}

            if selected_subject:
                return (
                    {"display": "none"},
                    {"display": "none"},
                    timeline_axis_style,
                    {"display": "none"},
                    {"display": "block"},
                    {"display": "none"},
                    {"display": "none"},
                    {"display": "none"},
                    {"display": "block"},
                    {"display": "none"},
                    {"display": "none"},
                    {"display": "none"},
                    {"display": "none"},
                )

            if active_tab == "ema-data":
                frequency_style = {"display": "none"} if is_optional_only_ema_study(study_name) else {"display": "grid"}
                return {"display": "none"}, {"display": "grid"}, timeline_axis_style, overview_kpi_style, subject_kpi_style, tab_style, subject_filter_style, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "block"}, frequency_style
            if active_tab == "device-sensor-data":
                return {"display": "none"}, {"display": "grid"}, timeline_axis_style, overview_kpi_style, subject_kpi_style, tab_style, subject_filter_style, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "none"}
            if active_tab == "sensor-data":
                return {"display": "none"}, {"display": "grid"}, timeline_axis_style, overview_kpi_style, subject_kpi_style, tab_style, subject_filter_style, {"display": "none"}, {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "none"}
            return (
                {"display": "none"},
                {"display": "grid"},
                timeline_axis_style,
                overview_kpi_style,
                subject_kpi_style,
                tab_style,
                subject_filter_style,
                {"display": "block"},
                {"display": "none"},
                {"display": "none"},
                {"display": "none"},
                {"display": "none"},
                {"display": "none"},
            )

    def register_status_callbacks(self):
        app = self.app

        @app.callback(
            Output("dq-dashboard-status", "children"),
            Input("studies-dropdown", "value"),
        )
        def update_quality_dashboard_status(study_name):
            if not study_name:
                return str(_("Select study"))
            return f"{study_name} · {len(update_selector(study_name))} CSV files"

        @app.callback(
            Output("live-dashboard-status", "children"),
            Output(LIVE_SUMMARY_CARD["id"], "children"),
            Output("live-warning-panel", "children"),
            Output("analytics-drilldown-payloads", "data"),
            Output("live-summary-content", "style"),
            Output("analytics-results-content", "style"),
            Output("analytics-no-data-message", "children"),
            Output("analytics-no-data-message", "style"),
            Input("studies-dropdown", "value"),
            Input("analytics-dashboard-tabs", "value"),
            Input("dq-filter-subject", "value"),
            Input("dq-filter-subject-mode", "value"),
            Input("dq-filter-subject", "options"),
            Input("overview-subject-select", "value"),
        )
        def update_live_dashboard_status(
            study_name,
            active_tab,
            subjects,
            subject_filter_mode,
            subject_options,
            selected_subject,
        ):
            if not study_name:
                return (
                    str(_("Select study")),
                    [],
                    [],
                    {},
                    {"display": "none"},
                    {"display": "none"},
                    "",
                    {"display": "none"},
                )

            if not study_has_analytics_csvs(study_name):
                return (
                    f"{study_name} · 0 study overview files",
                    [],
                    [],
                    {},
                    {"display": "none"},
                    {"display": "none"},
                    str(_("No data is available for this study.")),
                    {"display": "block"},
                )

            available_count = sum(
                1
                for card in LIVE_MONITORING_CARDS
                if load_quality_csv(study_name, card["filename"]) is not None
            )
            status = f"{study_name} · {available_count} study overview files"
            if selected_subject:
                return (
                    status,
                    [],
                    [],
                    {},
                    {"display": "none"},
                    {"display": "block"},
                    "",
                    {"display": "none"},
                )

            subjects = resolve_subject_filter(
                subjects,
                subject_filter_mode,
                subject_options,
            )
            cards, findings, payloads = build_connected_dashboard_summary(
                active_tab,
                study_name,
                subjects,
            )
            return (
                status,
                cards,
                findings,
                payloads,
                {"display": "block"},
                {"display": "block"},
                "",
                {"display": "none"},
            )

        @app.callback(
            Output("overview-subject-profile", "children"),
            Input("studies-dropdown", "value"),
            Input("overview-subject-select", "value"),
            Input("sensor-store", "data"),
        )
        def update_overview_subject_profile(study_name, selected_subject, sensors_map):
            return build_subject_profile_summary(
                study_name,
                selected_subject,
                sensors_map,
            )

    def register_download_callbacks(self):
        for quality_card in QUALITY_DASHBOARD_CARDS:
            self.register_card_download_callback(quality_card, quality_download_frame)

        for live_card in LIVE_MONITORING_CARDS:
            if live_card.get("type") == "kpi":
                continue
            self.register_card_download_callback(live_card, live_download_frame)

    def register_card_download_callback(self, card, download_frame_func):
        app = self.app
        chart_id = card["id"]

        if not card.get("raw_data"):
            @app.callback(
                Output(f"{chart_id}-csv-download", "data"),
                Input(f"{chart_id}-download-csv", "n_clicks"),
                State("analytics-dashboard-tabs", "value"),
                State("studies-dropdown", "value"),
                State("dq-filter-sensor", "value"),
                State("dq-filter-subject", "value"),
                State("dq-filter-subject-mode", "value"),
                State("dq-filter-subject", "options"),
                prevent_initial_call=True,
            )
            def download_quality_csv(
                n_clicks,
                active_tab,
                study_name,
                sensors,
                subjects,
                subject_filter_mode,
                subject_options,
            ):
                if not n_clicks or not study_name:
                    raise PreventUpdate

                path = source_csv_path(card, study_name)
                if path:
                    source_download = send_source_csv_files(path, study_name, chart_id)
                    if source_download:
                        return source_download

                subjects = resolve_subject_filter(
                    subjects,
                    subject_filter_mode,
                    subject_options,
                )
                df = download_frame_func(
                    card,
                    study_name,
                    sensor_filter_for_download(card, active_tab, sensors),
                    subjects,
                )
                filename = safe_download_filename(study_name, chart_id, extension="csv")
                return dcc.send_data_frame(df.to_csv, filename, index=False)

        if not card.get("table_download"):
            app.clientside_callback(
                f"""
                function(n_clicks) {{
                    if (!n_clicks) {{
                        return window.dash_clientside.no_update;
                    }}
                    const graph = document.getElementById("{chart_id}");
                    const plot = graph ? graph.querySelector(".js-plotly-plot") : null;
                    if (plot && window.Plotly) {{
                        window.Plotly.downloadImage(plot, {{
                            format: "png",
                            filename: "{chart_id}",
                            height: 700,
                            width: 1000,
                            scale: 2
                        }});
                    }}
                    return String(n_clicks);
                }}
                """,
                Output(f"{chart_id}-image-download-trigger", "children"),
                Input(f"{chart_id}-download-image", "n_clicks"),
            )

        app.clientside_callback(
            f"""
            function(n_clicks) {{
                if (!n_clicks) {{
                    return window.dash_clientside.no_update;
                }}

                const trigger = document.getElementById("{chart_id}-fullscreen");
                const card = trigger ? trigger.closest(".analytics-chart-card") : null;
                if (!card) {{
                    return window.dash_clientside.no_update;
                }}

                const fullscreenElement = document.fullscreenElement || document.webkitFullscreenElement;
                const requestFullscreen = card.requestFullscreen || card.webkitRequestFullscreen;
                const exitFullscreen = document.exitFullscreen || document.webkitExitFullscreen;
                const resizePlot = function() {{
                    const plot = card.querySelector(".js-plotly-plot");
                    if (plot && window.Plotly) {{
                        window.Plotly.Plots.resize(plot);
                    }}
                }};
                const fallbackClass = "analytics-chart-card-fullscreen";

                if (card.classList.contains(fallbackClass)) {{
                    card.classList.remove(fallbackClass);
                    window.setTimeout(resizePlot, 100);
                    return String(n_clicks);
                }}

                let fullscreenPromise;
                if (fullscreenElement === card && exitFullscreen) {{
                    fullscreenPromise = exitFullscreen.call(document);
                }} else if (requestFullscreen) {{
                    fullscreenPromise = requestFullscreen.call(card);
                }} else {{
                    card.classList.add(fallbackClass);
                    window.setTimeout(resizePlot, 100);
                    return String(n_clicks);
                }}

                Promise.resolve(fullscreenPromise).then(function() {{
                    window.setTimeout(resizePlot, 100);
                }}).catch(function() {{
                    card.classList.add(fallbackClass);
                    window.setTimeout(resizePlot, 100);
                }});
                return String(n_clicks);
            }}
            """,
            Output(f"{chart_id}-fullscreen-trigger", "children"),
            Input(f"{chart_id}-fullscreen", "n_clicks"),
        )

        if card.get("table_download"):
            self.register_table_excel_download_callback(card)

    def register_table_excel_download_callback(self, card):
        app = self.app
        chart_id = card["id"]

        @app.callback(
            Output(f"{chart_id}-excel-download", "data"),
            Input(f"{chart_id}-download-excel", "n_clicks"),
            State(chart_id, "figure"),
            State("studies-dropdown", "value"),
            prevent_initial_call=True,
        )
        def download_table_excel(n_clicks, figure, study_name):
            if not n_clicks:
                raise PreventUpdate

            table_df = table_figure_download_frame(figure)
            filename = safe_download_filename(
                study_name,
                chart_id,
                extension="xlsx",
            )
            return dcc.send_data_frame(
                table_df.to_excel,
                filename,
                index=False,
                engine="openpyxl",
            )


def register_dashboard_callbacks(app):
    DashboardCallbacks(app).register()
