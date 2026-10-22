import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output
from dash.exceptions import PreventUpdate

from jdash.analytics.csv_utils import get_csv_display_name, read_selected_csv


SUBJECT_KEYS = ("subject", "subject_id", "subjectid", "subject-id", "participant", "participant_id")
SENSOR_KEYS = ("sensor", "sensor_name", "sensorname", "data_type", "datatype", "stream")
DEVICE_KEYS = ("device", "device_id", "deviceid", "device_name", "devicename", "wearable", "platform")
STAGE_KEYS = ("stage", "qc_stage", "qcstage", "step", "reason", "flag", "anomaly", "status")
TIME_KEYS = ("date", "day", "study_day", "studyday", "timestamp", "time", "datetime")


def register_data_quality_callbacks(app):
    def normalize(value):
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def first_matching_column(columns, keys):
        normalized = {normalize(col): col for col in columns}
        for key in keys:
            key_norm = normalize(key)
            if key_norm in normalized:
                return normalized[key_norm]
        for col in columns:
            normalized_col = normalize(col)
            if any(key in normalized_col for key in keys):
                return col
        return None

    def option_list(values):
        cleaned = sorted(str(value) for value in pd.Series(values).dropna().unique())
        return [{"label": value, "value": value} for value in cleaned]

    def numeric_columns(df):
        return df.select_dtypes(include="number").columns.tolist()

    def default_x_column(df):
        time_col = first_matching_column(df.columns, TIME_KEYS)
        if time_col:
            return time_col
        subject_col = first_matching_column(df.columns, SUBJECT_KEYS)
        if subject_col:
            return subject_col
        return df.columns[0] if len(df.columns) else None

    def default_y_column(df):
        excluded = {
            normalize(col)
            for col in [
                first_matching_column(df.columns, SUBJECT_KEYS),
                first_matching_column(df.columns, SENSOR_KEYS),
                first_matching_column(df.columns, DEVICE_KEYS),
                first_matching_column(df.columns, STAGE_KEYS),
                first_matching_column(df.columns, TIME_KEYS),
            ]
            if col
        }
        for col in numeric_columns(df):
            if normalize(col) not in excluded:
                return col
        nums = numeric_columns(df)
        return nums[0] if nums else (df.columns[0] if len(df.columns) else None)

    def blank_fig(title):
        fig = go.Figure()
        fig.update_layout(title=title, margin=dict(l=20, r=20, t=50, b=20))
        return fig

    def apply_multi_filter(df, column, selected_values):
        if not column or not selected_values:
            return df
        selected = [str(value) for value in selected_values]
        return df[df[column].astype(str).isin(selected)]

    def filtered_df(csv_path, subject_values, sensor_values, device_values, stage_values):
        df = read_selected_csv(csv_path)
        subject_col = first_matching_column(df.columns, SUBJECT_KEYS)
        sensor_col = first_matching_column(df.columns, SENSOR_KEYS)
        device_col = first_matching_column(df.columns, DEVICE_KEYS)
        stage_col = first_matching_column(df.columns, STAGE_KEYS)

        df = apply_multi_filter(df, subject_col, subject_values)
        df = apply_multi_filter(df, sensor_col, sensor_values)
        df = apply_multi_filter(df, device_col, device_values)
        df = apply_multi_filter(df, stage_col, stage_values)
        return df, subject_col, sensor_col, device_col, stage_col

    def infer_quality_chart(filename, chart_type, df, x_col, y_col, subject_col, sensor_col, stage_col):
        if chart_type and chart_type != "auto":
            return chart_type

        name = get_csv_display_name(filename).lower()
        if "heatmap" in name or "matrix" in name or "timeline" in name:
            return "heatmap"
        if "retention" in name or "coverage" in name or "volume" in name:
            return "line"
        if "funnel" in name or "loss_by_stage" in name or "missingness" in name:
            return "bar"
        if x_col and y_col and subject_col and len(df[x_col].dropna().unique()) > 2:
            return "line"
        if stage_col or sensor_col:
            return "bar"
        return "scatter"

    @app.callback(
        Output("dq-x-axis", "options"),
        Output("dq-x-axis", "value"),
        Output("dq-y-axis", "options"),
        Output("dq-y-axis", "value"),
        Output("dq-subject-filter", "options"),
        Output("dq-sensor-filter", "options"),
        Output("dq-device-filter", "options"),
        Output("dq-stage-filter", "options"),
        Input("csv-dropdown", "value"),
    )
    def populate_data_quality_controls(csv_path):
        if not csv_path:
            raise PreventUpdate

        df = read_selected_csv(csv_path)
        columns = [{"label": col, "value": col} for col in df.columns]
        y_columns = [{"label": col, "value": col} for col in numeric_columns(df)] or columns

        subject_col = first_matching_column(df.columns, SUBJECT_KEYS)
        sensor_col = first_matching_column(df.columns, SENSOR_KEYS)
        device_col = first_matching_column(df.columns, DEVICE_KEYS)
        stage_col = first_matching_column(df.columns, STAGE_KEYS)

        return (
            columns,
            default_x_column(df),
            y_columns,
            default_y_column(df),
            option_list(df[subject_col]) if subject_col else [],
            option_list(df[sensor_col]) if sensor_col else [],
            option_list(df[device_col]) if device_col else [],
            option_list(df[stage_col]) if stage_col else [],
        )

    @app.callback(
        Output("data-quality-plot", "figure"),
        Input("csv-dropdown", "value"),
        Input("dq-chart-type", "value"),
        Input("dq-x-axis", "value"),
        Input("dq-y-axis", "value"),
        Input("dq-subject-filter", "value"),
        Input("dq-sensor-filter", "value"),
        Input("dq-device-filter", "value"),
        Input("dq-stage-filter", "value"),
    )
    def update_data_quality_plot(
        csv_path,
        chart_type,
        x_col,
        y_col,
        subject_values,
        sensor_values,
        device_values,
        stage_values,
    ):
        if not csv_path:
            raise PreventUpdate

        try:
            df, subject_col, sensor_col, _device_col, stage_col = filtered_df(
                csv_path,
                subject_values,
                sensor_values,
                device_values,
                stage_values,
            )
        except Exception as exc:
            return blank_fig(f"Could not read data quality CSV: {exc}")

        if df.empty:
            return blank_fig("No data matches the selected filters.")
        if not x_col or x_col not in df.columns:
            x_col = default_x_column(df)
        if not y_col or y_col not in df.columns:
            y_col = default_y_column(df)
        if not x_col or not y_col:
            return blank_fig("Select valid columns to plot.")

        df = df.copy()
        if y_col in df.columns:
            df[y_col] = pd.to_numeric(df[y_col], errors="ignore")

        color_col = sensor_col or stage_col
        selected_chart = infer_quality_chart(csv_path, chart_type, df, x_col, y_col, subject_col, sensor_col, stage_col)
        title = get_csv_display_name(csv_path).replace(".csv", "")

        try:
            if "sensor_availability_matrix" in get_csv_display_name(csv_path).lower() and subject_col:
                matrix_cols = [
                    col for col in df.columns
                    if col != subject_col and pd.api.types.is_numeric_dtype(pd.to_numeric(df[col], errors="coerce"))
                ]
                if not matrix_cols:
                    return blank_fig("No sensor availability columns found.")
                matrix = df[[subject_col] + matrix_cols].copy()
                for col in matrix_cols:
                    matrix[col] = pd.to_numeric(matrix[col], errors="coerce").fillna(0)
                matrix = matrix.set_index(subject_col)
                fig = px.imshow(
                    matrix,
                    aspect="auto",
                    color_continuous_scale="Viridis",
                    title=title,
                )
            elif selected_chart == "heatmap" and subject_col:
                heatmap = df.pivot_table(
                    index=subject_col,
                    columns=x_col,
                    values=y_col,
                    aggfunc="mean",
                    fill_value=0,
                )
                fig = px.imshow(
                    heatmap,
                    aspect="auto",
                    color_continuous_scale="Viridis",
                    title=title,
                )
            elif selected_chart == "line":
                fig = px.line(df, x=x_col, y=y_col, color=color_col, markers=True, title=title, template="simple_white")
            elif selected_chart == "bar":
                fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, template="simple_white")
            elif selected_chart == "box":
                fig = px.box(df, x=x_col, y=y_col, color=color_col, title=title, template="simple_white")
            else:
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title, template="simple_white")
        except Exception as exc:
            return blank_fig(f"Could not build plot: {exc}")

        fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="closest")
        return fig
