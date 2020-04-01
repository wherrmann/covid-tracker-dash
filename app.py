from dash.dependencies import Input, Output

import os
import time
from flask_caching import Cache
from flask import redirect, request
from urllib.parse import urlparse, urlunparse

import dash
import dash_core_components as dcc
import dash_html_components as html

from plots.plotly_figs import PlotlyFigs

from metadata.states import STATE_MAPPING, STATE_POP

TIMEOUT = 3600

app = dash.Dash(__name__)

app.index_string = '''
<!DOCTYPE html>
<html lang="en">
<html>
    <head>
        {%metas%}
        <title>COVID-19 Tracker Dash</title>
        <link rel="icon" href="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/google/241/world-map_1f5fa.png">
        {%css%}
        <link href="//fonts.googleapis.com/css?family=Raleway:400,300,600" rel="stylesheet" type="text/css">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.config.suppress_callback_exceptions = True

server = app.server

app.layout = html.Div(
    [
        html.Br(),
        html.Center(html.H1("COVID-19 Tracker Dash")),
        html.Br(),
        dcc.Tabs(
            id='tabs-covid',
            value='us',
            children=[
                dcc.Tab(label='US', value='us'),
                dcc.Tab(label='States', value='states'),
                dcc.Tab(label='Maps', value='maps')
            ]
        ),
        html.Br(),
        dcc.Loading(id="loading-1", children=[html.Div(id='tabs-content')], type="graph"),
        html.Br(),
        html.Footer(
            [
                html.Strong(dcc.Link('Created', href="https://github.com/wherrmann/covid-tracker-dash")),
                " by ",
                html.Strong(dcc.Link('herrmannwh', href="https://twitter.com/herrmannwh")),
                " with data from the ",
                html.Strong(dcc.Link('COVID Tracking Project', href="https://covidtracking.com")),
                "."
            ]
        )
    ],
    className="container"
)

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})

plotly_figs = PlotlyFigs(STATE_MAPPING, STATE_POP)

@cache.memoize(timeout=TIMEOUT)
def make_bar_figures(region):
    return plotly_figs.make_bar_figures(region)

@cache.memoize(timeout=TIMEOUT)
def make_map_figures():
    return plotly_figs.make_map_figures()

@cache.memoize(timeout=TIMEOUT)
def make_state_growth_plots():
    return plotly_figs.make_state_growth_plots()

state_growth_fig, state_growth_fig_per_capita = make_state_growth_plots()

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs-covid', 'value')])
def render_content(tab):
    if tab == 'us':
        return html.Div([
            dcc.Graph(id='graph-us',figure=make_bar_figures('US'))
        ])
    elif tab == 'states':
        content = html.Div([
            html.Label("State",form="stateForm",className="app__dropdown"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="state_dropdown",
                        value="NY",
                        options=[{"label": label, "value": val} for val, label in STATE_MAPPING.items()],
                    )
                ],
                id="stateForm",
                className="app__dropdown"
            ),
            dcc.Graph(id='state-graphs'),
            html.P(["Note: positive rates are not calculated for states with less than an 'A' ",
             dcc.Link('data quality rating.', href="https://covidtracking.com/about-tracker/#data-quality-grade"),
             " Tests administered are not shown for states with less than a 'C'."
            ]),
            html.Br(),
            html.H3('State Comparisons'),
            html.Label("Axis Type",form="yaxis-type-div"),
            html.Div([
                dcc.RadioItems(
                    id='yaxis-type',
                    options=[{'label': i, 'value': i} for i in ['Linear', 'Log']],
                    value='Log',
                    persistence=True,
                    labelStyle={'display': 'inline-block'}
                )
            ],
            id="yaxis-type-div"),
            dcc.Graph(id='state-growth'),
            dcc.Graph(id='state-capita'),
        ])
        return content
    elif tab == 'maps':
        return make_map_figures()

@app.callback(Output("state-growth", "figure"), [Input("yaxis-type", "value")])
def update_state_growth_fig(value):
    if value == 'Linear':
        yaxis_type = 'linear'
    else:
        yaxis_type = 'log'
    state_growth_fig.update_yaxes(type=yaxis_type)
    return state_growth_fig

@app.callback(Output("state-capita", "figure"), [Input("yaxis-type", "value")])
def update_state_growth_fig(value):
    if value == 'Linear':
        yaxis_type = 'linear'
    else:
        yaxis_type = 'log'
    state_growth_fig_per_capita.update_yaxes(type=yaxis_type)
    return state_growth_fig_per_capita

@app.callback(Output("state-graphs", "figure"), [Input("state_dropdown", "value")])
def make_figure(value):
    return make_bar_figures(value)

if __name__ == '__main__':
    app.run_server(debug=True)
