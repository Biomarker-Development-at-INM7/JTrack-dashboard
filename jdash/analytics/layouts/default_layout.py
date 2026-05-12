from dash import html, dcc
import dash_bootstrap_components as dbc

def default_layout():
    return html.Div(
        [
                    dcc.Loading(
                        dcc.Graph(id='heat-plot'),
                        type="graph",
                        style={'backgroundColor': '#f8f9fa'}
                    )
               
        ]
    )
