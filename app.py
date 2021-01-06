import json, os, pathlib
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash_extensions.javascript import Namespace
from dash import Dash
from dash.dependencies import Input, Output
from datetime import datetime

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
geo_colors = [
    "#8dd3c7",
    "#ffd15f",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
]

bar_coloway = [
    "#fa4f56",
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
]
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
server = app.server

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
    html.Div([
        html.Div(children=[
            dcc.Graph(id='nbh_radar', className="four columns"),
            dcc.Graph(animate=True, id='311-calls-deps', className="eight columns")
        ], className="eight columns named-card"),
        dcc.Graph(animate=True, id='311-calls-types', className="four columns")
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
    return {
        'data': [dict({'x': x, 'y': y, 'type': 'bar', 'name': '311 Calls Trend'})],
        'layout': {
            'xaxis': {'title': 'Year', 'range': [min(x)-1, max(x)+1]},
            'yaxis': {'title': 'Call Volume', 'range': [min(y)-100, max(y)+100]},
            'title': 'Trend of 311 Calls (Normalized)'
        }
    }


@app.callback(
    Output('311-calls-deps', 'figure'),
    [Input('year_slider', 'value'), Input('dd_state', 'value')])
def update_departments_graph(years_range, nbhid):
    years = list(range(years_range[0], years_range[1] + 1))
    df_nbh = df[df["nbhid"] == int(nbhid)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh_deps = df_nbh.groupby(['DEPARTMENT', 'CREATION YEAR'])[['CASE ID']].count()
    df_nbh_deps.rename(columns={'CASE ID': 'count'}, inplace=True)
    dep_counts = df_nbh_deps.groupby(level=0).apply(lambda df: df.xs(df.name).to_dict()).to_dict()
    fig = []
    for ind, dep in enumerate(dep_counts):
        fig.append(
            go.Scatter(
                x=years,
                y=list(dep_counts[dep]['count'].values()),
                name=dep,
                mode="markers+lines",
                hovertemplate="<b>" + dep + ": </b> %{y}",
                marker=dict(
                    size=12,
                    opacity=0.8,
                    color=geo_colors[ind % len(geo_colors)],
                    line=dict(width=1, color="#ffffff"),
                ),
            )
        )
    
    return {
        'data': fig,
        "layout": dict(
            title='311 Calls by Department',
            xaxis=dict(title="Year"),
            yaxis=dict(title="Call Volume"),
            hovermode="closest"
        )
    }

@app.callback(
    Output('311-calls-types', 'figure'),
    [Input('year_slider', 'value'), Input('dd_state', 'value')])
def update_types_graph(years_range, nbhid):
    years = list(range(years_range[0], years_range[1] + 1))
    df_nbh = df[df["nbhid"] == int(nbhid)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (df_nbh['CREATION YEAR'] >= years_range[0])]
    bins = [2007, 2011, 2016, 2020]
    types_df = df_nbh.groupby(['TYPE', pd.cut(df_nbh['CREATION YEAR'], bins)])[['CASE ID']].count().unstack().fillna(0).astype(int)
    types_df = types_df.rename(columns=str).reset_index().set_index('TYPE')
    types_df['total'] = types_df.sum(axis=1)
    types_df = types_df.nlargest(10, 'total')
    max_count = types_df['total'].max()
    types_df.drop('total', axis=1, inplace=True)
    types_df.columns = ['2007 - 2010', '2011 - 2015', '2016 - 2020']
    type_counts = types_df.groupby(level=0).apply(lambda df: df.xs(df.name).to_dict()).to_dict()
    fig = go.Figure()
    for ind, req_type in enumerate(type_counts):
        fig.add_trace(go.Bar(
            x=list(type_counts[req_type].values()),
            y=types_df.columns,
            name=req_type,
            orientation='h',
            marker=dict(
                color=bar_coloway[ind],
                line=dict(color=bar_coloway[ind], width=3)
            )
        ))

    fig.update_layout(barmode='stack',
    title=dict(text="Top Complaint Types - Composition", yanchor="bottom", y=0.2),
    xaxis=dict(title="Complaints", side='top', range=[0, max_count]),
    yaxis=dict(title="Period (bins)"),
    showlegend=True,
    legend=dict(
        yanchor="bottom",
        y=-0.99,
        xanchor="right",
        x=0.99
    ),
    margin=dict(l=0, t=10, b=0, r=0)
    )
    return fig

@app.callback([Output("geojson", "hideout"), Output("geojson", "data"), Output("colorbar", "colorscale"),
               Output("colorbar", "min"), Output("colorbar", "max")],
              [Input('year_slider', 'value'), Input("dd_csc", "value"), Input("dd_state", "value")])
def update_map(year_slider, csc, state):
    csc, data, mm = json.loads(csc), get_data(int(state), year_slider), get_minmax(int(state))
    hideout = dict(colorscale=csc, colorProp=color_prop, **mm)
    return hideout, data, csc, mm["min"], mm["max"]

@app.callback(Output("nbh_radar", "figure"),
              [Input('year_slider', 'value'), Input("dd_state", "value")])
def update_radar_hours(years_range, nbhid):
    df_nbh = df[df["nbhid"] == int(nbhid)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh['hour'] = df_nbh['CREATION TIME'].map(lambda d: datetime.strptime(d, '%I:%M %p').hour)
    frequencies = df_nbh.groupby(['hour'])['CASE ID'].count().tolist()
    fig = go.Figure(data=go.Scatterpolar(
    r=frequencies,
    theta=list(map(str, range(24))),
    mode='lines',
    fill='toself',
    name='Calls by Hour',
    ))

    fig.update_layout(
    title = 'Calls round the clock',
    polar=dict(
        radialaxis_angle = 90,
        radialaxis=dict(
        visible=True
        ),
        angularaxis = dict(
        rotation=90, # start position of angular axis
        direction="clockwise"
        )
    ),
    template="plotly_dark"
    )

    return fig


if __name__ == '__main__':
    # app.run_server(debug=True, threaded=True, use_reloader=True)
    app.run_server()