import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.express as px
import plotly.io as pio

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
                    options=[{"label": label, "value": val} for val, label in state_mapping.items()],
                )
            ],
            className="app__dropdown",
        ),
        dcc.Graph(id="graph"),
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

    df['new_positive'] = df['positive'].diff()
    df['new_total'] = df['total'].diff()
    df['positive_rate'] = df['positive']/df['posNeg']
    df['daily_positive_rate'] = df['new_positive']/df['new_posNeg']

    fig = px.bar(df,
        x="date",
        y="new_positive",
        title ="Daily New Cases - {}".format(state_mapping[state])
    )
    fig.update_xaxes(title_text='Date')
    fig.update_yaxes(title_text='Confirmed Cases')
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
