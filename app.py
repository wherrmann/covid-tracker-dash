import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import os
import time
from flask_caching import Cache
from flask import redirect, request
from urllib.parse import urlparse, urlunparse

import dash
import dash_core_components as dcc
import dash_html_components as html

from metadata.states import STATE_MAPPING, STATE_POP

FIG_FONT_DICT = {
    'family': "Raleway, monospace",
    'size' : 18,
    'color' : "#222"
}
BASE_API_URL = 'https://covidtracking.com/api/'

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

TIMEOUT = 3600

def get_data(endpoint):
    """
    Retrieve foundational data from covidtracking.com.
    """
    base_url = BASE_API_URL
    url = '/'.join([base_url,endpoint])
    r = requests.get(url)
    data = r.json()
    return data

@cache.memoize(timeout=TIMEOUT)
def make_bar_figures(region):
    """
    Makes three figure plotly subplot with these metrics:
     - Daily new cases
     - Daily new tests administered
     - Daily positive test rate
    """

    if region == 'US':
        data = get_data('us/daily')
        data_grade = 'A'
    else:
        data = get_data('states/daily?state={}'.format(region))
        data_grade = get_data('states?state={}'.format(region))['grade']
        region = STATE_MAPPING[region]

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'],format = '%Y%m%d')
    df = df.sort_values(by='date')

    # posNeg isn't returned by every endpoint
    if 'posNeg' not in list(df.columns):
        df['posNeg'] = df['positive'] + df['negative']

    df['new_positive'] = df['positive'].diff()
    df['new_total'] = df['total'].diff()
    df['new_posNeg'] = df['posNeg'].diff()
    df['positive_rate'] = df['new_positive']/df['new_posNeg']

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Daily New Cases - {}".format(region),
            "Daily New Tests Administered - {}".format(region),
            "Daily Positive Test Rate - {}".format(region)
        ),
        x_title="Date",
        vertical_spacing=0.1
    )
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['new_positive'],
            name=""
        ),
        row=1,
        col=1
    )
    if data_grade in ['A','B','C']:
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['new_total'],
                name=""
            ),
            row=2,
            col=1
        )
    if data_grade == 'A':
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['positive_rate'],
                name=""
            ),
            row=3,
            col=1
        )
    fig.update_yaxes(title_text="Confirmed Cases", row=1, col=1)
    fig.update_yaxes(title_text="Tests Administered", row=2, col=1)
    fig.update_yaxes(title_text="Positive Test Rate", tickformat = ',.0%', row=3, col=1)
    fig.update_layout(
        font=FIG_FONT_DICT,
        showlegend=False,
        height = 1400
    )
    return fig

@cache.memoize(timeout=TIMEOUT)
def make_map_figures():
    """
    Makes three choropleth mapbox figures of the US for these metrics:
     - Cases per capita
     - Tests per capita
     - Positive test rate
    """
    data = get_data('states')
    for state in data:
        state['state_name'] = STATE_MAPPING[state['state']]
    raw_df = pd.DataFrame(data)

    # get geojson data for use in mapping states
    geojson = requests.get('https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_500k.json')
    states_geo = geojson.json()

    # get state population data from census.gov
    states_pop = STATE_POP
    states_pop_df = pd.DataFrame(states_pop['data'])
    df = pd.merge(raw_df,states_pop_df,left_on='state_name',right_on='State')

    df['posNeg'] = df['positive'] + df['negative']
    df['positive_rate'] = df['positive']/df['posNeg']
    df['positives_per_hundred_tests'] = df['positive_rate']*100
    df['tests_per_capita'] = df['total']/df['Population']
    df['positives_per_capita'] = df['positive']/df['Population']
    df['positives_per_million'] = df['positives_per_capita']*1000000
    df['tests_per_million'] = df['tests_per_capita']*1000000

    layout_dict = {'font': FIG_FONT_DICT}

    standard_choropleth_mapbox_args = {
        'locations' : "state_name",
        'geojson' : states_geo,
        'featureidkey' : "properties.NAME",
        'color_continuous_scale' : "viridis_r",
        'opacity' : 0.5,
        'center' : {"lat": 37.0902, "lon": -95.7129},
        'zoom' : 2.5,
        'mapbox_style' : "carto-positron",
        'height' : 600
    }

    fig1 = px.choropleth_mapbox(df[df['positives_per_million'].notna()],
        title ="Confirmed Cases per Million People",
        color="positives_per_million",
        **standard_choropleth_mapbox_args
    )
    fig1.update(
        layout=layout_dict
    )
    nonnull_df = df[df['tests_per_million'].notna()]
    fig2 = px.choropleth_mapbox(nonnull_df[df['grade']!='D'],
        title ="Tests Per Million People",
        color="tests_per_million",
        **standard_choropleth_mapbox_args
    )
    fig2.update(
        layout=layout_dict
    )
    nonnull_df = df[df['positives_per_hundred_tests'].notna()]
    fig3 = px.choropleth_mapbox(nonnull_df[df['grade']=='A'],
        title ="Positives per Hundred Tests Administered",
        color="positives_per_hundred_tests",
        **standard_choropleth_mapbox_args
    )
    fig3.update(
        layout=layout_dict
    )
    graphs_div = html.Div([
        dcc.Graph(id='graph-map-1',figure=fig1),
        dcc.Graph(id='graph-map-2',figure=fig2),
        dcc.Graph(id='graph-map-3',figure=fig3),
            html.P(["Note: positive rates are not calculated for states with less than an 'A' ",
             dcc.Link('data quality rating.', href="https://covidtracking.com/about-tracker/#data-quality-grade"),
             " Tests administered are not shown for states with less than a 'C'."
            ])
    ])
    return graphs_div

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs-covid', 'value')])
def render_content(tab):
    if tab == 'us':
        return html.Div([
            dcc.Graph(id='graph-us',figure=make_bar_figures('US'))
        ])
    elif tab == 'states':
        content = html.Div([
            html.Br(),
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
            ])
        ])
        return content
    elif tab == 'maps':
        return make_map_figures()

@app.callback(Output("state-graphs", "figure"), [Input("state_dropdown", "value")])
def make_figure(value):
    return make_bar_figures(value)

if __name__ == '__main__':
    app.run_server(debug=True)
