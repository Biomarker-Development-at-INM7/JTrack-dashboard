import requests
from dash import dcc,no_update
from dash import html
import plotly.graph_objs as go
from django_plotly_dash import DjangoDash
from dash import Input, Output, State 
from dash.exceptions import PreventUpdate
from urllib.parse import urlparse, parse_qs
import os, base64, io,json
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from jdash.apps import jdashConfig as config
from jdash.apps import constants as constants
from .layouts.main_layout import main_layout
from .layouts.ema_layout import ema_layout
from .callbacks.ema_callbacks import register_ema_callbacks
from .callbacks.default_callbacks import default_callbacks
app = DjangoDash('janalytica',suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
register_ema_callbacks(app)
default_callbacks(app)
app.layout =  dbc.Container([
                dbc.Row([
                    html.Div([
                    dcc.Store(id='study-store',data={} ),  # Must match
                    html.Div(id='output-div'),
                    html.Script("""
                    window.addEventListener("DOMContentLoaded", function() {
                        console.log("🔍 Dash page loaded.");
                    });

                    window.addEventListener("initialArgsReady", function(e) {
                        console.log("🧠 initialArgsReady received:", e.detail);
                    });
                """)
                    ], style={'display': 'none'},     ),
                        html.Div(
                            [
                                dcc.Store(id='sensor-store', data={}),
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


                    ]
                ),
                
                dbc.Row([

                    dbc.Col(
                    [
                        html.Div(
                            [
                                dbc.Label("Choose Study", html_for="studies-dropdown", className="form-label"),
                                dcc.Dropdown(
                                    id='studies-dropdown',
                                    options=[],
                                    value=None,
                                    placeholder="Select study",
                                  
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
                                    placeholder="Select x-axis (Date or study_day)"
                                ),
                            ],
                            style={'margin-bottom': '20px'},
                        ),
                        html.Div(
                            [
                                dbc.Label("Filter subjects", html_for="subject-filter", className="form-label"),
                                dcc.Dropdown(id="subject-filter", options=[], value=None, multi=True, placeholder="All subjects"),                  
                            ],),  


                            ],style={'background-color': '#f8f9fa'},md=3,
                    ),

                    dbc.Col(
                    [
                       html.Div(
                        [
                                    dcc.Loading(
                                        dcc.Graph(id='data-plot'),
                                        type="graph",
                                        style={'backgroundColor': '#eaeaea'}
                                    )

                        ]),
                        ],style={'background-color': '#f8f9fa'},md=9,
                ),

                    ]),
                
            ], fluid=True)   


@app.callback(
    Output('output-div', 'children'),
    Input('study-store', 'data')
)
def initial_data(data):
    #logger.info("Initial data callback triggered",data)
    return data

@app.callback(
    [Output('studies-dropdown', 'options'),
     Output('studies-dropdown', 'value'),
     Output('studies-dropdown', 'style')],
     Input('output-div', 'children')
)
def update_studies_tabs(studies):
    try:
        # Create the studies list for Tabs or Dropdown
        studies_list = [{'label': i, 'value': i} for i in studies]
        
        return  studies_list, studies_list[0]['value'] ,{}  # Hide tabs, show dropdown

    except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
        print(f"Error loading studies from API: {e}")
        return no_update, {'display': 'none'}, no_update, {'display': 'none'}  # Hide both if error

@app.callback(
    Output('sensor-output-div', 'children'),
    Input('sensor-store', 'data')
)
def initial_data(data):
    #logger.info("Initial data callback triggered",data)
    return data


@app.callback(
    [
     Output('sensor-dropdown', 'options'),
     Output('sensor-dropdown', 'value'),
     Output('sensor-dropdown', 'style')],
     Input('sensor-output-div', 'children'),
     Input('studies-dropdown', 'value'),          # <-- pick sensors for this study
)
def populate_sensor_dropdown(sensors_map, selected_study):
    try:
        key = (selected_study or "")
        sensors = sensors_map[key]
        # Create the studies list for Tabs or Dropdown
        sensor_list = [{'label': i, 'value': i} for i in sensors]
        
        return  sensor_list, sensor_list[0]['value'] ,{}  # Hide tabs, show dropdown

    except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
        print(f"Error loading studies from API: {e}")
        return no_update, no_update, {'display': 'none'}  # Hide both if error



# Callback to populate the dropdown with CSV files based on the selected value
@app.callback(
    Output('csv-options-store', 'data'),
    Input('studies-dropdown', 'value')
)
def update_selector(tab_value,selected_value):
   
    value = ""
    if selected_value is not None:
        value = selected_value
    elif tab_value is not None:
        value = tab_value
    # Define the directory path based on the selected value
    data_dir = os.path.join(config.analytics_storage_folder, value,"outputs")
    # Get a list of CSV files in the directory
    csv_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]

    return csv_files
    

@app.callback(
    Output('dynamic-layout', 'children'),
    Input('csv-options-store', 'data'),
    prevent_initial_call=True,
)
def render_layout(csv_files):
    if not csv_files:  # None or empty list
        return html.Div([
            html.H3("⚠️ No CSV files found."),
            html.P("Please upload files or check your outputs directory.")
        ], style={"padding": "20px", "color": "red"})
    # Normal layout when CSV files exist
    return html.Div([
            html.Label("Select CSV file"),
            dcc.Dropdown(
                id='csv-dropdown',
                options=[{'label': os.path.basename(file), 'value': file} for file in csv_files],
                placeholder="Select a CSV file"
            ),
            html.Div(id='conditional-layout')
        ],
        style={}
        )

# Callback to switch layout
@app.callback(
    Output('conditional-layout', 'children'),
    Input('csv-dropdown', 'value'),
    prevent_initial_call=True
)
def load_dynamic_layout(filename):
    if not filename:
        raise PreventUpdate

    filename_lower = filename.lower()

    if "main" in filename_lower:
        return main_layout()
    elif "ema" in filename_lower:
        return ema_layout()
    else:
        return default_layout()

                


