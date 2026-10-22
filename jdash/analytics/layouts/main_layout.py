from dash import html, dcc

def main_layout():
    return html.Div([ 
           
                html.Div([
            html.Label("Select X-axis variable:"),
            dcc.Dropdown(
                id='x-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select X-axis variable"
            ),
        ], style={ 'margin-top': '20px', 'margin-bottom': '20px'}),

        html.Div([
            html.Label("Select Y-axis variable:"),
            dcc.Dropdown(
                id='y-variable-dropdown',
                options=[],
                value=None,
                placeholder="Select Y-axis variable"
            ),
        ], style={   'margin-bottom': '20px'}),

        html.Div([
            html.Label("Filter subject-id:"),
            dcc.Dropdown(
                id='subject-id',
                options=[],
                value=None,
                multi=True,
                placeholder="All subjects"
            ),
        ], style={'margin-bottom': '20px'}),
        
        ])     

