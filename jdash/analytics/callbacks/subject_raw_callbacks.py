"""Callbacks for the single-subject raw-data explorer."""

from dash import Input, Output, State, dcc
from dash.exceptions import PreventUpdate
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

from jdash.models import Study

from ..data.dashboard_data import safe_download_filename
from ..data.dashboard_data import visible_analytics_tabs
from ..data.raw_subject_data import RawSubjectDataError
from ..data.raw_subject_gateway import subject_raw_metadata, subject_sensor_series
from ..figures.common_figures import blank_quality_figure
from ..figures.raw_subject_figures import build_raw_subject_figure, raw_series_frame


SOURCE_CONFIG = {
    "smartphone": {
        "graph_id": "overview-subject-smartphone-progression",
        "metadata_source": "smartphone",
        "preferred_sensors": ("accelerometer", "activity", "pedometer", "location"),
    },
    "garmin": {
        "graph_id": "overview-subject-device-sensor-progression",
        "metadata_source": "wearable",
        "preferred_sensors": (
            "garmin_HEART_RATE",
            "garmin_STEPS",
            "garmin_STRESS",
        ),
    },
    "ema": {
        "graph_id": "overview-subject-ema-progression",
        "metadata_source": "ema",
        "fixed_sensor": "ema",
        "preferred_sensors": ("ema",),
    },
}


def _source_section_styles(sensors_map, study_name):
    """Mirror the main dashboard tab availability in the subject explorer."""
    tabs = visible_analytics_tabs(sensors_map, study_name)
    visible = {"display": "block"}
    hidden = {"display": "none"}
    return (
        visible if "sensor-data" in tabs else hidden,
        visible if "device-sensor-data" in tabs else hidden,
        visible if "ema-data" in tabs else hidden,
    )


def _period_options(study_duration):
    """Build 30-day windows through the configured study duration."""
    try:
        duration = max(0, int(study_duration or 0))
    except (TypeError, ValueError):
        duration = 0
    maximum = max(30, duration)
    periods = list(range(30, maximum + 1, 30))
    if duration > 30 and duration not in periods:
        periods.append(duration)
    periods.sort()
    return [
        {
            "label": str(_("Last %(days)s study days")) % {"days": days},
            "value": days,
        }
        for days in periods
    ]


def _source_sensors(metadata, source):
    if not isinstance(metadata, dict):
        return []
    return (metadata.get("sources") or {}).get(source, []) or []


def _preferred_sensor(sensors, preferred):
    names = {sensor.get("name") for sensor in sensors}
    for name in preferred:
        if name in names:
            return name
    return sensors[0].get("name") if sensors else None


def _sensor_metadata(metadata, source, sensor_name=None):
    sensors = _source_sensors(metadata, source)
    if not sensor_name and sensors:
        return sensors[0]
    return next(
        (sensor for sensor in sensors if sensor.get("name") == sensor_name),
        None,
    )


def _metric_options(sensor):
    metrics = (sensor or {}).get("metrics") or []
    return [
        {"label": metric.get("label") or metric.get("value"), "value": metric.get("value")}
        for metric in metrics
        if metric.get("value")
    ]


def _load_series(
    study_name,
    subject_id,
    source,
    sensor,
    metric,
    statistic,
    resolution,
    period,
):
    if not study_name or not subject_id:
        return None
    config = SOURCE_CONFIG[source]
    sensor = config.get("fixed_sensor") or sensor
    if not sensor or not metric:
        return None
    return subject_sensor_series(
        study_name,
        subject_id,
        sensor,
        metric=metric,
        statistic="count" if source == "ema" else (statistic or "mean"),
        resolution=resolution or "day",
        period_days=period or 30,
    )


def _register_metric_callback(app, source):
    config = SOURCE_CONFIG[source]
    inputs = [Input("subject-raw-metadata", "data")]
    if source != "ema":
        inputs.append(Input(f"subject-explorer-{source}-sensor", "value"))

    @app.callback(
        Output(f"subject-explorer-{source}-metric", "options"),
        Output(f"subject-explorer-{source}-metric", "value"),
        *inputs,
    )
    def update_metric_options(metadata, sensor_name=None):
        sensor_name = config.get("fixed_sensor") or sensor_name
        sensor = _sensor_metadata(metadata, config["metadata_source"], sensor_name)
        options = _metric_options(sensor)
        default = (sensor or {}).get("default_metric")
        valid_values = {option["value"] for option in options}
        return options, default if default in valid_values else (options[0]["value"] if options else None)


def _register_statistic_callback(app, source):
    if source == "ema":
        return

    @app.callback(
        Output(f"subject-explorer-{source}-statistic", "value"),
        Output(f"subject-explorer-{source}-statistic", "disabled"),
        Input(f"subject-explorer-{source}-metric", "value"),
        State(f"subject-explorer-{source}-statistic", "value"),
    )
    def sync_statistic(metric, current_statistic):
        if metric in {"records", "events", "responses", "submissions"}:
            return "count", True
        return current_statistic if current_statistic != "count" else "mean", False


def _register_figure_callback(app, source):
    config = SOURCE_CONFIG[source]
    inputs = [
        Input("studies-dropdown", "value"),
        Input("overview-subject-select", "value"),
    ]
    if source != "ema":
        inputs.append(Input(f"subject-explorer-{source}-sensor", "value"))
    inputs.extend(
        [
            Input(f"subject-explorer-{source}-metric", "value"),
            Input(f"subject-explorer-{source}-statistic", "value"),
            Input(f"subject-explorer-{source}-resolution", "value"),
            Input(f"subject-explorer-{source}-timeline", "value"),
            Input(f"subject-explorer-{source}-period", "value"),
        ]
    )

    @app.callback(Output(config["graph_id"], "figure"), *inputs)
    def update_raw_figure(study_name, subject_id, *values):
        if source == "ema":
            sensor = "ema"
            metric, statistic, resolution, timeline, period = values
        else:
            sensor, metric, statistic, resolution, timeline, period = values
        try:
            payload = _load_series(
                study_name,
                subject_id,
                source,
                sensor,
                metric,
                statistic,
                resolution,
                period,
            )
        except RawSubjectDataError as exc:
            return blank_quality_figure("", str(exc))
        return build_raw_subject_figure(payload, timeline)


def _register_download_callback(app, source):
    config = SOURCE_CONFIG[source]
    states = [
        State("studies-dropdown", "value"),
        State("overview-subject-select", "value"),
    ]
    if source != "ema":
        states.append(State(f"subject-explorer-{source}-sensor", "value"))
    states.extend(
        [
            State(f"subject-explorer-{source}-metric", "value"),
            State(f"subject-explorer-{source}-statistic", "value"),
            State(f"subject-explorer-{source}-resolution", "value"),
            State(f"subject-explorer-{source}-timeline", "value"),
            State(f"subject-explorer-{source}-period", "value"),
        ]
    )

    @app.callback(
        Output(f"{config['graph_id']}-csv-download", "data"),
        Input(f"{config['graph_id']}-download-csv", "n_clicks"),
        *states,
        prevent_initial_call=True,
    )
    def download_displayed_series(n_clicks, study_name, subject_id, *values):
        if not n_clicks or not study_name or not subject_id:
            raise PreventUpdate
        if source == "ema":
            sensor = "ema"
            metric, statistic, resolution, timeline, period = values
        else:
            sensor, metric, statistic, resolution, timeline, period = values
        try:
            payload = _load_series(
                study_name,
                subject_id,
                source,
                sensor,
                metric,
                statistic,
                resolution,
                period,
            )
        except RawSubjectDataError:
            raise PreventUpdate
        frame = raw_series_frame(payload, timeline)
        filename = safe_download_filename(
            study_name,
            subject_id,
            source,
            "raw-preview",
            extension="csv",
        )
        return dcc.send_data_frame(frame.to_csv, filename, index=False)


def register_subject_raw_callbacks(app):
    @app.callback(
        Output("subject-explorer-smartphone-period", "options"),
        Output("subject-explorer-smartphone-period", "value"),
        Output("subject-explorer-garmin-period", "options"),
        Output("subject-explorer-garmin-period", "value"),
        Output("subject-explorer-ema-period", "options"),
        Output("subject-explorer-ema-period", "value"),
        Input("studies-dropdown", "value"),
    )
    def update_subject_period_options(study_name):
        duration = (
            Study.objects.filter(title=study_name)
            .values_list("duration", flat=True)
            .first()
            if study_name
            else 0
        )
        options = _period_options(duration)
        return options, 30, options, 30, options, 30

    @app.callback(
        Output("subject-explorer-smartphone-section", "style"),
        Output("subject-explorer-garmin-section", "style"),
        Output("subject-explorer-ema-section", "style"),
        Input("studies-dropdown", "value"),
        Input("sensor-store", "data"),
    )
    def update_subject_source_sections(study_name, sensors_map):
        return _source_section_styles(sensors_map, study_name)

    @app.callback(
        Output("subject-raw-metadata", "data"),
        Output("subject-explorer-smartphone-sensor", "options"),
        Output("subject-explorer-smartphone-sensor", "value"),
        Output("subject-explorer-garmin-sensor", "options"),
        Output("subject-explorer-garmin-sensor", "value"),
        Output("subject-raw-data-download", "href"),
        Output("subject-raw-data-download", "style"),
        Input("studies-dropdown", "value"),
        Input("overview-subject-select", "value"),
    )
    def update_raw_metadata(study_name, subject_id):
        hidden = {"display": "none"}
        if not study_name or not subject_id:
            return None, [], None, [], None, None, hidden
        try:
            metadata = subject_raw_metadata(study_name, subject_id)
        except RawSubjectDataError:
            return None, [], None, [], None, None, hidden

        smartphone = _source_sensors(metadata, "smartphone")
        wearable = _source_sensors(metadata, "wearable")
        smartphone_options = [
            {"label": sensor["label"], "value": sensor["name"]}
            for sensor in smartphone
        ]
        wearable_options = [
            {"label": sensor["label"], "value": sensor["name"]}
            for sensor in wearable
        ]
        try:
            download_url = reverse(
                "download_subject_raw_data",
                kwargs={"study_name": study_name, "subject_id": subject_id},
            )
        except NoReverseMatch:
            download_url = None
        return (
            metadata,
            smartphone_options,
            _preferred_sensor(smartphone, SOURCE_CONFIG["smartphone"]["preferred_sensors"]),
            wearable_options,
            _preferred_sensor(wearable, SOURCE_CONFIG["garmin"]["preferred_sensors"]),
            download_url,
            {"display": "inline-flex"} if download_url else hidden,
        )

    for source in SOURCE_CONFIG:
        _register_metric_callback(app, source)
        _register_statistic_callback(app, source)
        _register_figure_callback(app, source)
        _register_download_callback(app, source)
