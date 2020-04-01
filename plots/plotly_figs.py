import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
import dash_html_components as html

FIG_FONT_DICT = {
    'family': "Raleway, monospace",
    'size' : 18,
    'color' : "#222"
}

BASE_API_URL = 'https://covidtracking.com/api/'

class PlotlyFigs:

    def __init__(self, state_mapping, state_pop):
        self.state_mapping = state_mapping
        self.state_pop = state_pop

    def get_data(self, endpoint):
        """
        Retrieve foundational data from covidtracking.com.
        """
        base_url = BASE_API_URL
        url = '/'.join([base_url,endpoint])
        r = requests.get(url)
        data = r.json()
        return data

    def make_bar_figures(self, region):
        """
        Makes three figure plotly subplot with these metrics:
         - Daily new cases
         - Daily new tests administered
         - Daily positive test rate
        """

        if region == 'US':
            data = self.get_data('us/daily')
            data_grade = 'A'
        else:
            data = self.get_data('states/daily?state={}'.format(region))
            data_grade = self.get_data('states?state={}'.format(region))['grade']
            region = self.state_mapping[region]

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'],format = '%Y%m%d')
        df = df.sort_values(by='date')

        df['positive_rate'] = df['positiveIncrease']/df['totalTestResultsIncrease']

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
                y=df['positiveIncrease'],
                name=""
            ),
            row=1,
            col=1
        )
        if data_grade in ['A','B','C']:
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['totalTestResultsIncrease'],
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

    def make_map_figures(self):
        """
        Makes three choropleth mapbox figures of the US for these metrics:
         - Cases per capita
         - Tests per capita
         - Positive test rate
        """
        data = self.get_data('states')
        for state in data:
            state['state_name'] = self.state_mapping[state['state']]
        raw_df = pd.DataFrame(data)

        # get geojson data for use in mapping states
        geojson = requests.get('https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_500k.json')
        states_geo = geojson.json()

        # get state population data from census.gov
        states_pop = self.state_pop
        states_pop_df = pd.DataFrame(states_pop['data'])
        df = pd.merge(raw_df,states_pop_df,left_on='state_name',right_on='State')

        df['positive_rate'] = df['positive']/df['totalTestResults']
        df['positives_per_hundred_tests'] = df['positive_rate']*100
        df['tests_per_capita'] = df['totalTestResults']/df['Population']
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

    def make_state_growth_plots(self):
        data = self.get_data('states/daily')
        for state in data:
            state['state_name'] = self.state_mapping[state['state']]
        raw_df = pd.DataFrame(data)
        raw_df['date'] = pd.to_datetime(raw_df['date'],format = '%Y%m%d')

        # get state population data from census.gov
        states_pop = self.state_pop
        states_pop_df = pd.DataFrame(states_pop['data'])
        df = pd.merge(raw_df,states_pop_df,left_on='state_name',right_on='State')

        df['tests_per_capita'] = df['totalTestResults']/df['Population']
        df['positives_per_capita'] = df['positive']/df['Population']
        df['positives_per_million'] = df['positives_per_capita']*1000000

        df = df.sort_values(by='date')
        df['days_since_hundredth_case'] = df[df['positive']>=100].groupby(['state']).cumcount()
        df['days_since_10_per_million'] = df[df['positives_per_million']>=10].groupby(['state']).cumcount()

        df_non_nulls_hundredth = df[df['days_since_hundredth_case'].notnull()]
        df_non_nulls_per_capita = df[df['days_since_10_per_million'].notnull()]

        fig = px.scatter(
            df_non_nulls_hundredth,
            x='days_since_hundredth_case',
            y='positive',
            color='state_name',
            labels = {'days_since_hundredth_case':'Days Since 100th Positive','positive':'Total Positives'},
            log_y=True
        )

        for trace in fig.data:
            trace.update(mode='markers+lines')

        fig_per_capita = px.scatter(
            df_non_nulls_per_capita,
            x='days_since_10_per_million',
            y='positives_per_million',
            color='state_name',
            labels = {'days_since_10_per_million':'Days Since 10 Positive per Million','positives_per_million':'Positives per Million People'},
            log_y=True
        )

        for trace in fig_per_capita.data:
            trace.update(mode='markers+lines')

        return fig, fig_per_capita
