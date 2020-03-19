import pandas as pd
from dash.dependencies import Input, Output
import requests
import plotly.express as px
import plotly.io as pio

import dash
import dash_core_components as dcc
import dash_html_components as html

pio.templates.default = "plotly_white"

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

state_mapping = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AS": "American Samoa",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District Of Columbia",
    "FM": "Federated States Of Micronesia",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MH": "Marshall Islands",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "MP": "Northern Mariana Islands",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PW": "Palau",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VI": "Virgin Islands",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming"
}

app.layout = html.Div(
    [
        html.H1("Demo: COVID-19"),
        html.Div(
            [
                dcc.Dropdown(
                    id="state_dropdown",
                    value='NY',
                    options=[{"label": label, "value": val} for val, label in state_mapping.items()],
                )
            ],
            className="app__dropdown",
        ),
        dcc.Graph(id="graph")
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
    # df['posNeg'] = df['positive'] + df['negative']
    # df['new_posNeg'] = df['posNeg'].diff()
    # df['new_death'] = df['death'].diff()
    df['new_positive'] = df['positive'].diff()
    # df['new_total'] = df['total'].diff()
    # df['fatality_rate'] = df['death']/df['positive']
    # df['positive_rate'] = df['positive']/df['posNeg']
    # df['daily_positive_rate'] = df['new_positive']/df['new_posNeg']
    # df['daily_fatality_rate'] = df['new_death']/df['new_positive']
    return px.bar(df,
        x="date",
        y="new_positive",
        title ="Daily New {} Positive Cases".format(state_mapping[state]),
        labels = {'x':'Date','y':'Confirmed Cases'}
    )

if __name__ == '__main__':
    app.run_server(debug=True)
