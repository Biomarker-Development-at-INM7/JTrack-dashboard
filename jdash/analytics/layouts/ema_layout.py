from dash import html, dcc


def ema_layout():
    return html.Div(
        [
            html.Div(
                [
                    html.Label("Select X-axis variable:", id="ema-x-axis-label"),
                    dcc.Dropdown(
                        id="ema-x-axis-dropdown",
                        options=[],
                        value=None,
                        placeholder="Select EMA dimension",
                    ),
                ],
                id="ema-x-axis-container",
                style={"margin-top": "20px","margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label("Select Y-axis variable:", id="ema-y-axis-label"),
                    dcc.Dropdown(
                        id="ema-y-axis-dropdown",
                        options=[],
                        value=None,
                        placeholder="Select EMA metric",
                    ),
                ],
                id="ema-y-axis-container",
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label("Filter X-axis values:", id="ema-x-axis-values-label"),
                    dcc.Dropdown(
                        id="ema-x-axis-values",
                        options=[],
                        value=None,
                        multi=True,
                        placeholder="All selected values",
                    ),
                ],
                id="ema-x-axis-values-container",
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label("Filter subject-id:", id="ema-subject-label"),
                    dcc.Dropdown(
                        id="ema-subject-id",
                        options=[],
                        value=None,
                        multi=True,
                        placeholder="All subjects",
                    ),
                ],
                id="ema-subject-container",
                style={"margin-bottom": "20px"},
            ),
        ]
    )

