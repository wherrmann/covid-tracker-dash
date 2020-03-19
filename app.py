import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
import dash_html_components as html

from metadata.state_iso_codes import state_mapping

app = dash.Dash(__name__)

server = app.server

app.layout = html.Div(
    [
        html.H1("COVID-19 Tracker Dash"),
        html.Div(
            [
                dcc.Dropdown(
                    id="state_dropdown",
                    value="NY",
                    options=[{"label": label, "value": val} for val, label in state_mapping.items()],
                )
            ],
            className="app__dropdown"
        ),
        dcc.Graph(id="graph"),
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

@app.callback(Output("graph", "figure"), [Input("state_dropdown", "value")])
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
            "Daily New Cases - {}".format(state_mapping[state]),
            "Daily New Tests Administered - {}".format(state_mapping[state]),
            "Positive Test Rate, Aggregate - {}".format(state_mapping[state]),
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
