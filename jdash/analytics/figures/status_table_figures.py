"""Status table figure builders for analytics overview cards."""

import pandas as pd
import plotly.graph_objects as go
from django.utils.translation import gettext_lazy as _

from ..data.dashboard_data import first_matching_column, normalize_column_name
from .common_figures import blank_quality_figure, finish_quality_figure, status_color


def format_table_header(column, max_line_length=18):
    words = str(column).replace("_", " ").split()
    if not words:
        return "", 1

    lines = []
    current_line = []
    for word in words:
        candidate = " ".join(current_line + [word])
        if current_line and len(candidate) > max_line_length:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))

    return f"<b>{'<br>'.join(lines)}</b>", len(lines)


def build_status_table(df, columns, status_color_column=None, subject_color_column=None):
    visible_columns = [column for column in columns if column in df.columns]
    if not visible_columns:
        visible_columns = list(df.columns)

    table_df = df[visible_columns].copy()
    row_fill_colors = [
        "#ffffff" if index % 2 == 0 else "#fbfcfd"
        for index in range(len(table_df))
    ]
    column_widths = []
    for column in table_df.columns:
        normalized_column = normalize_column_name(column)
        if normalized_column in ("subject_id", "subject"):
            column_widths.append(1.75)
        elif normalized_column in ("smartphone_sensors", "wearables", "ema"):
            column_widths.append(1.35)
        elif normalized_column == "status":
            column_widths.append(0.85)
        elif normalized_column in (
            "days_since_last_data_received",
            "days_since_last_any_data",
            "days_since_last_data",
            "days_since_latest_data",
        ):
            column_widths.append(1.8)
        elif normalized_column in ("date_joined", "joined_date"):
            column_widths.append(1.05)
        else:
            column_widths.append(1.15)
    fill_color = [
        [
            status_color(value) if column == "Status" else row_fill_colors[index]
            for index, value in enumerate(table_df[column])
        ]
        for column in table_df.columns
    ]
    font_color = "#212529"
    if status_color_column and subject_color_column in table_df.columns and status_color_column in df.columns:
        status_values = df[status_color_column].reset_index(drop=True)
        font_color = [
            [
                status_color(status_values.iloc[index]) if column == subject_color_column else "#212529"
                for index in range(len(table_df))
            ]
            for column in table_df.columns
        ]

    formatted_headers = [format_table_header(column) for column in visible_columns]
    header_values = [header for header, _ in formatted_headers]
    header_line_count = max(line_count for _, line_count in formatted_headers)
    header_height = max(42, 22 + (16 * header_line_count))

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=column_widths,
                header={
                    "values": header_values,
                    "fill_color": "#1f2937",
                    "font": {"color": "#ffffff", "size": 13},
                    "align": "left",
                    "line": {"color": "#1f2937", "width": 1},
                    "height": header_height,
                },
                cells={
                    "values": [table_df[column] for column in table_df.columns],
                    "fill_color": fill_color,
                    "font": {"color": font_color, "size": 11},
                    "align": "left",
                    "line": {"color": "#e8edf3", "width": 1},
                    "height": 34,
                },
            )
        ]
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig

def first_non_empty_value(values):
    for value in values:
        if pd.notna(value) and str(value).strip():
            return str(value)
    return ""

def worst_subject_status(values):
    status_rank = {
        "critical": 3,
        "fail": 3,
        "error": 3,
        "watch": 2,
        "warning": 2,
        "healthy": 1,
        "ok": 1,
        "pass": 1,
        "good": 1,
    }
    worst_value = ""
    worst_rank = -1
    for value in values:
        if pd.isna(value):
            continue
        status = str(value).strip()
        rank = status_rank.get(status.lower(), 0)
        if rank > worst_rank:
            worst_value = status
            worst_rank = rank
    return worst_value


def parse_status_dates(values):
    text = pd.Series(values).astype("string").str.strip()
    text = text.replace(
        {
            "": pd.NA,
            "none": pd.NA,
            "None": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "NaT": pd.NA,
        }
    )
    parsed = pd.Series(pd.NaT, index=text.index, dtype="datetime64[ns]")
    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%b-%y",
    ):
        mask = parsed.isna() & text.notna()
        if not mask.any():
            break
        parsed.loc[mask] = pd.to_datetime(text.loc[mask], format=date_format, errors="coerce")
    return parsed


def sensor_group_column(sensor_group, sensor):
    group = normalize_column_name(sensor_group)
    sensor_name = normalize_column_name(sensor)

    if group == "ema" or sensor_name == "ema":
        return str(_("EMA"))
    if group in ("garmin", "wearable", "wearables", "device_sensor", "device_sensors") or (
        "garmin" in sensor_name or "wearable" in sensor_name
    ):
        return str(_("Wearables"))
    if group in ("smartphone", "phone", "passive_sensor", "passive_sensors", "sensor", "sensors"):
        return str(_("Smartphone Sensors"))
    return str(_("Other Sensors"))


def latest_group_dates(table_df, index_columns, group_col, last_date_col):
    latest_df = table_df[index_columns + [group_col, last_date_col]].copy()
    latest_df[last_date_col] = latest_df[last_date_col].fillna("").astype(str).str.strip()
    latest_df["_has_last_date"] = latest_df[last_date_col].astype(bool)
    latest_df["_parsed_last_date"] = parse_status_dates(latest_df[last_date_col])
    latest_df = latest_df.sort_values(
        index_columns + [group_col, "_has_last_date", "_parsed_last_date", last_date_col],
        na_position="first",
    )
    latest_df = latest_df.groupby(index_columns + [group_col], as_index=False).tail(1)
    pivot = latest_df.pivot_table(
        index=index_columns,
        columns=group_col,
        values=last_date_col,
        aggfunc=first_non_empty_value,
        fill_value="",
    ).reset_index()
    pivot.columns = [str(column) for column in pivot.columns]
    return pivot


def build_subject_sensor_status_table(df):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    date_joined_col = first_matching_column(df.columns, ["Date_joined", "date_joined", "Joined_date"])
    sensor_group_col = first_matching_column(df.columns, ["Sensor_group", "sensor_group", "Group"])
    sensor_col = first_matching_column(df.columns, ["Sensor", "sensor"])
    status_col = first_matching_column(df.columns, ["Status", "status"])
    last_date_col = first_matching_column(
        df.columns,
        ["Last_data_received_date", "Last_any_data_date", "Last_data_date"],
    )
    days_since_col = first_matching_column(
        df.columns,
        ["Days_since_last_data_received", "Days_since_last_any_data", "Days_since_last_data"],
    )
    if not subject_col or not date_joined_col or not sensor_col or not last_date_col:
        return blank_quality_figure(
            _("Subject Status"),
            _("Subject sensor status file is missing subject, joined date, sensor, or last data date columns."),
        )

    table_df = df[[subject_col, date_joined_col, sensor_col, last_date_col]].copy()
    table_df[subject_col] = table_df[subject_col].fillna("").astype(str)
    table_df[date_joined_col] = table_df[date_joined_col].fillna("").astype(str)
    table_df[sensor_col] = table_df[sensor_col].fillna("").astype(str)
    table_df[last_date_col] = table_df[last_date_col].fillna("").astype(str)
    table_df = table_df[table_df[subject_col].astype(bool) & table_df[sensor_col].astype(bool)]
    if table_df.empty:
        return blank_quality_figure(_("Subject Status"))

    index_columns = [subject_col, date_joined_col]
    if sensor_group_col:
        table_df[sensor_group_col] = df.loc[table_df.index, sensor_group_col].fillna("").astype(str)
    else:
        sensor_group_col = "_Sensor_group"
        table_df[sensor_group_col] = ""
    group_display_col = "_Sensor_group_display"
    table_df[group_display_col] = table_df.apply(
        lambda row: sensor_group_column(row[sensor_group_col], row[sensor_col]),
        axis=1,
    )

    pivot = latest_group_dates(table_df, index_columns, group_display_col, last_date_col)
    group_columns = [
        str(_("Smartphone Sensors")),
        str(_("Wearables")),
        str(_("EMA")),
        str(_("Other Sensors")),
    ]
    for group_column in group_columns:
        if group_column in pivot.columns:
            pivot[group_column] = pivot[group_column].replace("", "--")

    if status_col:
        status_df = df[[subject_col, date_joined_col, status_col]].copy()
        status_df[subject_col] = status_df[subject_col].fillna("").astype(str)
        status_df[date_joined_col] = status_df[date_joined_col].fillna("").astype(str)
        status_df = (
            status_df
            .groupby([subject_col, date_joined_col], as_index=False)[status_col]
            .agg(worst_subject_status)
            .rename(columns={status_col: "Status"})
        )
        pivot = pivot.merge(status_df, on=[subject_col, date_joined_col], how="left")

    if days_since_col:
        days_since_df = df[[subject_col, date_joined_col, days_since_col]].copy()
        days_since_df[subject_col] = days_since_df[subject_col].fillna("").astype(str)
        days_since_df[date_joined_col] = days_since_df[date_joined_col].fillna("").astype(str)
        days_since_df[days_since_col] = pd.to_numeric(days_since_df[days_since_col], errors="coerce")
        days_since_df = (
            days_since_df
            .groupby([subject_col, date_joined_col], as_index=False)[days_since_col]
            .max()
            .rename(columns={days_since_col: "Days_since_last_data_received"})
        )
        pivot = pivot.merge(days_since_df, on=[subject_col, date_joined_col], how="left")
        pivot["Days_since_last_data_received"] = pivot["Days_since_last_data_received"].map(
            lambda value: "" if pd.isna(value) else f"{float(value):.0f}"
        )

    display_column_map = {
        subject_col: str(_("Subject ID")),
        date_joined_col: str(_("Date Joined")),
        "Days_since_last_data_received": str(_("Days Since Latest Data")),
    }
    pivot = pivot.rename(columns=display_column_map)

    subject_display_col = display_column_map[subject_col]
    visible_columns = [subject_display_col, display_column_map[date_joined_col]]
    visible_columns += [column for column in group_columns if column in pivot.columns]
    days_since_display_col = display_column_map["Days_since_last_data_received"]
    if days_since_display_col in pivot.columns:
        visible_columns.append(days_since_display_col)
    return build_status_table(
        pivot,
        visible_columns,
        status_color_column="Status",
        subject_color_column=subject_display_col,
    )
