"""Dash application wiring for the analytics page."""

import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash

from .callbacks.dashboard_callbacks import register_dashboard_callbacks
from .layouts.dashboard_layout import build_dashboard_layout, static_asset_url


app = DjangoDash(
    "janalytica",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        static_asset_url("css/dash_style.css?v=20261020-1"),
    ],
    external_scripts=[static_asset_url("dash/component/plotly/package_data/plotly.min.js")],
)

app.layout = build_dashboard_layout()
register_dashboard_callbacks(app)
