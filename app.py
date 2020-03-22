import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import os
import time
from flask_caching import Cache

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
def make_bar_figures(endpoint, region):
    """
    Makes three figure plotly subplot with these metrics:
     - Daily new cases
     - Daily new tests administered
     - Aggregate positive test rate
    """
    data = get_data(endpoint)
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'],format = '%Y%m%d')
    df = df.sort_values(by='date')

    # posNeg isn't returned by every endpoint
    if 'posNeg' not in list(df.columns):
        df['posNeg'] = df['positive'] + df['negative']

    df['new_positive'] = df['positive'].diff()
    df['new_total'] = df['total'].diff()
    df['positive_rate'] = df['positive']/df['posNeg']

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Daily New Cases - {}".format(region),
            "Daily New Tests Administered - {}".format(region),
            "Positive Test Rate, Aggregate - {}".format(region)
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
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['new_total'],
            name=""
        ),
        row=2,
        col=1
    )
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
        'zoom' : 3,
        'mapbox_style' : "carto-positron",
        'height' : 800
    }

    fig1 = px.choropleth_mapbox(df[df['positives_per_million'].notna()],
        title ="Confirmed Cases per Million People",
        color="positives_per_million",
        **standard_choropleth_mapbox_args
    )
    fig1.update(
        layout=layout_dict
    )
    fig2 = px.choropleth_mapbox(df[df['tests_per_million'].notna()],
        title ="Tests Per Million People",
        color="tests_per_million",
        **standard_choropleth_mapbox_args
    )
    fig2.update(
        layout=layout_dict
    )
    fig3 = px.choropleth_mapbox(df[df['positives_per_hundred_tests'].notna()],
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
        dcc.Graph(id='graph-map-3',figure=fig3)
    ])
    return graphs_div

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs-covid', 'value')])
def render_content(tab):
    if tab == 'us':
        return html.Div([
            dcc.Graph(id='graph-us',figure=make_bar_figures('us/daily','US'))
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
            dcc.Graph(id='state-graphs')
        ])
        return content
    elif tab == 'maps':
        return make_map_figures()

@app.callback(Output("state-graphs", "figure"), [Input("state_dropdown", "value")])
def make_figure(value):
    return make_bar_figures('states/daily?state={}'.format(value),STATE_MAPPING[value])

if __name__ == '__main__':
    app.run_server(debug=True)
