from dash import html, dcc
from dash.dependencies import Input, Output

def ema_layout():
    return html.Div([ 
            html.Div([
                html.Div([
            html.Label("Select X-axis variable:"),
            dcc.Dropdown(
                id='x-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select X-axis variable"
            ),
        ], style={'display': 'inline-block', 'width': '20%', 'margin-right': '10px', 'margin-bottom': '10px'}),

        html.Div([
            html.Label("Select Y-axis variable:"),
            dcc.Dropdown(
                id='y-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select Y-axis variable"
            ),
        ], style={'display': 'inline-block', 'width': '20%', 'margin-right': '20px', 'margin-bottom': '20px'}),
        
            
            ],style={'margin-top': '20px'}),
            html.Div([
                                 html.Div([
                    html.Label("Select subject-id:"),
                    dcc.Dropdown(
                        id='subject-id',
                        options=[],
                        value=None,
                        placeholder="Select subject-id"
                    ),
                ], style={'display': 'inline-block', 'width': '30%', 'margin-right': '20px'}),

                html.Div([
                    html.Label("For HeatMap select end subject-id:"),
                    dcc.Dropdown(
                        id='subject-id-end',
                        options=[],
                        value=None,
                        placeholder="Select end subject-id"
                    ),
                ], style={'display': 'inline-block', 'width': '30%', 'margin-right': '20px'})
            ], style={'margin-top': '20px'}),
            dcc.Loading(
                    dcc.Graph(id='selected-plot'),
                    type="cube"
                ),
            dcc.Loading(
                dcc.Graph(id='mean-plot'),
                type="graph"
            )
        ])     

