import json, os, pathlib
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx
import pandas as pd
import numpy as np
from dash_extensions.javascript import Namespace
from dash import Dash
from dash.dependencies import Input, Output

# region Data
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

def header_section():
    return html.Div(
        [
            html.Img(src=app.get_asset_url("ocelai-logo.jpg"), className="logo"),
            html.H4("311 Community Engagement - OCEL.AI")
        ],
        className="header__title",
    )

def get_data(nbhid, years_range):
    df_nbh = df[df["nbhid"] == nbhid]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (df_nbh['CREATION YEAR'] >= years_range[0])]
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
# locate control 
locate_control = dl.LocateControl(options={'locateOptions': {'enableHighAccuracy': True}})

# Create the app.
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', 'https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css']
app = Dash(__name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
    external_scripts=[chroma],
    external_stylesheets=external_stylesheets,
    prevent_initial_callbacks=False)

app.layout = html.Div([
    header_section(),
    html.Div([
        html.Div([
        dl.Map([dl.TileLayer(), geojson, colorbar, locate_control]),
        html.Div([dd_state, dd_csc],
            style={"position": "relative", "bottom": "80px", "left": "10px", "z-index": "1000", "width": "200px"})
        ], style={'height': '75vh', 'margin': "auto", "display": "block", "position": "relative"},
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
    ], className="twelve columns"),
],className="container twelve columns")

# =====Callbacks=====
@app.callback(
    Output('311-calls-trend', 'figure'),
    [Input('year_slider', 'value'), Input('dd_state', 'value')])
def update_trends_graph(years_range, nbhid):
    x = list(range(years_range[0], years_range[1] + 1))
    df_nbh = df[df["nbhid"] == int(nbhid)]  # pick one state
    y = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (df_nbh['CREATION YEAR'] >= years_range[0])].groupby(['CREATION YEAR'])['CASE ID'].count().tolist()
    print(len(y))
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
              [Input('year_slider', 'value'), Input("dd_csc", "value"), Input("dd_state", "value")])
def update(year_slider, csc, state):
    csc, data, mm = json.loads(csc), get_data(int(state), year_slider), get_minmax(int(state))
    hideout = dict(colorscale=csc, colorProp=color_prop, **mm)
    return hideout, data, csc, mm["min"], mm["max"]


if __name__ == '__main__':
    app.run_server(debug=True, threaded=True, use_reloader=True)