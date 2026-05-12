import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Output, Input
from dash.exceptions import PreventUpdate


def read_csv_flexible(csv_path):
    """Read comma- or semicolon-delimited CSVs with a small fallback."""
    try:
        df = pd.read_csv(csv_path)
        if len(df.columns) == 1 and ";" in str(df.columns[0]):
            return pd.read_csv(csv_path, sep=";")
        return df
    except Exception:
        return pd.read_csv(csv_path, sep=";")


def blank_fig(title_text):
    fig = go.Figure(go.Heatmap(z=[[None]], showscale=False, hoverinfo="skip"))
    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    fig.update_layout(title=title_text, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def normalize_name(value):
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def detect_ema_file_type(csv_path):
    name = os.path.basename(csv_path).lower()
    if "question_summary" in name:
        return "question_summary"
    if "subject_summary" in name:
        return "subject_summary"
    return "responses"


def find_subject_column(columns):
    for col in columns:
        if normalize_name(col) in {"subject_id", "subject"}:
            return col
    return None


def get_numeric_columns(df):
    return [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]


def build_question_label_column(df):
    question_id_col = next((col for col in df.columns if normalize_name(col) == "question_id"), None)
    question_title_col = next((col for col in df.columns if normalize_name(col) == "question_title"), None)

    if not question_id_col and not question_title_col:
        return None, df

    question_labels = []
    for _, row in df.iterrows():
        question_id = str(row.get(question_id_col, "") or "").strip() if question_id_col else ""
        question_title = str(row.get(question_title_col, "") or "").strip() if question_title_col else ""

        if question_title and question_id:
            question_labels.append(f"{question_id} | {question_title}")
        elif question_title:
            question_labels.append(question_title)
        else:
            question_labels.append(question_id)

    result = df.copy()
    result["Question_Label"] = question_labels
    return "Question_Label", result


def build_response_question_label_column(df):
    question_id_col = next((col for col in df.columns if normalize_name(col) == "question_id"), None)
    question_title_col = next((col for col in df.columns if normalize_name(col) == "question_title"), None)
    question_subtext_col = next((col for col in df.columns if normalize_name(col) == "question_subtext"), None)

    if not question_id_col and not question_title_col and not question_subtext_col:
        return None, df

    question_labels = []
    for _, row in df.iterrows():
        question_id = str(row.get(question_id_col, "") or "").strip() if question_id_col else ""
        question_title = str(row.get(question_title_col, "") or "").strip() if question_title_col else ""
        question_subtext = str(row.get(question_subtext_col, "") or "").strip() if question_subtext_col else ""

        label_text = question_title or question_subtext or question_id
        if question_id and label_text and label_text != question_id:
            question_labels.append(f"{question_id} | {label_text}")
        else:
            question_labels.append(label_text or question_id)

    result = df.copy()
    result["Question_Label"] = question_labels
    return "Question_Label", result


def get_summary_dimensions(df, file_type):
    if file_type == "question_summary":
        return build_question_label_column(df)
    if file_type == "subject_summary":
        subject_col = find_subject_column(df.columns)
        return subject_col, df
    return None, df


def get_default_numeric_column(df):
    numeric_columns = get_numeric_columns(df)
    preferred = [
        "Answer_Row_Count",
        "Submission_Count",
        "Unique_Subject_Count",
        "Avg_Submissions_Per_Active_Day",
        "Avg_Answers_Per_Submission",
        "Answer_Value",
    ]
    for candidate in preferred:
        if candidate in numeric_columns:
            return candidate
    return numeric_columns[0] if numeric_columns else None


def get_default_subject_summary_metric(df):
    numeric_columns = get_numeric_columns(df)
    preferred = [
        "Submission_Count",
        "Active_Days",
        "Avg_Submissions_Per_Active_Day",
        "Answer_Row_Count",
        "Unique_Questions_Answered",
        "Free_Text_Response_Count",
        "Avg_Answers_Per_Submission",
    ]
    for candidate in preferred:
        if candidate in numeric_columns:
            return candidate
    return numeric_columns[0] if numeric_columns else None


def get_summary_filter_values(df, label_column):
    if not label_column or label_column not in df.columns:
        return []
    return sorted(df[label_column].dropna().astype(str).unique().tolist())


def get_x_axis_options(df, file_type):
    if file_type in {"question_summary", "subject_summary"}:
        label_column, _ = get_summary_dimensions(df, file_type)
        return [label_column] if label_column else []
    label_column, _ = build_response_question_label_column(df)
    if label_column:
        remaining_columns = [col for col in df.columns.tolist() if col != label_column]
        return [label_column] + remaining_columns
    return df.columns.tolist()


def get_y_axis_options(df, file_type):
    if file_type in {"question_summary", "subject_summary"}:
        return get_numeric_columns(df)
    preferred = [
        "Answer_Option_Text",
        "Free_Text",
        "Answer_Text",
        "Answer_Value",
    ]
    answer_columns = [col for col in preferred if col in df.columns]
    if answer_columns:
        return answer_columns
    numeric_columns = get_numeric_columns(df)
    return numeric_columns or df.columns.tolist()


def get_default_x_axis(df, file_type):
    if file_type in {"question_summary", "subject_summary"}:
        label_column, _ = get_summary_dimensions(df, file_type)
        return label_column
    label_column, _ = build_response_question_label_column(df)
    if label_column:
        return label_column
    for candidate in ["Question_Title", "Question_ID", "Date", "Study_day", "Timestamp_iso", "Timestamp_ms"]:
        if candidate in df.columns:
            return candidate
    columns = df.columns.tolist()
    return columns[0] if columns else None


def get_default_y_axis(df, file_type):
    if file_type == "subject_summary":
        return get_default_subject_summary_metric(df)
    if file_type == "question_summary":
        return get_default_numeric_column(df)
    for candidate in ["Answer_Option_Text", "Free_Text", "Answer_Text", "Answer_Value"]:
        if candidate in df.columns:
            return candidate
    return get_default_numeric_column(df) or (df.columns[0] if len(df.columns) > 0 else None)


def build_summary_heatmap(filtered_df, label_column, numeric_columns, title_text):
    if filtered_df.empty or not label_column or not numeric_columns:
        return blank_fig("No EMA summary data available.")

    heatmap_source = filtered_df[[label_column] + numeric_columns].copy()
    heatmap_source[label_column] = heatmap_source[label_column].astype(str)
    heatmap_source = heatmap_source.drop_duplicates(subset=[label_column], keep="last")
    heatmap_source = heatmap_source.set_index(label_column)
    heatmap_source = heatmap_source.apply(pd.to_numeric, errors="coerce")
    heatmap_source = heatmap_source.dropna(axis=0, how="all").dropna(axis=1, how="all")

    if heatmap_source.empty:
        return blank_fig("No EMA summary data available after filtering.")

    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_source.values,
            x=[str(item) for item in heatmap_source.columns.tolist()],
            y=[str(item) for item in heatmap_source.index.tolist()],
            colorscale="Cividis",
            colorbar={"title": "Value"},
        )
    )
    fig.update_layout(
        title=title_text,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def build_summary_histogram(filtered_df, metric_column, label_column, title_text):
    if metric_column not in filtered_df.columns:
        return blank_fig("Select a valid EMA metric.")

    histogram_source = filtered_df[[metric_column] + ([label_column] if label_column in filtered_df.columns else [])].copy()
    histogram_source[metric_column] = pd.to_numeric(histogram_source[metric_column], errors="coerce")
    histogram_source = histogram_source.dropna(subset=[metric_column])

    if histogram_source.empty:
        return blank_fig("No numeric EMA summary values available for the selected metric.")

    color_column = None
    if label_column in histogram_source.columns and histogram_source[label_column].nunique(dropna=True) <= 20:
        color_column = label_column

    fig = px.histogram(
        histogram_source,
        x=metric_column,
        color=color_column,
        barmode="overlay",
        title=title_text,
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    return fig


def register_ema_callbacks(app):
    @app.callback(
        [
            Output("ema-x-axis-dropdown", "options"),
            Output("ema-x-axis-dropdown", "value"),
            Output("ema-y-axis-dropdown", "options"),
            Output("ema-y-axis-dropdown", "value"),
            Output("ema-subject-id", "options"),
            Output("ema-x-axis-label", "children"),
            Output("ema-y-axis-label", "children"),
            Output("ema-x-axis-values-label", "children"),
            Output("ema-subject-label", "children"),
            Output("ema-x-axis-container", "style"),
            Output("ema-y-axis-container", "style"),
            Output("ema-x-axis-values-container", "style"),
            Output("ema-subject-container", "style"),
        ],
        Input("csv-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_ema_variable_dropdowns(csv_path):
        if not csv_path:
            raise PreventUpdate

        df = read_csv_flexible(csv_path)
        file_type = detect_ema_file_type(csv_path)
        subject_column = find_subject_column(df.columns)

        x_axis_columns = get_x_axis_options(df, file_type)
        y_axis_columns = get_y_axis_options(df, file_type)

        x_axis_options = [{"label": col, "value": col} for col in x_axis_columns]
        y_axis_options = [{"label": col, "value": col} for col in y_axis_columns]
        default_x_axis = get_default_x_axis(df, file_type)
        default_y_axis = get_default_y_axis(df, file_type)

        subject_options = []
        if subject_column:
            subjects = sorted(map(str, df[subject_column].dropna().unique()))
            subject_options = [{"label": subject, "value": subject} for subject in subjects]

        x_axis_label = "Select response dimension:"
        y_axis_label = "Select response metric:"
        x_axis_values_label = "Filter selected dimension values:"
        subject_label = "Filter subjects:"
        x_axis_style = {"margin-top": "20px", "margin-bottom": "20px"}
        y_axis_style = {"margin-bottom": "20px"}
        x_axis_values_style = {"margin-bottom": "20px"}
        subject_style = {"margin-bottom": "20px"}

        if file_type == "question_summary":
            x_axis_label = "Summary dimension:"
            y_axis_label = "Summary metric:"
            x_axis_values_label = "Filter questions:"
            subject_label = "Subject filter not used for question summaries"
            subject_style = {"display": "none"}
        elif file_type == "subject_summary":
            x_axis_label = "Summary dimension:"
            y_axis_label = "Summary metric:"
            x_axis_values_label = "Filter subjects:"
            subject_label = "Filter subjects:"
            x_axis_values_style = {"display": "none"}
        return (
            x_axis_options,
            default_x_axis,
            y_axis_options,
            default_y_axis,
            subject_options,
            x_axis_label,
            y_axis_label,
            x_axis_values_label,
            subject_label,
            x_axis_style,
            y_axis_style,
            x_axis_values_style,
            subject_style,
        )

    @app.callback(
        [
            Output("ema-x-axis-values", "options"),
            Output("ema-x-axis-values", "value"),
        ],
        Input("csv-dropdown", "value"),
        Input("ema-x-axis-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_ema_x_axis_values(csv_path, x_axis_column):
        if not csv_path:
            return [], None

        df = read_csv_flexible(csv_path)
        file_type = detect_ema_file_type(csv_path)

        if file_type in {"question_summary", "subject_summary"}:
            label_column, summary_df = get_summary_dimensions(df, file_type)
            if not label_column or x_axis_column != label_column:
                return [], None
            unique_values = get_summary_filter_values(summary_df, label_column)
            options = [{"label": value, "value": value} for value in unique_values]
            return options, None

        response_label_column, response_df = build_response_question_label_column(df)
        if response_label_column and x_axis_column == response_label_column:
            unique_values = sorted(response_df[response_label_column].dropna().astype(str).unique().tolist())
            options = [{"label": value, "value": value} for value in unique_values]
            return options, None

        if not x_axis_column or x_axis_column not in df.columns:
            return [], None

        unique_values = sorted(df[x_axis_column].dropna().astype(str).unique().tolist())
        if len(unique_values) > 200 and x_axis_column not in {"Question_Title", "Question_ID"}:
            return [], None

        options = [{"label": value, "value": value} for value in unique_values]
        default_values = unique_values[: min(10, len(unique_values))] if x_axis_column in {"Question_Title", "Question_ID"} else None
        return options, default_values

    @app.callback(
        [Output("ema-selected-plot", "figure"), Output("ema-mean-plot", "figure")],
        Input("ema-x-axis-dropdown", "value"),
        Input("ema-y-axis-dropdown", "value"),
        Input("ema-x-axis-values", "value"),
        Input("ema-subject-id", "value"),
        Input("csv-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_ema_plot(x_axis_column, y_axis_column, x_axis_values, subject_ids, selected_file):
        if not selected_file:
            raise PreventUpdate

        try:
            df = read_csv_flexible(selected_file)
        except Exception as exc:
            message = f"Couldn't read EMA CSV: {exc}"
            return blank_fig(message), blank_fig(message)

        file_type = detect_ema_file_type(selected_file)
        subject_column = find_subject_column(df.columns)

        if file_type in {"question_summary", "subject_summary"}:
            label_column, summary_df = get_summary_dimensions(df, file_type)
            metric_columns = get_numeric_columns(summary_df)

            if not label_column or not metric_columns:
                message = "EMA summary file is missing the expected label or numeric metric columns."
                return blank_fig(message), blank_fig(message)

            filtered_df = summary_df.copy()
            if x_axis_values:
                selected_labels = x_axis_values if isinstance(x_axis_values, list) else [x_axis_values]
                filtered_df = filtered_df[
                    filtered_df[label_column].astype(str).isin([str(item) for item in selected_labels])
                ]

            if file_type == "subject_summary" and subject_column and subject_ids:
                selected_subjects = subject_ids if isinstance(subject_ids, list) else [subject_ids]
                filtered_df = filtered_df[
                    filtered_df[subject_column].astype(str).isin([str(item) for item in selected_subjects])
                ]

            if filtered_df.empty:
                message = "No EMA summary data available for the selected filters."
                return blank_fig(message), blank_fig(message)

            metric_column = y_axis_column if y_axis_column in metric_columns else get_default_numeric_column(filtered_df)
            heatmap_title = "EMA Question Summary Heatmap" if file_type == "question_summary" else "EMA Subject Summary Heatmap"
            histogram_title = (
                f"EMA Question Summary Histogram: {metric_column}"
                if file_type == "question_summary"
                else f"EMA Subject Summary Histogram: {metric_column}"
            )

            return (
                build_summary_heatmap(filtered_df, label_column, metric_columns, heatmap_title),
                build_summary_histogram(filtered_df, metric_column, label_column, histogram_title),
            )

        if not x_axis_column or x_axis_column not in df.columns:
            response_label_column, response_df = build_response_question_label_column(df)
            if response_label_column:
                x_axis_column = response_label_column
                df = response_df
            else:
                message = "Select a valid X-axis variable."
                return blank_fig(message), blank_fig(message)
        else:
            response_label_column, response_df = build_response_question_label_column(df)
            if response_label_column and x_axis_column == response_label_column:
                df = response_df

        if not y_axis_column or y_axis_column not in df.columns:
            message = "Select a valid answer field."
            return blank_fig(message), blank_fig(message)

        filtered_df = df.copy()
        if subject_column and subject_ids:
            selected_subjects = subject_ids if isinstance(subject_ids, list) else [subject_ids]
            filtered_df = filtered_df[
                filtered_df[subject_column].astype(str).isin([str(item) for item in selected_subjects])
            ]

        if x_axis_values:
            selected_x_values = x_axis_values if isinstance(x_axis_values, list) else [x_axis_values]
            filtered_df = filtered_df[
                filtered_df[x_axis_column].astype(str).isin([str(item) for item in selected_x_values])
            ]

        if filtered_df.empty:
            message = "No EMA data available for the selected filters."
            return blank_fig(message), blank_fig(message)

        question_column = response_label_column if response_label_column in filtered_df.columns else x_axis_column
        if question_column not in filtered_df.columns:
            message = "No question labels available for EMA response heatmap."
            return blank_fig(message), blank_fig(message)

        count_column = "Answer_ID" if "Answer_ID" in filtered_df.columns else question_column

        if subject_column:
            heatmap_source = filtered_df.pivot_table(
                index=subject_column,
                columns=question_column,
                values=count_column,
                aggfunc="count",
                fill_value=0,
            ).sort_index()
        else:
            heatmap_source = filtered_df.pivot_table(
                columns=question_column,
                values=count_column,
                aggfunc="count",
                fill_value=0,
            )
            heatmap_source.index = ["All responses"]

        heatmap_source = heatmap_source.dropna(axis=1, how="all").fillna(0)
        if heatmap_source.empty:
            message = "No EMA heatmap data available after filtering."
            return blank_fig(message), blank_fig(message)

        heatmap_fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_source.values,
                x=[str(item) for item in heatmap_source.columns.tolist()],
                y=[str(item) for item in heatmap_source.index.tolist()],
                colorscale="Cividis",
                colorbar={"title": "Count"},
            )
        )
        heatmap_fig.update_layout(
            title="EMA Response Count Heatmap",
            margin=dict(l=20, r=20, t=50, b=20),
        )

        answer_distribution_df = filtered_df.copy()
        answer_distribution_df[y_axis_column] = answer_distribution_df[y_axis_column].astype(str).str.strip()
        answer_distribution_df = answer_distribution_df[
            answer_distribution_df[y_axis_column].notna()
            & (answer_distribution_df[y_axis_column] != "")
        ]
        if answer_distribution_df.empty:
            histogram_fig = blank_fig("No answer distribution data available for the selected field.")
        else:
            value_counts = (
                answer_distribution_df[y_axis_column]
                .value_counts()
                .reset_index()
            )
            value_counts.columns = [y_axis_column, "Count"]
            value_counts = value_counts.head(30)
            histogram_fig = px.bar(
                value_counts,
                x=y_axis_column,
                y="Count",
                title=f"EMA Answer Distribution: {y_axis_column}",
            )
        histogram_fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))

        return heatmap_fig, histogram_fig

