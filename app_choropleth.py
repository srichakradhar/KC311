import pathlib
import os
import json

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import Namespace
from dash import Dash
import geopandas as gpd


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create the app
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
    external_scripts=[chroma],
    external_stylesheets=external_stylesheets,
    prevent_initial_callbacks=True
)

server = app.server
app.config["suppress_callback_exceptions"] = True
app.title = "311 Community Enagement"

# mapbox
mapbox_access_token = "pk.eyJ1Ijoic3JpY2hha3JhZGhhciIsImEiOiJja2lqZXh6aTYwMjE4MndvOG5iZGUzZ2hkIn0.j6cqd-ISDEhuvAyIRb0mDA"
# srichakradhar: pk.eyJ1Ijoic3JpY2hha3JhZGhhciIsImEiOiJja2lqZXh6aTYwMjE4MndvOG5iZGUzZ2hkIn0.j6cqd-ISDEhuvAyIRb0mDA
# Load data
APP_PATH = str(pathlib.Path(__file__).parent.resolve())
cols = ['CASE ID', 'SOURCE', 'DEPARTMENT', 'WORK GROUP', 'REQUEST TYPE',
        'CATEGORY', 'TYPE', 'DETAIL', 'CREATION DATE', 'CREATION TIME',
        'CREATION MONTH', 'CREATION YEAR', 'STATUS', 'EXCEEDED EST TIMEFRAME',
        'CLOSED DATE', 'CLOSED MONTH', 'CLOSED YEAR', 'DAYS TO CLOSE', 'STREET ADDRESS',
        'ZIP CODE', 'NEIGHBORHOOD', 'LATITUDE', 'LONGITUDE', 'COUNTY', 'CASE URL', 'nbh_id', 'nbh_name']
df = pd.concat([pd.read_csv(os.path.join(APP_PATH, os.path.join("data", nbh)), usecols=cols)
                for nbh in os.listdir(os.path.join(APP_PATH, "data")) if nbh.endswith('.csv')])
df.rename(columns={'nbh_id': 'nbhid'}, inplace=True)
color_prop = 'DAYS TO CLOSE'

with open(os.path.join(APP_PATH, os.path.join("data", 'KCNeighborhood.geojson'))) as f:
    kcnbh_geojson = json.loads(f.read())

intro_text = """
**About Community Engagement**
This app applies spatial clustering and regionalization analysis to discover the trends of [311 Calls in Kansas City](http://insideairbnb.com/get-the-data.html). Models are created using [pysal](https://pysal.readthedocs.io/en/latest/)
and scikit-learn.
Select the type of model from dropdown, click on the button to run clustering and visualize output regions geographically on the map, computing may take seconds to finish. Click
on regions on the map to update the number of 311 Calls from your highlighted neighborhood.
"""


def header_section():
    return html.Div(
        [
            html.Img(src=app.get_asset_url(
                "ocelai-logo.jpg"), className="logo"),
            html.H4("311 Community Engagement - OCEL.AI")
        ],
        className="header__title",
    )


def populate_init_data():
    return {}


def make_base_map():
    # Scattermapbox with geojson layer, plot all listings on mapbox
    ivanhoe_df = df[df['nbh_id'] == 54]
    customdata = list(
        zip(
            ivanhoe_df["CASE ID"],
            ivanhoe_df["DEPARTMENT"],
            ivanhoe_df["NEIGHBORHOOD"],
            ivanhoe_df["REQUEST TYPE"],
            ivanhoe_df["DETAIL"],
            ivanhoe_df["STREET ADDRESS"]
        )
    )
    mapbox_figure = dict(
        type="scattermapbox",
        lat=df["LATITUDE"],
        lon=df["LONGITUDE"],
        marker=dict(size=7, opacity=0.7, color="#550100"),
        customdata=customdata,
        name="311 Call",
        hovertemplate="<b>Case ID: %{customdata[0]}</b><br><br>"
        "<b>Department: %{customdata[1]}</b><br>"
        "<b>Neighborhood: </b>%{customdata[2]}<br>"
        "<b>Category: </b>%{customdata[3]} / night<br>"
        "<b>Details: </b>%{customdata[4]}<br>"
        "<b>Street Address: </b>%{customdata[5]}",
    )

    layout = dict(
        mapbox=dict(
            style="streets",
            uirevision=True,
            accesstoken=mapbox_access_token,
            zoom=12,
            center=dict(
                lon=df["LONGITUDE"].mean(),
                lat=df["LATITUDE"].mean(),
            ),
        ),
        shapes=[
            {
                "type": "rect",
                "xref": "paper",
                "yref": "paper",
                "x0": 0,
                "y0": 0,
                "x1": 1,
                "y1": 1,
                "line": {"width": 1, "color": "#B0BEC5"},
            }
        ],
        margin=dict(l=10, t=10, b=10, r=10),
        height=600,
        showlegend=True,
        hovermode="closest",
    )

    figure = {"data": [mapbox_figure], "layout": layout}
    return figure



def get_data(nbhid, years_range):
    # filter_df = df[(df['CREATION YEAR'] <= years_range[1]) &
    #                (df['CREATION YEAR'] >= years_range[0])]
    df_nbh = df[df["nbhid"] == nbhid]  # pick one state
    df_nbh = df_nbh[['LATITUDE', 'LONGITUDE', 'NEIGHBORHOOD', 'DAYS TO CLOSE']]  # use only relevant columns
    dicts = df_nbh.to_dict('rows')
    for item in dicts:
        item["tooltip"] = "{:.1f}".format(item[color_prop])  # bind tooltip
        item["popup"] = item["NEIGHBORHOOD"]  # bind popup
    geojson = dlx.dicts_to_geojson(dicts, lat="LATITUDE", lon="LONGITUDE")  # convert to geojson
    geobuf = dlx.geojson_to_geobuf(geojson)  # convert to geobuf
    return geobuf


def get_minmax(nbhid):
    df_state = df[df["nbhid"] == nbhid]  # pick one neighborhood
    return dict(min=0, max=np.log(df_state[color_prop].max()))


# Setup a few color scales.
csc_map = {"Rainbow": ['red', 'yellow', 'green', 'blue', 'purple'],
           "Hot": ['yellow', 'red', 'black'],
           "Viridis": "Viridis"}
csc_options = [dict(label=key, value=json.dumps(csc_map[key])) for key in csc_map]
default_csc = "Rainbow"
dd_csc = dcc.Dropdown(options=csc_options, value=json.dumps(csc_map[default_csc]), id="dd_csc", clearable=False)
# Setup state options.
states = df["nbhid"].unique()
state_names = [df[df["nbhid"] == state]["nbh_name"].iloc[0] for state in states]
state_options = [dict(label=state_names[i], value=state) for i, state in enumerate(states)]
default_state = "76"
dd_state = dcc.Dropdown(options=state_options, value=default_state, id="dd_state", clearable=False)

# endregion

minmax = get_minmax(default_state)
# Create geojson.
ns = Namespace("dlx", "scatter")
geojson = dl.GeoJSON(data=get_data(default_state, [2015, 2020]), id="geojson", format="geobuf",
                     zoomToBounds=True,  # when true, zooms to bounds when data changes
                     cluster=True,  # when true, data are clustered
                     clusterToLayer=ns("clusterToLayer"),  # how to draw clusters
                     zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
                     options=dict(pointToLayer=ns("pointToLayer")),  # how to draw points
                     superClusterOptions=dict(radius=150),  # adjust cluster size
                     hideout=dict(colorscale=csc_map[default_csc], colorProp=color_prop, **minmax))
# Create a colorbar.
colorbar = dl.Colorbar(colorscale=csc_map[default_csc], id="colorbar", width=20, height=150, **minmax)

app.layout = html.Div([
    header_section(),
    html.Div([
        # html.Div(
        #     children=[
        #         html.Div(id="intro-text", children=dcc.Markdown(intro_text)),
        #         html.P("Kansas City Neighborhoods"),
        #         html.Hr(),
        #         dcc.Graph(id="map", config={"responsive": True}),
        #     ],
        #     className="eight columns named-card",
        # ),
        html.Div([
        dl.Map([dl.TileLayer(), geojson, colorbar]),
        html.Div([dd_state, dd_csc],
            style={"position": "relative", "bottom": "80px", "left": "10px", "z-index": "1000", "width": "200px"})
        ], style={'height': '50vh', 'margin': "auto", "display": "block", "position": "relative"},
        className="eight columns named-card"),
        html.Div(
            children=[
                html.P(
                    'Filter by year:',
                    className="control_label"
                ),
                dcc.RangeSlider(
                    id='year_slider',
                    min=2007,
                    max=2020,
                    value=[2015, 2020],
                    className="dcc_control",
                    step=None,
                    marks={i: str(i) for i in range(2007, 2021)}
                ),
                dcc.Graph(animate=True, id='311-calls-trend')
        ], className="four columns named-card"),
    ], className="twelve columns")
],className="container twelve columns")

# =====Callbacks=====

@app.callback(
    Output('311-calls-trend', 'figure'),
    [Input('year_slider', 'value')])
def update_trends_graph(years_range):
    x = list(range(years_range[0], years_range[1] + 1))
    y = df[(df['CREATION YEAR'] <= years_range[1]) & (df['CREATION YEAR'] >=
                                                      years_range[0])].groupby(['CREATION YEAR'])['CASE ID'].count().tolist()
    return {
        'data': [dict({'x': x, 'y': y, 'type': 'bar', 'name': '311 Calls Trend'})],
        'layout': {
            'xaxis': {'range': [min(x)-1, max(x)+1]},
            'yaxis': {'range': [min(y)-100, max(y)+100]},
            'title': 'Trend of 311 Calls (Normalized)'
        }
    }

@app.callback([Output("geojson", "hideout"), Output("geojson", "data"), Output("colorbar", "colorscale"),
               Output("colorbar", "min"), Output("colorbar", "max")],
              [Input("dd_csc", "value"), Input("dd_state", "value"), Input('year_slider', 'value')])
def update(csc, state, years_range):
    csc, data, mm = json.loads(csc), get_data(state, years_range), get_minmax(state)
    hideout = dict(colorscale=csc, colorProp=color_prop, **mm)
    return hideout, data, csc, mm["min"], mm["max"]

"""
@app.callback(
    Output("map", "figure"),
    [Input("map", "clickData"), dash.dependencies.Input(
        'year_slider', 'value'), Input("cluster-data-store", "data")]
)
def update_map(region_select, years_range, ds):
    # Update map based on selectedData and stored calculation
    ctx = dash.callback_context
    # return make_base_map()
    filter_df = df[(df['CREATION YEAR'] <= years_range[1]) &
                   (df['CREATION YEAR'] >= years_range[0])]
    filter_df.drop(['SOURCE', 'DEPARTMENT', 'WORK GROUP', 'REQUEST TYPE',
                    'CATEGORY', 'TYPE', 'DETAIL', 'CREATION DATE', 'CREATION TIME',
                    'CREATION MONTH', 'CREATION YEAR', 'STATUS', 'EXCEEDED EST TIMEFRAME',
                    'CLOSED DATE', 'CLOSED MONTH', 'CLOSED YEAR', 'STREET ADDRESS',
                    'ZIP CODE', 'NEIGHBORHOOD', 'LATITUDE', 'LONGITUDE', 'COUNTY', 'CASE URL'], axis=1)

    # make df with consolidated
    stats_df = pd.DataFrame()
    # groupby call volume
    stats_df['volume'] = filter_df.groupby(['nbhid'])['CASE ID'].count()
    # groupby response time
    stats_df['avg_resp_time'] = filter_df.groupby(
        ['nbhid'])['DAYS TO CLOSE'].mean()
    stats_df = stats_df.reset_index()
    stats_df['nbhid'] = stats_df['nbhid'].map(str)

    geo_df = gpd.GeoDataFrame.from_features(
        kcnbh_geojson["features"]
    ).merge(stats_df, on="nbhid").set_index("nbhid")

    # figure = make_base_map()

    fig = px.choropleth_mapbox(geo_df,
                               geojson=geo_df.geometry,
                               locations=geo_df.index,
                               color="avg_resp_time",
                               center=dict(
                                   lon=df["LONGITUDE"].mean(),
                                   lat=df["LATITUDE"].mean(),
                               ),
                               mapbox_style="open-street-map", zoom=12)

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig
"""

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=True)
