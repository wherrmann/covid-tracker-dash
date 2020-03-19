import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
import dash_html_components as html

from metadata.states import STATE_MAPPING, STATE_POP

app = dash.Dash(__name__)

app.config.suppress_callback_exceptions = True

server = app.server

app.layout = html.Div(
    [
        html.H1("COVID-19 Tracker Dash"),
        dcc.Tabs(
            id='tabs-covid',
            value='us',
            children=[
                dcc.Tab(label='US', value='us'),
                dcc.Tab(label='States', value='states'),
                dcc.Tab(label='Maps', value='maps')
            ]
        ),
        html.Div(id='tabs-content'),
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
    ]
)

def make_us_agg_figures():
    url = 'https://covidtracking.com/api/us/daily'
    r = requests.get(url)
    data = r.json()

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'],format = '%Y%m%d')
    df = df.sort_values(by='date')

    df['new_positive'] = df['positive'].diff()
    df['new_total'] = df['total'].diff()
    df['positive_rate'] = df['positive']/df['posNeg']

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Daily New Cases - {}".format('US'),
            "Daily New Tests Administered - {}".format('US'),
            "Positive Test Rate, Aggregate - {}".format('US')
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
        font=dict(
            family="Raleway, monospace",
            size=18,
            color="#222"
        ),
        showlegend=False,
        height = 1400
    )
    return fig


def make_map_figures():
    r = requests.get('https://covidtracking.com/api/states')
    data = r.json()
    for state in data:
        state['state_name'] = STATE_MAPPING[state['state']]
    raw_df = pd.DataFrame(data)
    geojson = requests.get('https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_500k.json')
    states_geo = geojson.json()
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

    fig1 = px.choropleth_mapbox(df[df['positives_per_million'].notna()],
        locations="state_name",
        geojson=states_geo,
        featureidkey="properties.NAME",
        color="positives_per_million",
        color_continuous_scale="viridis_r",
        opacity=0.5,
        title ="Confirmed Cases per Million People",
        center = {"lat": 37.0902, "lon": -95.7129},
        zoom=3,
        mapbox_style="carto-positron",
        height = 800
    )
    fig1.update(
        layout=dict(
            font=dict(
                family="Raleway, monospace",
                size=18,
                color="#222"
            )
        )
    )
    fig2 = px.choropleth_mapbox(df[df['tests_per_million'].notna()],
        locations="state_name",
        geojson=states_geo,
        featureidkey="properties.NAME",
        color="tests_per_million",
        color_continuous_scale="viridis_r",
        opacity=0.5,
        title ="Tests Per Million People",
        center = {"lat": 37.0902, "lon": -95.7129},
        zoom=3,
        mapbox_style="carto-positron",
        height = 800
    )
    fig2.update(
        layout=dict(
            font=dict(
                family="Raleway, monospace",
                size=18,
                color="#222"
            )
        )
    )
    fig3 = px.choropleth_mapbox(df[df['positives_per_hundred_tests'].notna()],
        locations="state_name",
        geojson=states_geo,
        featureidkey="properties.NAME",
        color="positives_per_hundred_tests",
        color_continuous_scale="viridis_r",
        opacity=0.5,
        title ="Positives per Hundred Tests Administered",
        center = {"lat": 37.0902, "lon": -95.7129},
        zoom=3,
        mapbox_style="carto-positron",
        height = 800
    )
    fig3.update(
        layout=dict(
            font=dict(
                family="Raleway, monospace",
                size=18,
                color="#222"
            )
        )
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
            dcc.Graph(id='graph-us',figure=make_us_agg_figures())
        ])
    elif tab == 'states':
        content = html.Div([
            html.Div(
                [
                    dcc.Dropdown(
                        id="state_dropdown",
                        value="NY",
                        options=[{"label": label, "value": val} for val, label in STATE_MAPPING.items()],
                    )
                ],
                className="app__dropdown"
            ),
            dcc.Graph(id='state-graphs')
        ])
        return content
    elif tab == 'maps':
        return make_map_figures()

@app.callback(Output("state-graphs", "figure"), [Input("state_dropdown", "value")])
def make_figure(value):
    state = value
    url = 'https://covidtracking.com/api/states/daily?state={}'.format(state)
    r = requests.get(url)
    data = r.json()

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'],format = '%Y%m%d')
    df = df.sort_values(by='date')

    df['posNeg'] = df['positive'] + df['negative']
    df['new_positive'] = df['positive'].diff()
    df['new_total'] = df['total'].diff()
    df['positive_rate'] = df['positive']/df['posNeg']

    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Daily New Cases - {}".format(STATE_MAPPING[state]),
            "Daily New Tests Administered - {}".format(STATE_MAPPING[state]),
            "Positive Test Rate, Aggregate - {}".format(STATE_MAPPING[state]),
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
        font=dict(
            family="Raleway, monospace",
            size=18,
            color="#222"
        ),
        showlegend=False,
        height = 1400
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
