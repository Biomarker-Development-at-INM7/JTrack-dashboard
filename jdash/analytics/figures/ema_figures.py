"""EMA-specific figure builders."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from django.utils.translation import gettext_lazy as _

from jdash.analytics.data.dashboard_data import (
    apply_filter,
    first_matching_column,
    normalize_column_name,
)

from .common_figures import (
    availability_threshold,
    blank_quality_figure,
    finish_quality_figure,
    timeline_x_column,
)


COMPLETION_COLORSCALE = [
    [0.0, "#e9ecef"],
    [0.009, "#e9ecef"],
    [0.01, "#c92a2a"],
    [0.019, "#c92a2a"],
    [0.02, "#f59f00"],
    [0.99, "#f59f00"],
    [1.0, "#00796b"],
]

EMA_RESPONSE_COUNT_COLUMNS = [
    "Anytime_questions_answered",
    "Optional_questions_answered",
    "Total_questions_answered",
    "Submissions_count",
    "Total_submissions",
]


def ema_response_count_column(columns):
    return first_matching_column(columns, EMA_RESPONSE_COUNT_COLUMNS)


def finish_ema_figure(fig):
    fig.update_layout(
        title=None,
        template="simple_white",
        margin=dict(l=24, r=24, t=24, b=58),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def blank_ema_figure(title, message="No EMA data available."):
    fig = go.Figure()
    fig.add_annotation(
        text=str(message),
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#6c757d"},
    )
    fig.update_layout(
        title=None,
        template="simple_white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def ema_timeline_x_column(df, preferred_axis=None):
    if preferred_axis == "date":
        return (
            first_matching_column(df.columns, ["Date", "date"])
            or first_matching_column(df.columns, ["Study_day", "study_day"])
        )
    return (
        first_matching_column(df.columns, ["Study_day", "study_day"])
        or first_matching_column(df.columns, ["Date", "date"])
    )


def completion_hover_values(matrix):
    return matrix.apply(
        lambda column: column.map(
            lambda value: _("Not expected") if pd.isna(value) else f"{float(value):.1f}%"
        )
    )


def build_ema_completion_matrix_figure(df, subjects=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    if not subject_col:
        return blank_ema_figure(title or _("EMA Completion Matrix"), _("Completion matrix is missing Subject_ID."))

    matrix_df = apply_filter(df.copy(), subject_col, subjects)
    if matrix_df.empty:
        return blank_ema_figure(title or _("EMA Completion Matrix"))

    window_cols = [column for column in matrix_df.columns if column != subject_col]
    if not window_cols:
        return blank_ema_figure(title or _("EMA Completion Matrix"), _("Completion matrix has no window columns."))

    matrix_df[subject_col] = matrix_df[subject_col].astype(str)
    matrix = matrix_df.set_index(subject_col)[window_cols].apply(pd.to_numeric, errors="coerce")
    z_values = matrix.fillna(-1)
    customdata = completion_hover_values(matrix).to_numpy()

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values.to_numpy(),
            x=list(matrix.columns),
            y=list(matrix.index),
            zmin=-1,
            zmax=100,
            colorscale=COMPLETION_COLORSCALE,
            customdata=customdata,
            colorbar=dict(title=dict(text=str(_("Completion %"))), thickness=14, len=0.78),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Window: %{x}<br>"
                "Completion: %{customdata}<extra></extra>"
            ),
            xgap=1,
            ygap=1,
        )
    )
    fig = finish_ema_figure(fig)
    fig.update_layout(height=max(360, min(820, 24 * len(matrix.index) + 150)))
    fig.update_xaxes(title=str(_("Frequency window")), tickangle=-35)
    fig.update_yaxes(title=None)
    return fig


def build_ema_frequency_window_detail_figure(df, subjects=None, timeline_axis=None, title=None, frequencies=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    completion_col = first_matching_column(df.columns, ["Question_completion_percent", "Completion_percent"])
    required = ["Frequency", "Window_index", "Expected_questions", "Answered_questions", "Missed_questions"]
    if not subject_col or not completion_col or any(column not in df.columns for column in required):
        return blank_ema_figure(
            title or _("EMA Frequency Window Detail"),
            _("Frequency window file is missing required completion columns."),
        )

    detail_df = apply_filter(df.copy(), subject_col, subjects)
    detail_df = apply_filter(detail_df, "Frequency", frequencies)
    if detail_df.empty:
        return blank_ema_figure(title or _("EMA Frequency Window Detail"))

    detail_df[subject_col] = detail_df[subject_col].astype(str)
    detail_df["Question_completion_percent"] = pd.to_numeric(detail_df[completion_col], errors="coerce")
    detail_df["Window_label"] = (
        "F"
        + detail_df["Frequency"].astype(str)
        + " W"
        + detail_df["Window_index"].astype(str)
    )
    sort_cols = ["Frequency", "Window_index"]
    detail_df = detail_df.sort_values(sort_cols)
    window_order = detail_df["Window_label"].drop_duplicates().tolist()

    heatmap = detail_df.pivot_table(
        index=subject_col,
        columns="Window_label",
        values="Question_completion_percent",
        aggfunc="mean",
    ).reindex(columns=window_order)

    metadata_cols = [
        "Expected_questions",
        "Answered_questions",
        "Missed_questions",
        "Compliance_state",
        "Window_start_date",
        "Window_end_date",
    ]
    metadata_arrays = []
    for column in metadata_cols:
        if column in detail_df.columns:
            metadata = detail_df.pivot_table(
                index=subject_col,
                columns="Window_label",
                values=column,
                aggfunc="first",
            ).reindex(index=heatmap.index, columns=heatmap.columns)
        else:
            metadata = pd.DataFrame("", index=heatmap.index, columns=heatmap.columns)
        metadata_arrays.append(metadata.fillna("").to_numpy())

    customdata = np.dstack(metadata_arrays)
    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap.fillna(-1).to_numpy(),
            x=list(heatmap.columns),
            y=list(heatmap.index),
            zmin=-1,
            zmax=100,
            colorscale=COMPLETION_COLORSCALE,
            customdata=customdata,
            colorbar=dict(title=dict(text=str(_("Completion %"))), thickness=14, len=0.78),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Window: %{x}<br>"
                "Completion: %{z:.1f}%<br>"
                "Expected: %{customdata[0]}<br>"
                "Answered: %{customdata[1]}<br>"
                "Missed: %{customdata[2]}<br>"
                "State: %{customdata[3]}<br>"
                "Start: %{customdata[4]}<br>"
                "End: %{customdata[5]}<extra></extra>"
            ),
            xgap=1,
            ygap=1,
        )
    )
    fig = finish_ema_figure(fig)
    fig.update_layout(height=max(360, min(820, 24 * len(heatmap.index) + 150)))
    fig.update_xaxes(title=str(_("Frequency window")), tickangle=-35)
    fig.update_yaxes(title=None)
    return fig


def build_ema_risk_ranking_figure(df, subjects=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    completion_col = first_matching_column(df.columns, ["Question_completion_percent", "Completion_percent"])
    if not subject_col or not completion_col:
        return blank_ema_figure(
            title or _("EMA Subject Risk Ranking"),
            _("Missingness summary is missing subject or completion percent columns."),
        )

    risk_df = apply_filter(df.copy(), subject_col, subjects)
    if risk_df.empty:
        return blank_ema_figure(title or _("EMA Subject Risk Ranking"))

    risk_df[subject_col] = risk_df[subject_col].astype(str)
    risk_df["Question_completion_percent"] = pd.to_numeric(risk_df[completion_col], errors="coerce").fillna(0)
    for column in ("Expected_questions_total", "Answered_questions_total", "Missed_questions_total"):
        if column in risk_df.columns:
            risk_df[column] = pd.to_numeric(risk_df[column], errors="coerce").fillna(0)
        else:
            risk_df[column] = 0
    risk_df = risk_df.sort_values("Question_completion_percent", ascending=True)

    fig = px.bar(
        risk_df,
        x=subject_col,
        y="Question_completion_percent",
        color="Question_completion_percent",
        range_color=[0, 100],
        color_continuous_scale=[
            [0.0, "#c92a2a"],
            [0.65, "#f59f00"],
            [1.0, "#00796b"],
        ],
        text=risk_df["Question_completion_percent"].map(lambda value: f"{value:.1f}%"),
        labels={
            subject_col: str(_("Subject")),
            "Question_completion_percent": str(_("Question completion %")),
        },
        custom_data=["Expected_questions_total", "Answered_questions_total", "Missed_questions_total"],
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Completion: %{y:.1f}%<br>"
            "Expected questions: %{customdata[0]:,.0f}<br>"
            "Answered questions: %{customdata[1]:,.0f}<br>"
            "Missed questions: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig = finish_ema_figure(fig)
    fig.update_layout(
        height=420,
        coloraxis_showscale=False,
        margin=dict(l=48, r=24, t=24, b=90),
    )
    fig.update_xaxes(title=None, tickangle=-45)
    fig.update_yaxes(title=str(_("Question completion %")), range=[0, 105], ticksuffix="%")
    return fig


def aggregate_ema_daily_response_volume(df, subjects=None, timeline_axis=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    if not subject_col:
        return df

    x_col = ema_timeline_x_column(df, timeline_axis)
    scheduled_col = first_matching_column(df.columns, ["Scheduled_questions_answered"])
    response_col = ema_response_count_column(df.columns)
    total_questions_col = first_matching_column(df.columns, ["Total_questions_answered"])
    total_submissions_col = first_matching_column(df.columns, ["Total_submissions"])
    if not x_col or not response_col:
        return df

    timeline_df = apply_filter(df.copy(), subject_col, subjects)
    if timeline_df.empty:
        return timeline_df

    if not scheduled_col:
        timeline_df["Scheduled_questions_answered"] = 0
        scheduled_col = "Scheduled_questions_answered"

    for column in [scheduled_col, response_col, total_questions_col, total_submissions_col]:
        if column and column in timeline_df.columns:
            timeline_df[column] = pd.to_numeric(timeline_df[column], errors="coerce").fillna(0)
    if normalize_column_name(x_col) == "study_day":
        timeline_df[x_col] = pd.to_numeric(timeline_df[x_col], errors="coerce")
    timeline_df = timeline_df.dropna(subset=[x_col])
    if timeline_df.empty:
        return timeline_df

    if not total_questions_col:
        timeline_df["Total_questions_answered"] = timeline_df[scheduled_col] + timeline_df[response_col]
        total_questions_col = "Total_questions_answered"
    if not total_submissions_col:
        timeline_df["Total_submissions"] = 0
        total_submissions_col = "Total_submissions"

    grouped = timeline_df.groupby(x_col, as_index=False).agg(
        {
            scheduled_col: "sum",
            response_col: "sum",
            total_questions_col: "sum",
            total_submissions_col: "sum",
        }
    )
    subjects_with_answers = (
        timeline_df[timeline_df[total_questions_col] > 0]
        .groupby(x_col)[subject_col]
        .nunique()
        .rename("Subjects_with_any_answer")
        .reset_index()
    )
    grouped = grouped.merge(subjects_with_answers, on=x_col, how="left")
    grouped["Subjects_with_any_answer"] = grouped["Subjects_with_any_answer"].fillna(0)
    return grouped


def build_ema_daily_response_volume_figure(df, subjects=None, timeline_axis=None, title=None):
    df = aggregate_ema_daily_response_volume(df, subjects, timeline_axis)
    x_col = ema_timeline_x_column(df, timeline_axis)
    if not x_col:
        return blank_ema_figure(title or _("EMA Daily Response Volume"), _("Daily volume file is missing Study_day or Date."))

    scheduled_col = first_matching_column(df.columns, ["Scheduled_questions_answered"])
    response_col = ema_response_count_column(df.columns)
    subjects_col = first_matching_column(df.columns, ["Subjects_with_any_answer"])
    total_questions_col = first_matching_column(df.columns, ["Total_questions_answered"])
    total_submissions_col = first_matching_column(df.columns, ["Total_submissions"])
    if not response_col:
        return blank_ema_figure(
            title or _("EMA Daily Response Volume"),
            _("Daily volume file is missing expected answer columns."),
        )

    volume_df = df.copy()
    if not scheduled_col:
        volume_df["Scheduled_questions_answered"] = 0
        scheduled_col = "Scheduled_questions_answered"
    for column in [scheduled_col, response_col, subjects_col, total_questions_col, total_submissions_col]:
        if column and column in volume_df.columns:
            volume_df[column] = pd.to_numeric(volume_df[column], errors="coerce").fillna(0)
    if not total_questions_col:
        volume_df["Total_questions_answered"] = volume_df[scheduled_col] + volume_df[response_col]
        total_questions_col = "Total_questions_answered"
    if normalize_column_name(x_col) == "study_day":
        volume_df[x_col] = pd.to_numeric(volume_df[x_col], errors="coerce")
    volume_df = volume_df.dropna(subset=[x_col]).sort_values(x_col)
    custom_cols = [
        total_questions_col or scheduled_col,
        total_submissions_col or scheduled_col,
        subjects_col or scheduled_col,
    ]
    response_activity_only = volume_df[scheduled_col].sum() == 0 and volume_df[response_col].sum() > 0

    fig = go.Figure()
    if not response_activity_only:
        fig.add_trace(
            go.Bar(
                x=volume_df[x_col],
                y=volume_df[scheduled_col],
                name=str(_("Scheduled questions answered")),
                marker_color="#00796b",
                customdata=volume_df[custom_cols].to_numpy(),
                hovertemplate=(
                    f"{x_col}: %{{x}}<br>"
                    "Scheduled questions: %{y:,.0f}<br>"
                    "Total questions: %{customdata[0]:,.0f}<br>"
                    "Total submissions: %{customdata[1]:,.0f}<extra></extra>"
                ),
            )
        )
    fig.add_trace(
        go.Bar(
            x=volume_df[x_col],
            y=volume_df[response_col],
            name=str(_("Questions answered") if response_activity_only else _("Additional responses answered")),
            marker_color="#71c7bd",
            customdata=volume_df[custom_cols].to_numpy(),
            hovertemplate=(
                f"{x_col}: %{{x}}<br>"
                "Questions answered: %{y:,.0f}<br>"
                "Total questions: %{customdata[0]:,.0f}<br>"
                "Total submissions: %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    if subjects_col:
        fig.add_trace(
            go.Scatter(
                x=volume_df[x_col],
                y=volume_df[subjects_col],
                name=str(_("Subjects with any answer")),
                mode="lines+markers",
                yaxis="y2",
                line={"color": "#212529", "width": 2.5},
                marker={"size": 6},
                hovertemplate=(
                    f"{x_col}: %{{x}}<br>"
                    "Subjects with any answer: %{y:,.0f}<extra></extra>"
                ),
            )
        )

    fig = finish_ema_figure(fig)
    fig.update_layout(
        height=420,
        barmode="stack",
        hovermode="x unified",
        yaxis2=dict(
            title=str(_("Subjects")),
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
        ),
    )
    fig.update_xaxes(title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)))
    fig.update_yaxes(
        title=str(_("Questions answered")),
        rangemode="tozero",
    )
    return fig


def build_ema_subject_timeline_figure(df, subjects=None, timeline_axis=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    x_col = ema_timeline_x_column(df, timeline_axis)
    study_day_col = first_matching_column(df.columns, ["Study_day", "study_day"])
    date_col = first_matching_column(df.columns, ["Date", "date"])
    scheduled_col = first_matching_column(df.columns, ["Scheduled_questions_answered"])
    response_col = ema_response_count_column(df.columns)
    total_col = first_matching_column(df.columns, ["Total_questions_answered"])
    submissions_col = first_matching_column(df.columns, ["Total_submissions"])
    if not subject_col or not x_col or not (total_col or response_col or submissions_col):
        return blank_ema_figure(title or _("Subject EMA Timeline"), _("Timeline file is missing subject, day, or answer columns."))

    timeline_df = apply_filter(df.copy(), subject_col, subjects)
    if timeline_df.empty:
        return blank_ema_figure(title or _("Subject EMA Timeline"))

    timeline_df[subject_col] = timeline_df[subject_col].astype(str)
    if not scheduled_col:
        timeline_df["Scheduled_questions_answered"] = 0
        scheduled_col = "Scheduled_questions_answered"
    if not response_col:
        timeline_df["Questions_answered"] = timeline_df[total_col] if total_col else timeline_df[submissions_col]
        response_col = "Questions_answered"
    if not total_col:
        timeline_df["Total_questions_answered"] = timeline_df[response_col]
        total_col = "Total_questions_answered"

    for column in [scheduled_col, response_col, total_col, submissions_col]:
        if column and column in timeline_df.columns:
            timeline_df[column] = pd.to_numeric(timeline_df[column], errors="coerce").fillna(0)
    if normalize_column_name(x_col) == "study_day":
        timeline_df[x_col] = pd.to_numeric(timeline_df[x_col], errors="coerce")
    timeline_df = timeline_df.dropna(subset=[x_col])
    timeline_df = timeline_df[timeline_df[total_col] > 0]
    if timeline_df.empty:
        return blank_ema_figure(title or _("Subject EMA Timeline"))

    scheduled_values = timeline_df[scheduled_col] if scheduled_col else 0
    response_values = timeline_df[response_col] if response_col else 0
    timeline_df["Answer_type"] = np.select(
        [
            (scheduled_values > 0) & (response_values > 0),
            scheduled_values > 0,
            response_values > 0,
        ],
        [str(_("scheduled + response")), str(_("scheduled only")), str(_("response only"))],
        default=str(_("answered")),
    )

    response_activity_only = (
        bool(scheduled_col)
        and bool(response_col)
        and timeline_df[scheduled_col].sum() == 0
        and timeline_df[response_col].sum() > 0
    )
    size_col = response_col if response_activity_only and response_col else total_col
    color_col = response_col if response_activity_only and response_col else "Answer_type"
    color_args = {
        "color_continuous_scale": [
            [0.0, "#d9f0ed"],
            [0.7, "#2a9d8f"],
            [1.0, "#006d5b"],
        ],
    } if response_activity_only else {
        "color_discrete_map": {
            str(_("scheduled + response")): "#00796b",
            str(_("scheduled only")): "#2f80ed",
            str(_("response only")): "#f59f00",
            str(_("answered")): "#6c757d",
        },
    }

    if not submissions_col:
        timeline_df["Total_submissions"] = 0
        submissions_col = "Total_submissions"
    if not date_col:
        timeline_df["Date"] = ""
        date_col = "Date"
    if not study_day_col:
        timeline_df["Study_day"] = timeline_df[x_col]
        study_day_col = "Study_day"
    custom_cols = [date_col, study_day_col, response_col, total_col, submissions_col]
    fig = px.scatter(
        timeline_df,
        x=x_col,
        y=subject_col,
        size=size_col,
        color=color_col,
        labels={
            x_col: str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            subject_col: str(_("Subject")),
            size_col: str(_("Questions answered") if response_activity_only else _("Total questions answered")),
            "Answer_type": str(_("Answer type")),
        },
        custom_data=custom_cols,
        **color_args,
    )
    fig.update_traces(
        marker={"sizemin": 5, "line": {"width": 1, "color": "#ffffff"}},
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Date: %{customdata[0]}<br>"
            "Study_day: %{customdata[1]}<br>"
            "Questions answered: %{customdata[2]:,.0f}<br>"
            "Total questions: %{customdata[3]:,.0f}<br>"
            "Total submissions: %{customdata[4]:,.0f}<extra></extra>"
        ),
    )
    fig = finish_ema_figure(fig)
    fig.update_layout(height=max(380, min(820, 24 * timeline_df[subject_col].nunique() + 160)))
    fig.update_xaxes(title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)))
    fig.update_yaxes(title=None)
    return fig


def build_ema_anytime_question_status_figure(df, subjects=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    question_col = first_matching_column(df.columns, ["Question_ID", "question_id", "question"])
    answer_days_col = first_matching_column(df.columns, ["Answer_days", "Days_with_answer", "Response_days"])
    status_col = first_matching_column(df.columns, ["Answer_status", "Status", "Response_status"])
    if not subject_col or not question_col:
        return blank_ema_figure(
            title or _("EMA Question Response Status"),
            _("Question status file is missing subject or question columns."),
        )

    status_df = apply_filter(df.copy(), subject_col, subjects)
    if status_df.empty:
        return blank_ema_figure(title or _("EMA Question Response Status"))

    status_df[subject_col] = status_df[subject_col].astype(str)
    status_df[question_col] = status_df[question_col].astype(str)
    if answer_days_col:
        status_df["Answer_days_value"] = pd.to_numeric(status_df[answer_days_col], errors="coerce").fillna(0)
    elif status_col:
        status_df["Answer_days_value"] = np.where(
            status_df[status_col].astype(str).str.casefold().eq("answered"),
            1,
            0,
        )
    else:
        return blank_ema_figure(
            title or _("EMA Question Response Status"),
            _("Question status file is missing answer-day or status columns."),
        )

    status_df = status_df.sort_values([subject_col, question_col])
    heatmap = status_df.pivot_table(
        index=subject_col,
        columns=question_col,
        values="Answer_days_value",
        aggfunc="max",
        fill_value=0,
    )
    if heatmap.empty:
        return blank_ema_figure(title or _("EMA Question Response Status"))

    def metadata_matrix(column):
        if column in status_df.columns:
            return status_df.pivot_table(
                index=subject_col,
                columns=question_col,
                values=column,
                aggfunc="first",
            ).reindex(index=heatmap.index, columns=heatmap.columns).fillna("")
        return pd.DataFrame("", index=heatmap.index, columns=heatmap.columns)

    metadata_cols = [
        status_col,
        "First_answer_day",
        "First_answer_date",
        "Last_answer_day",
        "Last_answer_date",
        "Total_submissions",
    ]
    metadata_arrays = [metadata_matrix(column).to_numpy() for column in metadata_cols]
    customdata = np.dstack(metadata_arrays)

    max_value = pd.to_numeric(heatmap.stack(), errors="coerce").max()
    zmax = 1 if pd.isna(max_value) or max_value <= 0 else max_value
    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap.to_numpy(),
            x=list(heatmap.columns),
            y=list(heatmap.index),
            zmin=0,
            zmax=zmax,
            colorscale=[
                [0.0, "#e9ecef"],
                [0.0001, "#e9ecef"],
                [0.35, "#d9f0ed"],
                [0.7, "#71c7bd"],
                [1.0, "#00796b"],
            ],
            customdata=customdata,
            colorbar=dict(title=dict(text=str(_("Answer days"))), thickness=14, len=0.78),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Question: %{x}<br>"
                "Answer days: %{z:,.0f}<br>"
                "Status: %{customdata[0]}<br>"
                "First answer day: %{customdata[1]}<br>"
                "First answer date: %{customdata[2]}<br>"
                "Last answer day: %{customdata[3]}<br>"
                "Last answer date: %{customdata[4]}<br>"
                "Total submissions: %{customdata[5]}<extra></extra>"
            ),
            xgap=1,
            ygap=1,
        )
    )
    fig = finish_ema_figure(fig)
    fig.update_layout(height=max(380, min(840, 24 * len(heatmap.index) + 160)))
    fig.update_xaxes(title=str(_("Question")), tickangle=-35)
    fig.update_yaxes(title=None)
    return fig


def build_ema_missingness_figure(df, subjects=None, timeline_axis=None, title=None):
    subject_col = first_matching_column(df.columns, ["Subject_ID", "subject_id", "subject"])
    response_col = first_matching_column(
        df.columns,
        [
            "Question_completion_percent",
            "question_completion_percent",
            "Completion_percent",
            "completion_percent",
            "Response_rate_percent",
            "response_rate_percent",
            "Response_percent",
            "Availability_percent",
            "Adherence_percent",
        ],
    )
    if not subject_col:
        return blank_quality_figure(
            title or _("EMA Response Rate"),
            _("EMA missingness summary is missing a subject column."),
        )
    if not response_col:
        return blank_quality_figure(
            title or _("EMA Response Rate"),
            _("EMA missingness summary is missing completion, response, or availability percent columns."),
        )

    response_df = df.copy()
    response_df["Response_rate_percent"] = pd.to_numeric(response_df[response_col], errors="coerce")
    response_df[subject_col] = response_df[subject_col].astype(str)
    response_df["Response_rate_percent"] = (
        pd.to_numeric(response_df["Response_rate_percent"], errors="coerce")
        .clip(lower=0, upper=100)
    )
    response_df = response_df.dropna(subset=["Response_rate_percent"])
    response_df = apply_filter(response_df, subject_col, subjects)
    if response_df.empty:
        return blank_quality_figure(title or _("EMA Response Rate"))

    metric_label = (
        _("Question completion %")
        if "question_completion" in normalize_column_name(response_col)
        else _("Response rate %")
    )
    x_col = timeline_x_column(response_df, timeline_axis)
    if normalize_column_name(x_col) == "study_day":
        response_df[x_col] = pd.to_numeric(response_df[x_col], errors="coerce")

    if x_col and subjects:
        heatmap = response_df.pivot_table(
            index=subject_col,
            columns=x_col,
            values="Response_rate_percent",
            aggfunc="mean",
            fill_value=0,
        )
        if heatmap.empty:
            return blank_quality_figure(title or _("EMA Response Rate"))

        heatmap = heatmap.loc[sorted(heatmap.index)]
        heatmap = heatmap.reindex(sorted(heatmap.columns), axis=1)
        fig = px.imshow(
            heatmap,
            aspect="auto",
            range_color=[0, 100],
            color_continuous_scale=[
                [0.0, "#e9ecef"],
                [0.35, "#d9f0ed"],
                [0.7, "#71c7bd"],
                [1.0, "#00796b"],
            ],
            labels={
                "x": str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
                "y": str(_("Subject")),
                "color": str(metric_label),
            },
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{x_col}: %{{x}}<br>"
                f"{metric_label}: %{{z:.1f}}%<extra></extra>"
            ),
            xgap=1,
            ygap=1,
            colorbar=dict(title=dict(text=str(metric_label)), thickness=14, len=0.78),
        )
        fig = finish_quality_figure(fig)
        fig.update_layout(
            height=max(340, min(780, 24 * len(heatmap.index) + 130)),
            margin=dict(l=24, r=24, t=10, b=58),
        )
        fig.update_xaxes(
            title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
            nticks=12,
        )
        fig.update_yaxes(title=None)
        return fig

    if not x_col:
        subject_summary = (
            response_df
            .groupby(subject_col, as_index=False)["Response_rate_percent"]
            .mean()
            .sort_values("Response_rate_percent", ascending=True)
        )
        if subject_summary.empty:
            return blank_quality_figure(title or _("EMA Response Rate"))

        threshold = availability_threshold(response_df)
        observed_max = pd.to_numeric(
            subject_summary["Response_rate_percent"],
            errors="coerce",
        ).max()
        if pd.isna(observed_max):
            observed_max = 0
        threshold_is_far = observed_max < (threshold * 0.5)
        if threshold_is_far:
            x_axis_max = min(100, max(30, float(np.ceil((observed_max + 5) / 5) * 5)))
        else:
            x_axis_max = min(100, max(30, float(np.ceil((max(observed_max, threshold) + 5) / 5) * 5)))

        fig = px.bar(
            subject_summary,
            x="Response_rate_percent",
            y=subject_col,
            orientation="h",
            range_x=[0, x_axis_max],
            text=subject_summary["Response_rate_percent"].map(lambda value: f"{value:.1f}%"),
            labels={
                "Response_rate_percent": str(metric_label),
                subject_col: str(_("Subject")),
            },
        )
        fig.update_traces(
            marker_color="#00796b",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{metric_label}: %{{x:.1f}}%<extra></extra>"
            ),
        )
        if threshold <= x_axis_max:
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color="#212529",
                line_width=1.5,
                annotation_text=f"{threshold:g}% {str(_('threshold'))}",
                annotation_position="top right",
            )
        else:
            fig.add_annotation(
                x=1,
                y=1.1,
                xref="paper",
                yref="paper",
                text=f"{threshold:g}% {str(_('threshold'))} - {str(_('no participants reach this'))}",
                showarrow=False,
                xanchor="right",
                align="right",
                font={"size": 12, "color": "#495057"},
            )
        fig = finish_quality_figure(fig)
        fig.update_layout(
            height=max(340, min(780, 24 * len(subject_summary) + 130)),
            margin=dict(l=24, r=36, t=54, b=54),
            showlegend=False,
        )
        fig.update_xaxes(title=str(metric_label), ticksuffix="%", range=[0, x_axis_max])
        fig.update_yaxes(title=None)
        return fig

    response_df = response_df.dropna(subset=[x_col])
    if response_df.empty:
        return blank_quality_figure(title or _("EMA Response Rate"))

    summary = (
        response_df
        .groupby(x_col, as_index=False)["Response_rate_percent"]
        .mean()
        .sort_values(x_col)
    )
    if summary.empty:
        return blank_quality_figure(title or _("EMA Response Rate"))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=summary[x_col],
            y=summary["Response_rate_percent"],
            mode="lines",
            fill="tozeroy",
            line={"color": "#00796b", "width": 2.5},
            fillcolor="rgba(0, 121, 107, 0.18)",
            hovertemplate=(
                f"{x_col}: %{{x}}<br>"
                f"{metric_label}: %{{y:.1f}}%<extra></extra>"
            ),
            name=str(metric_label),
        )
    )
    fig = finish_quality_figure(fig)
    fig.update_layout(
        height=420,
        hovermode="x unified",
        margin=dict(l=48, r=24, t=24, b=58),
        showlegend=False,
    )
    fig.update_xaxes(
        title=str(_("Study day") if normalize_column_name(x_col) == "study_day" else _(x_col)),
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
        nticks=12,
    )
    fig.update_yaxes(
        title=str(metric_label),
        range=[0, 100],
        ticksuffix="%",
        showgrid=True,
        gridcolor="#eef2f5",
        zeroline=False,
    )
    return fig
