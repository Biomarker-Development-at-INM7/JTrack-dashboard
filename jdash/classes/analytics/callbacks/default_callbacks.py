import os
import pandas as pd
import plotly.express as px
from dash import Input, Output
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

BASE_DIR = "/mnt/jutrack_data/studies_bids/"   # single fixed location
SUBJECT_CANDIDATES = [
    "subject", "Subject_ID"
]
X_AXIS_CANDIDATES = [ "Study_day","Date"]  # order = preference
def default_callbacks(app):
    
    @app.callback(
        Output("date-filter", "options"),
        Output("date-filter", "value"),
        Input("studies-dropdown", "value"),
        Input("sensor-dropdown", "value"),
        prevent_initial_call=True
    )
    def populate_date_filter(study, sensor):
        if not (study and sensor):
            raise PreventUpdate

        path = os.path.join(BASE_DIR, study, f"Data_per_day_{sensor}_latest.csv")
        if not os.path.exists(path):
            return [], None

        try:
            df = pd.read_csv(path, sep=";")
        except Exception:
            return [], None

        available = [c for c in X_AXIS_CANDIDATES if c in df.columns]
        options = [{"label": c, "value": c} for c in available]
        default = next((c for c in X_AXIS_CANDIDATES if c in available), None)  # prefer "Date"
        return options, default
    
    @app.callback(
    [Output("subject-filter", "options"),
     Output("subject-filter", "value")],     # keep None => show all by default
    [Input("studies-dropdown", "value"),
     Input("sensor-dropdown", "value")],
    prevent_initial_call=True
    )
    def populate_subject_filter(study, sensor):
        if not (study and sensor):
            raise PreventUpdate

        path = os.path.join(BASE_DIR, study, f"Data_per_day_{sensor}_latest.csv")
        if not os.path.exists(path):
            return [], None

        try:
            df = pd.read_csv(path, sep=";")
        except Exception:
            return [], None

        subj_col = next((c for c in SUBJECT_CANDIDATES if c in df.columns), None)
        if subj_col is None:
            return [], None

        subjects = sorted(map(str, df[subj_col].dropna().unique()))
        options = [{"label": s, "value": s} for s in subjects]

        # Default: show all (no filtering). If you prefer to preselect all:
        # return options, subjects
        return options, None

    @app.callback(
    Output('data-plot', 'figure'),
    Input('studies-dropdown', 'value'),
    Input('sensor-dropdown', 'value'),
    Input('date-filter', 'value'),      # "Date" or "Study_day"
    Input('subject-filter', 'value'),   # single or list
    )
    def update_heat_map(study, sensor, date_filter, subject_filter):
        if not (study and sensor):
            raise PreventUpdate

        
        def blank_fig(title_text: str):
            fig = go.Figure(
                go.Heatmap(
                    z=[[None]],        # single empty cell
                    showscale=False,
                    hoverinfo="skip",
                )
            )
            fig.update_xaxes(visible=False, fixedrange=True)
            fig.update_yaxes(visible=False, fixedrange=True)
            fig.update_layout(
                title=title_text,
                paper_bgcolor="#f8f9fa",
                plot_bgcolor="#f8f9fa",
                margin=dict(l=0, r=0, t=60, b=0),
            )
            return fig
        path = os.path.join(BASE_DIR, study, f"Data_per_day_{sensor}_latest.csv")
        if not os.path.exists(path):
            blank_fig(f"File not found: Contact the administrator") 

        try:
            df = pd.read_csv(path, sep=';')
        except Exception as e:
            return blank_fig(f"File not found: Contact the administrator") 

        DT_COL, VAL_COL = "Date", "Data_per_day"

        subj_col = next((c for c in SUBJECT_CANDIDATES if c in df.columns), None)
        missing = [c for c in (VAL_COL,) if c not in df.columns]
        if subj_col is None:
            missing.append("subject column (e.g., 'subject' or 'participant_id')")
        if missing:
            return blank_fig(f"File not found: Contact the administrator") 

        # Decide x-axis with candidates (keep order preference)
        if not date_filter:
            date_filter = next((c for c in X_AXIS_CANDIDATES if c in df.columns), None)

        df = df.copy()
        df[subj_col] = df[subj_col].astype(str)

        # Apply subject filter
        if subject_filter:
            selected = subject_filter if isinstance(subject_filter, list) else [subject_filter]
            df = df[df[subj_col].isin([str(v) for v in selected])]

        if date_filter == "Date":
            # Parse to datetime
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            # --- MONTHLY BINNING ---
            df["x_key"] = df["Date"].dt.to_period("M").dt.to_timestamp()  # month start
            x_is_date = True
        elif date_filter == "Study_day":
            # numeric if possible
            df["Study_day"] = pd.to_numeric(df["Study_day"], errors="coerce")
            df = df.dropna(subset=["Study_day"])
            df["x_key"] = df["Study_day"]
            x_is_date = False
        else:
            raise PreventUpdate

        # Pivot: subjects (rows) × x (cols), SUM (daily rows collapse to monthly totals)
        pivot = df.pivot_table(
            index=subj_col,
            columns="x_key",
            values=VAL_COL,
            aggfunc="sum",
            fill_value=0
        ).sort_index()

        # Ensure chronological x order
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)

        # Labels for imshow
        if x_is_date:
            # columns are month-start Timestamps (from .dt.to_period("M").dt.to_timestamp())
            import calendar
            x_vals = [f"{calendar.month_abbr[c.month]} {c.year}" for c in pivot.columns]  # e.g., "Jan 2022"
        else:
            x_vals = [int(c) if float(c).is_integer() else float(c) for c in pivot.columns]


        y_vals = list(pivot.index)
        z = pivot.values
        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=x_vals,
                y=y_vals,
                colorscale="Viridis",
                colorbar=dict(title=VAL_COL),
                hovertemplate=f"Subject: %{{y}}<br>{date_filter}: %{{x}}<br>{VAL_COL}: %{{z}}<extra></extra>",
            )    
        )
        fig.update_layout(
            title=f"{sensor} — {VAL_COL} by Subject vs {('Month' if x_is_date else 'Study_day')}",
            xaxis=dict(title=("Month" if x_is_date else "Study_day"), tickangle=-45, type="category"),
            yaxis=dict(title="Subject"),
            paper_bgcolor="#f8f9fa",
            plot_bgcolor="#f8f9fa",
            margin=dict(l=40, r=10, t=60, b=40),
        )
        return fig


