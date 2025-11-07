from dash import html, dcc

def default_layout():
    return html.Div([

        html.Div([
            html.Label("Select X-axis variable:"),
            dcc.Dropdown(
                id='x-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select X-axis variable"
            ),
        ], style={'display': 'inline-block', 'width': '20%', 'margin-right': '20px', 'margin-bottom': '20px'}),

        html.Div([
            html.Label("Select Y-axis variable:"),
            dcc.Dropdown(
                id='y-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select Y-axis variable"
            ),
        ], style={'display': 'inline-block', 'width': '20%', 'margin-right': '20px', 'margin-bottom': '20px'}),

        html.Div([
            dcc.Loading(
                dcc.Graph(id='selected-plot'),
                type="cube"
            ),
            dcc.Loading(
                dcc.Graph(id='mean-plot'),
                type="graph"
            )
        ], style={'margin-top': '30px'})
    ])