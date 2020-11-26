from dash import dash

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from app import app

hhu_icon = 'assets/hhu-icon.png'
fz_icon = 'assets/fz-icon.png'
bb_icon = 'assets/bb-icon.png'


def get_main_page():
    return html.Div([
        dcc.Location(id='url', refresh=False),
        html.Header(id='page-header', children=get_header()),
        html.Div(id='login-wrapper', children=get_log_in_div()),
        html.Div(id='page-body'),
        html.Footer(id='page-footer', children=get_footer())
    ])


def get_header():
    return html.Div(id='header-div', className='row', children=[
        html.Div(id='title-wrapper', style={'float': 'left'}, children=[
            html.H1(id='title', children='JuTrack Dashboard'),
            html.H6(id='subtitle', children=[
                html.Span('by '),
                html.A('Biomarker Development Group, INM-7',
                       href='https://www.fz-juelich.de/inm/inm-7/EN/Forschung/Biomarker%20Development/artikel.html?nn=654270',
                       target='_blank', rel='noreferrer')])
        ]),
        html.Div(id='icons-wrapper', style={'float': 'right'}, children=[
            html.A(html.Img(style={'border-left': '0'}, src=hhu_icon), href='https://www.medizin.hhu.de/',
                   target='_blank', rel='noreferrer'),
            html.A(html.Img(style={'border-left': '0'}, src=fz_icon),
                   href='https://www.fz-juelich.de/portal/EN/Home/home_node.html', target='_blank',
                   rel='noreferrer'),
            html.A(html.Img(style={'border-left': '0', 'border-right': '0'}, src=bb_icon),
                   href='https://www.fz-juelich.de/inm/inm-7/EN/Home/home_node.html', target='_blank',
                   rel='noreferrer')
        ]),
    ])


def get_body():
    return html.Div(id='body-div', className='row', children=[
        html.Div(id='menu-wrapper', children=get_menu()),
        html.Div(id='content-wrapper', children=html.Div(id='content-div'))
    ])


def get_footer():
    return html.Div(id='footer-div', children=[
        html.Div(id='info-text', children=[
            html.P(children=
                   "You are visiting the JuTrack website which provides access to the dashboard for managing research studies "
                   "running on the JuTrack mobile platform."),
            html.P(children=
                   "JuTrack is developed by the Group Biomarker Development of the Institute "
                   "for Neuroscience and Medicine 7 (Brain and Behaviour) at the Forschungszentrum Jülich. It is a multifunctional "
                   "Android-based digital biomarker platform for collection of sensor, mobile usage and ecological momentary assessment "
                   "information from mobile and wearable devices."),
            html.P(children=
                   "JuTrack is developed as an open source solution (release in preparation, "
                   "Sahandi-Far et al.). It is currently deployed in several clinical and mobile health studies. If you are interested "
                   "in collaboration with us or would like to learn more about JuTrack or our studies please reach out to "
                   "Dr. Juergen Dukart (j.dukart@fz-juelich.de)."),
            html.P(children=["You can find more information about our group on: ", html.A(
                children="https://www.fz-juelich.de/inm/inm-7/EN/Forschung/Biomarker%20Development/_node.html",
                href="https://www.fz-juelich.de/inm/inm-7/EN/Forschung/Biomarker%20Development/_node.html")]),
        ])
    ])


def get_menu():
    return html.Div(id='menu-div', children=[
        html.Button(id='create-button', children='Create Study'),
        html.Button(id='current-studies-button', children='Current Studies', className='top-border'),
        html.Button(id='close-button', children='Close Study', className='top-border'),
        html.Button(id='about-button', children='About', className='top-border'),
    ])


@app.callback(Output('content-div', 'children'),
              [Input('create-button', 'n_clicks'),
               Input('current-studies-button', 'n_clicks'),
               Input('about-button', 'n_clicks'),
               Input('close-button', 'n_clicks')
               ])
def display_menu_tab_content_callback(btn1, btn2, btn3, btn4):
    """
    Callback reacting if a menu button is clicked. Returns clicked button content

    :param btn1: not used due callback_context syntax
    :param btn2: not used due callback_context syntax
    :param btn3: not used due callback_context syntax
    :param btn4: not used due callback_context syntax
    :return: Several possible divs depending which button was clicked. The div is displayed on the page right next
            to the menu. Returned by Output('page-content', 'children')
    """

    ctx = dash.callback_context
    if len(ctx.triggered) > 0:
        if ctx.triggered[0]['value']:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'create-button' and user.role == 'master':
                return get_create_study_div()
            if button_id == 'current-studies-button':
                return get_current_studies_div()
            if button_id == 'close-button' and user.role == 'master':
                return get_close_study_div()
            if button_id == 'about-button':
                return get_about_div()
    raise PreventUpdate


app.layout = get_main_page()
user = DashboardUser()

if __name__ == '__main__':
    app.run_server(debug=True)
