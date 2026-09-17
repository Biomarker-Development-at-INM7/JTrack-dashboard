"""
Dash application wiring for the analytics page.

This module defines the top-level Dash layout used inside Django, registers
the shared analytics callbacks, and provides the small orchestration callbacks
that:
- hydrate Dash stores from Django `initial_args`
- populate study and sensor selectors
- list available output CSV files for the selected study
- switch between the main and EMA layouts based on the chosen CSV filename
- render the secondary graph area for the selected analytics mode
"""

import requests
from dash import dcc,no_update
from dash import html, dash_table
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash
from dash import Input, Output, State 
from dash.exceptions import PreventUpdate
from urllib.parse import urlparse, parse_qs
import os, base64, io,json
import pandas as pd
import numpy as np
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from jdash.config import runtime_config as config
from jdash.config import constants as constants
from .layouts.main_layout import main_layout
from .layouts.ema_layout import ema_layout
from .callbacks.default_callbacks import default_callbacks
from .callbacks.ema_callbacks import register_ema_callbacks
from .callbacks.main_callbacks import main_callbacks

main_keywords = ['main', 'activity','phoneusage','location']


def read_csv_flexible(csv_path):
    """Read comma- or semicolon-delimited CSVs with a small fallback."""
    try:
        df = pd.read_csv(csv_path)
        if len(df.columns) == 1 and ";" in str(df.columns[0]):
            return pd.read_csv(csv_path, sep=";")
        return df
    except Exception:
        return pd.read_csv(csv_path, sep=";")

app = DjangoDash('janalytica',suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        # Row 1: Left controls (3) + Right data area (9)
        dbc.Row(
            [
                dbc.Col(
                    [
                        # Hidden: stores + boot logs
                        html.Div(
                            [
                                dcc.Store(id='study-store', data=None),
                                html.Div(id='output-div'),
                                html.Script(
                                    """
                                    window.addEventListener("DOMContentLoaded", function() {
                                        console.log("🔍 Dash page loaded.");
                                    });
                                    window.addEventListener("initialArgsReady", function(e) {
                                        console.log("🧠 initialArgsReady received:", e.detail);
                                    });
                                    """
                                ),
                            ],
                            style={'display': 'none'},
                        ),
                        
                        html.Div(
                            [
                                dcc.Store(id='sensor-store', data=None),
                                html.Div(id='sensor-output-div'),
                                html.Script(
                                    """
                                    window.addEventListener("DOMContentLoaded", function() {
                                        console.log("🔍 Dash page loaded.");
                                    });
                                    window.addEventListener("initialArgsReady", function(e) {
                                        console.log("🧠 initialArgsReady received:", e.detail);
                                    });
                                    """
                                ),
                            ],
                            style={'display': 'none'},
                        ),

                        # Study selector
                        html.Div(
                            [
                                dbc.Label("Choose Study", html_for="studies-dropdown", className="form-label"),
                                dcc.Dropdown(
                                    id='studies-dropdown',
                                    options=[],
                                    value=None,
                                    placeholder="Select study",
                                    persistence=True,
                                    persistence_type='session',
                                    clearable=True,
                                ),
                            ],
                            style={'margin-bottom': '20px'},
                        ),

                        # Dynamic controls container
                        html.Div(
                            [
                                dbc.Label("Select which sensor", html_for="sensor-dropdown", className="form-label"),
                                dcc.Dropdown(
                                    id='sensor-dropdown',
                                    options=[],          # populated after CSV is chosen
                                    value=None,
                                    placeholder="Select sensor ",
                                    persistence=True,
                                    persistence_type='session',
                                    clearable=True,
                                ),
                            ],
                            style={'margin-bottom': '20px'},
                        ),
                        html.Div(
                            [
                                dbc.Label("Choose X-axis", html_for="date-filter", className="form-label"),
                                dcc.Dropdown(
                                    id="date-filter",
                                    options=[],              # populated from CSV columns
                                    value=None,              # default chosen automatically
                                    multi=False,             # choose ONE of: Date or study_day
                                    persistence=True,
                                    persistence_type='session',
                                    placeholder="Select x-axis (Date or study_day)"
                                ),
                            ],
                            style={'margin-bottom': '20px'},
                        ),                      
                        
                        html.Div(
                            [
                                dbc.Label("Filter subjects", html_for="subject-filter", className="form-label"),
                                dcc.Dropdown(
                                    id="subject-filter",
                                    options=[],
                                    value=None,
                                    multi=True,
                                    placeholder="All subjects",
                                    persistence=True,
                                    persistence_type='session',
                                ),
                            ],),             
                    ],style={'background-color': '#f8f9fa'},
                    md=3, lg=3,
                ),

                dbc.Col(
                    [
                       html.Div(
                        [
                            dcc.Tabs(
                                id='data-view-tabs',
                                value='graph',
                                parent_style={
                                    'display': 'flex',
                                    'justifyContent': 'center',
                                    'marginBottom': '16px',
                                },
                                style={
                                    'display': 'inline-flex',
                                    'width': 'fit-content',
                                    'margin': '0 auto',
                                    'height': 'auto',
                                    'border': 'none',
                                    'backgroundColor': 'transparent',
                                },
                                children=[
                                    dcc.Tab(
                                        label='Graph',
                                        value='graph',
                                        style={
                                            'display': 'inline-flex',
                                            'flex': '0 0 auto',
                                            'width': 'auto',
                                            'alignItems': 'center',
                                            'justifyContent': 'center',
                                            'padding': '8px 18px',
                                            'borderRadius': '999px',
                                            'border': '1px solid #cfd6dd',
                                            'backgroundColor': '#ffffff',
                                            'fontWeight': '600',
                                            'marginRight': '10px',
                                        },
                                        selected_style={
                                            'display': 'inline-flex',
                                            'flex': '0 0 auto',
                                            'width': 'auto',
                                            'alignItems': 'center',
                                            'justifyContent': 'center',
                                            'padding': '8px 18px',
                                            'borderRadius': '999px',
                                            'border': '1px solid #0d6efd',
                                            'backgroundColor': '#0d6efd',
                                            'color': '#ffffff',
                                            'fontWeight': '600',
                                            'marginRight': '10px',
                                        },
                                        children=[
                                            dcc.Loading(
                                                dcc.Graph(id='data-plot'),
                                                type="graph",
                                                style={'backgroundColor': '#eaeaea'}
                                            )
                                        ],
                                    ),
                                    dcc.Tab(
                                        label='Table',
                                        value='table',
                                        style={
                                            'display': 'inline-flex',
                                            'flex': '0 0 auto',
                                            'width': 'auto',
                                            'alignItems': 'center',
                                            'justifyContent': 'center',
                                            'padding': '8px 18px',
                                            'borderRadius': '999px',
                                            'border': '1px solid #cfd6dd',
                                            'backgroundColor': '#ffffff',
                                            'fontWeight': '600',
                                        },
                                        selected_style={
                                            'display': 'inline-flex',
                                            'flex': '0 0 auto',
                                            'width': 'auto',
                                            'alignItems': 'center',
                                            'justifyContent': 'center',
                                            'padding': '8px 18px',
                                            'borderRadius': '999px',
                                            'border': '1px solid #0d6efd',
                                            'backgroundColor': '#0d6efd',
                                            'color': '#ffffff',
                                            'fontWeight': '600',
                                        },
                                        children=[
                                            dcc.Loading(
                                                dash_table.DataTable(
                                                    id='data-table',
                                                    columns=[],
                                                    data=[],
                                                    page_size=20,
                                                    sort_action='native',
                                                    filter_action='native',
                                                    style_table={'overflowX': 'auto'},
                                                    style_cell={
                                                        'textAlign': 'left',
                                                        'minWidth': '120px',
                                                        'maxWidth': '280px',
                                                        'whiteSpace': 'normal',
                                                    },
                                                ),
                                                type="graph",
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ]),
                    ],style={'background-color': '#f8f9fa'},
                    md=9, lg=9,
                ),
            ],
            className="g-3",
        ),
    ],
    fluid=True,
)

app.validation_layout = html.Div([
    app.layout,
    main_layout(),
    ema_layout()
])
default_callbacks(app)
main_callbacks(app)
register_ema_callbacks(app)

@app.callback(
    [
     Output('studies-dropdown', 'options'),
     Output('studies-dropdown', 'value'),
     Output('studies-dropdown', 'style')],
     Input('study-store', 'data')
)
def update_studies_tabs(studies):
    """
    Populate the study dropdown from the injected study list.

    Args:
        studies (list | None): List of study names available to the user.

    Returns:
        tuple: Dropdown options, selected value, and style override.
    """
    if not studies:
        return no_update, no_update, no_update

    studies_list = [{'label': i, 'value': i} for i in studies]
    return studies_list, studies_list[0]['value'], {}

@app.callback(
    [
     Output('sensor-dropdown', 'options'),
     Output('sensor-dropdown', 'value'),
     Output('sensor-dropdown', 'style')],
     Input('sensor-store', 'data'),
     Input('studies-dropdown', 'value'),          # <-- pick sensors for this study
)
def populate_sensor_dropdown(sensors_map, selected_study):
    """
    Populate the sensor dropdown for the selected study.

    Args:
        sensors_map (dict | None): Study-to-sensor mapping from `sensor-store`.
        selected_study (str | None): Currently selected study name.

    Returns:
        tuple: Sensor dropdown options, selected value, and style override.
    """
    if not sensors_map or not isinstance(sensors_map, dict):
        return no_update, no_update, no_update

    key = selected_study or ""
    sensors = sensors_map.get(key, [])
    if not sensors:
        return no_update, no_update, no_update

    sensor_list = [{'label': sensor, 'value': sensor} for sensor in sensors]
    return sensor_list, sensor_list[0]['value'], {}




#Callback to populate the dropdown with CSV files based on the selected value
@app.callback(
    Output('csv-options-store', 'data'),
    Input('studies-dropdown', 'value')
)
def update_selector(selected_value):
    """
    List analytics CSV output files for the selected study.

    Args:
        selected_value (str | None): Selected study name.

    Returns:
        list[str]: Absolute paths to CSV files in the study's outputs folder.
    """
    if not selected_value:
        return []

    data_dir = os.path.join(config.analytics_storage_folder, selected_value, "outputs")
    if not data_dir or not os.path.isdir(data_dir):
        return []

    csv_files = []
    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith('.csv'):
            continue

        filename_lower = filename.lower()
        if filename_lower.startswith('data_per_day_'):
            continue
        if filename_lower.startswith('jutrack_dashboard_'):
            continue

        csv_files.append(os.path.join(data_dir, filename))
    return csv_files
    


