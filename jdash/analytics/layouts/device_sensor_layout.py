from dash import dcc, html
from django.utils.translation import gettext_lazy as _


def device_sensor_layout():
    return html.Div(
        [
            html.Div(
                [
                    html.Label(_("Select chart type:")),
                    dcc.Dropdown(
                        id="device-sensor-chart-type",
                        options=[
                            {"label": _("Auto"), "value": "auto"},
                            {"label": _("Line"), "value": "line"},
                            {"label": _("Scatter"), "value": "scatter"},
                            {"label": _("Bar"), "value": "bar"},
                            {"label": _("Box"), "value": "box"},
                        ],
                        value="auto",
                        clearable=False,
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label(_("Device")),
                    dcc.Dropdown(
                        id="device-sensor-device-filter",
                        options=[],
                        value=None,
                        multi=True,
                        placeholder=_("All selected values"),
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label(_("Select sensor")),
                    dcc.Dropdown(
                        id="device-sensor-sensor-filter",
                        options=[],
                        value=None,
                        multi=True,
                        placeholder=_("All selected values"),
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label(_("Filter subjects")),
                    dcc.Dropdown(
                        id="device-sensor-subject-filter",
                        options=[],
                        value=None,
                        multi=True,
                        placeholder=_("All subjects"),
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label(_("Choose X-axis")),
                    dcc.Dropdown(
                        id="device-sensor-x-axis",
                        options=[],
                        value=None,
                        placeholder=_("Select X-axis variable"),
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
            html.Div(
                [
                    html.Label(_("Select Y-axis variable:")),
                    dcc.Dropdown(
                        id="device-sensor-y-axis",
                        options=[],
                        value=None,
                        placeholder=_("Select Y-axis variable"),
                    ),
                ],
                style={"margin-bottom": "20px"},
            ),
        ]
    )

