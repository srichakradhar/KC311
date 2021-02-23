import json
import os
import pathlib
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash_extensions.javascript import Namespace
from dash import Dash
from dash.dependencies import Input, Output, State
from dash_extensions import Download
from dash_extensions.snippets import send_data_frame
from dash_extensions.javascript import Namespace, arrow_function
from datetime import datetime

# region Data
APP_PATH = str(pathlib.Path(__file__).parent.resolve())
cols = ['CASE ID', 'SOURCE', 'DEPARTMENT', 'WORK GROUP', 'REQUEST TYPE',
        'CATEGORY', 'TYPE', 'DETAIL', 'CREATION DATE', 'CREATION TIME',
        'CREATION MONTH', 'CREATION YEAR', 'STATUS', 'EXCEEDED EST TIMEFRAME',
        'CLOSED DATE', 'CLOSED MONTH', 'CLOSED YEAR', 'DAYS TO CLOSE', 'STREET ADDRESS',
        'ZIP CODE', 'NEIGHBORHOOD', 'LATITUDE', 'LONGITUDE', 'COUNTY', 'CASE URL', 'nbh_id', 'nbh_name']
# df = pd.concat([pd.read_csv(os.path.join(APP_PATH, os.path.join("data", nbh)), usecols=cols)
#                 for nbh in os.listdir(os.path.join(APP_PATH, "data")) if nbh.endswith('.csv')])
df = pd.read_csv(os.path.join(APP_PATH, os.path.join("data", "Merged-311_Calls_2007-2020-1497400.csv")))
df.rename(columns={'nbh_id': 'nbhid'}, inplace=True)
df = df[df['nbhid'].isin([76, 89, 118, 93])]
response_range = df.groupby('nbhid')['DAYS TO CLOSE'].agg('mean').to_dict()
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

months = ["NA",
          "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def header_section():
    return html.Div(
        [
            html.Img(src=app.get_asset_url("SCC-Logo.png"), className="logo"),
            html.H4("SCC - 311 Community Engagement"),
            html.Div([html.Hr()]),
        ],
        className="header__title",
    )


def get_data(nbds, years_range):
    df_nbh = df[df["nbhid"].isin(nbds)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1])
                    & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh = df_nbh[['LATITUDE', 'LONGITUDE', 'NEIGHBORHOOD',
                     'DAYS TO CLOSE']]  # use only relevant columns
    dicts = df_nbh.to_dict('rows')
    for item in dicts:
        item["tooltip"] = "{:.1f}".format(item[color_prop])  # bind tooltip
        item["popup"] = item["NEIGHBORHOOD"]  # bind popup
    geojson = dlx.dicts_to_geojson(
        dicts, lat="LATITUDE", lon="LONGITUDE")  # convert to geojson
    geobuf = dlx.geojson_to_geobuf(geojson)  # convert to geobuf
    return geobuf


def get_minmax(nbds):
    max_range = 0
    for nbd in nbds:
        max_range = max(max_range, response_range[int(nbd)])
    return dict(min=0, max=max_range * 2)


with open(os.path.join(APP_PATH, os.path.join("assets", 'KCNeighborhood.json'))) as f:
    geojson_data = json.loads(f.read())


def get_outline_data(years_range):
    df_nbh = df[(df['CREATION YEAR'] <= years_range[1])
                & (df['CREATION YEAR'] >= years_range[0])]
    volumes = df_nbh.groupby(['nbhid'])['CASE ID'].count().to_dict()
    outline_data = geojson_data.copy()
    for i in range(len(outline_data['features'])):
        nbhid = int(outline_data['features'][i]['properties']['nbhid'])
        nbhname = outline_data['features'][i]['properties']['nbhname']
        if nbhid in volumes:
            outline_data['features'][i]['properties']['volume'] = int(
                volumes[nbhid])
            
        outline_data['features'][i]['properties']["tooltip"] = nbhname
        # bind popup
        outline_data['features'][i]['properties']["popup"] = geojson_data['features'][i]['properties']['nbhname']
    # geojson_data = dlx.geojson_to_geobuf(geojson_data)  # convert to geobuf
    return outline_data, min(volumes.values()), max(volumes.values())


# Setup a few color scales.
csc_map = {"Rainbow": ['red', 'yellow', 'green', 'blue', 'purple'],
           "Hot": ['yellow', 'red', 'black'],
           "Viridis": "Viridis"}
csc_options = [dict(label=key, value=json.dumps(csc_map[key]))
               for key in csc_map]
default_csc = "Hot"
dd_csc = dcc.Dropdown(options=csc_options, value=json.dumps(
    csc_map[default_csc]), id="dd_csc", clearable=False)
# Setup state options.
states = [state for state in df["nbhid"].unique() if state != 0]
state_names = df.groupby('nbhid').first()['nbh_name'].dropna().to_dict()
state_options = [dict(label=state_names[state], value=state) for state in states]
default_state = ["76"]
dd_state = dcc.Dropdown(options=state_options,
                        value=default_state, id="dd_state", clearable=False, multi=True)

# endregion

minmax = get_minmax(default_state)
# Create geojson.
ns = Namespace("dlx", "scatter")
geojson = dl.GeoJSON(data=get_data(default_state, [2015, 2020]), id="geojson", format="geobuf",
                     zoomToBounds=False,  # when true, zooms to bounds when data changes
                     cluster=True,  # when true, data are clustered
                     # how to draw clusters
                     clusterToLayer=ns("clusterToLayer"),
                     # when true, zooms to bounds of feature (e.g. cluster) on click
                     zoomToBoundsOnClick=False,
                     # how to draw points
                     options=dict(pointToLayer=ns("pointToLayer")),
                     superClusterOptions=dict(
                         radius=150),  # adjust cluster size
                     hideout=dict(colorscale=csc_map[default_csc], colorProp=color_prop, **minmax))
# Create a colorbar.
colorbar = dl.Colorbar(tooltip=True,
    colorscale=csc_map[default_csc], id="colorbar", width=20, height=150, **minmax)
# locate control
locate_control = dl.LocateControl(
    options={'locateOptions': {'enableHighAccuracy': True}})

# Create the app.
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css',
                        'https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css']
app = Dash(__name__,
           meta_tags=[
               {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
           ],
           external_scripts=[chroma],
           external_stylesheets=external_stylesheets,
           prevent_initial_callbacks=False)
server = app.server

keys = ["watercolor", "toner", "terrain"]
url_template = "http://{{s}}.tile.stamen.com/{}/{{z}}/{{x}}/{{y}}.png"
attribution = 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, ' \
              '<a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data ' \
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

"""
dl.Map([dl.TileLayer(), geojson, colorbar, locate_control, dl.LayersControl(
            [dl.BaseLayer(dl.TileLayer(url=url_template.format(key), attribution=attribution),
                        name=key, checked=key == "terrain") for key in keys]
        )]),
"""

# Mapbox setup
mapbox_url = "https://api.mapbox.com/styles/v1/mapbox/{id}/tiles/{{z}}/{{x}}/{{y}}{{r}}?access_token={access_token}"
mapbox_token = "pk.eyJ1Ijoic3JpY2hha3JhZGhhciIsImEiOiJja2lqZXh6aTYwMjE4MndvOG5iZGUzZ2hkIn0.j6cqd-ISDEhuvAyIRb0mDA"
mapbox_ids = ["light-v9", "dark-v9", "streets-v9",
              "outdoors-v9", "satellite-streets-v9"]

MAP_ID = "map-id"
BASE_LAYER_ID = "base-layer-id"
BASE_LAYER_DROPDOWN_ID = "base-layer-drop-down-id"
COORDINATE_CLICK_ID = "coordinate-click-id"

"""
dl.Map(children=[dl.TileLayer(id=BASE_LAYER_ID),geojson, colorbar, locate_control, dl.LayersControl(
                [dl.BaseLayer(dl.TileLayer(url=mapbox_url.format(id=key, access_token=mapbox_token)),
                              name=key, checked=key == "satellite-streets-v9") for key in mapbox_ids]
            )], id=MAP_ID),
"""

# ESri
esri_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/{variant}/MapServer/tile/{{z}}/{{y}}/{{x}}'
variants = {'DeLorme': {'attribution': 'Tiles &copy; Esri &mdash; Copyright: '
                        '&copy;2012 DeLorme',
                        'maxZoom': 11,
                        'minZoom': 1,
                        'variant': 'Specialty/DeLorme_World_Base_Map'},
            'NatGeoWorldMap': {'attribution': 'Tiles &copy; Esri &mdash; '
                               'National Geographic, Esri, '
                               'DeLorme, NAVTEQ, UNEP-WCMC, '
                               'USGS, NASA, ESA, METI, NRCAN, '
                               'GEBCO, NOAA, iPC',
                               'maxZoom': 16,
                               'variant': 'NatGeo_World_Map'},
            'OceanBasemap': {'attribution': 'Tiles &copy; Esri &mdash; '
                             'Sources: GEBCO, NOAA, CHS, OSU, '
                             'UNH, CSUMB, National Geographic, '
                             'DeLorme, NAVTEQ, and Esri',
                             'maxZoom': 13,
                             'variant': 'Ocean_Basemap'},
            'WorldGrayCanvas': {'attribution': 'Tiles &copy; Esri &mdash; '
                                'Esri, DeLorme, NAVTEQ',
                                'maxZoom': 16,
                                'variant': 'Canvas/World_Light_Gray_Base'},
            'WorldImagery': {'attribution': 'Tiles &copy; Esri &mdash; '
                             'Source: Esri, i-cubed, USDA, '
                             'USGS, AEX, GeoEye, Getmapping, '
                             'Aerogrid, IGN, IGP, UPR-EGP, and '
                             'the GIS User Community',
                             'variant': 'World_Imagery'},
            'WorldPhysical': {'attribution': 'Tiles &copy; Esri &mdash; '
                              'Source: US National Park '
                              'Service',
                              'maxZoom': 8,
                              'variant': 'World_Physical_Map'},
            'WorldShadedRelief': {'attribution': 'Tiles &copy; Esri &mdash; '
                                  'Source: Esri',
                                  'maxZoom': 13,
                                  'variant': 'World_Shaded_Relief'},
            'WorldTerrain': {'attribution': 'Tiles &copy; Esri &mdash; Source: USGS, Esri, TANA, DeLorme, and NPS',
                             'maxZoom': 13,
                             'variant': 'World_Terrain_Base'},
            'WorldTopoMap': {'attribution': 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community',
                             'variant': 'World_Topo_Map'}}


def get_info(feature=None):
    header = [html.H4("KCMO 311 Calls")]
    if not feature:
        return header + ["Hover over a Neighborhood"]
    return header + [html.B(feature["properties"]["nbhname"]), " (", feature["properties"]["nbhid"],
                     ")", html.Br(), feature["properties"].get("volume", 0), " Calls"]


classes = [0, 100, 200, 500, 1000, 2000, 5000, 10000]
colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
              '#FC4E2A', '#E31A1C', '#BD0026', '#800026']
style = dict(weight=2, opacity=1, color='white',
             dashArray='3', fillOpacity=0.7)
# Create colorbar.
ctg = ["{}+".format(cls, classes[i + 1])
       for i, cls in enumerate(classes[:-1])] + ["{}+".format(classes[-1])]
nbd_colorbar = dlx.categorical_colorbar(
    id="outline_colorbar", categories=ctg, colorscale=colorscale, width=300, height=30, position="bottomright")
with open('assets/us-states.json') as f:
    us_states = json.loads(f.read())
# Create info control.
info = html.Div(children=get_info(), id="info", className="info",
                style={"position": "absolute", "bottom": "80px", "right": "10px", "z-index": "1000"})

ns = Namespace("dlx", "choropleth")
outline_data, outline_min, outline_max = get_outline_data([2015, 2020])
app.layout = html.Div([
    header_section(),
    html.Div([
        html.Div([
            dl.Map(children=[dl.TileLayer(id=BASE_LAYER_ID), geojson,
            # dl.GeoJSON(data=us_states,
            #     # url=app.get_asset_url("us-states.json"),  # url to geojson file
            #          options=dict(style=ns("style")),  # how to style each polygon
            #          zoomToBounds=True,  # when true, zooms to bounds when data changes (e.g. on load)
            #          zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. polygon) on click
            #          hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')),  # style applied on hover
            #          hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="density"),
            #          id="geojson_test"),
            dl.GeoJSON(
                # url=app.get_asset_url('KCNeighborhood.json'),
                data=outline_data, id="outlines",
                options=dict(style=ns("style")),  # how to style each polygon
                # when true, zooms to bounds when data changes (e.g. on load)
                # zoomToBounds=True,
                # when true, zooms to bounds of feature (e.g. polygon) on click
                zoomToBoundsOnClick=False,
                # style applied on hover
                hoverStyle=arrow_function(
                    dict(weight=5, color='#666', dashArray='')),
                hideout=dict(colorscale=colorscale, classes=list(range(
                    outline_min, outline_max, (outline_max - outline_min) // 5)), style=style, colorProp="volume"),
            ), locate_control, dl.LayersControl(
                [dl.BaseLayer(dl.TileLayer(url=esri_url.format(variant=variants[key]['variant']), attribution=variants[key]['attribution']),
                              name=key, checked=key == "World_Terrain_Base") for key in variants]
            ), colorbar, nbd_colorbar, info], zoom=11, center=(39.1, -94.5786)),
            html.Div([dd_state],
                     style={"position": "relative", "bottom": "80px", "right": "10px", "z-index": "1000", "width": "300px"}),
            # html.Div(id="nbd-select-list",
            #     style={"position": "absolute", "bottom": "180px", "right": "10px", "z-index": "1000"})
        ], style={'height': '75vh', 'margin': "auto", "display": "block", "position": "relative"},
            className="eight columns named-card"),
        html.Div(id='nbd-selected', style={'display': 'none'}),
        html.Div(
            children=[
                dcc.RangeSlider(
                    id='year_slider',
                    min=2007,
                    max=2020,
                    value=[2015, 2020],
                    className="dcc_control",
                    step=None,
                    marks={i: str(i) for i in range(2007, 2021)}
                ),
                dcc.RangeSlider(
                    id='month_slider',
                    min=1,
                    max=12,
                    value=[1, 12],
                    className="dcc_control",
                    step=None,
                    marks={i: months[i] for i in range(1, 13)}
                ),
                dcc.Graph(animate=True, id='311-calls-trend'),
                html.Div([html.Button("Download", id="download_btn"),
                          Download(id="download")]),
            ], className="four columns named-card"),
    ], className="twelve columns"),
    html.Div([
        html.Div(children=[
            dcc.Graph(id='nbh_radar', className="four columns"),
            dcc.Graph(animate=True, id='311-calls-deps',
                      className="eight columns")
        ], className="eight columns named-card"),
        dcc.Graph(animate=True, id='311-calls-types', className="four columns")
    ], className="twelve columns"),
], className="container twelve columns")

# =====Callbacks=====

default_nbd_id = 76

@app.callback(
    Output('311-calls-trend', 'figure'),
    [Input('year_slider', 'value'), Input('month_slider', 'value'), Input('outlines', 'click_feature'),
    State('nbd-selected', 'children')])
def update_trends_graph(years_range, months_range, nbd_feature, nbds):
    x = list(range(years_range[0], years_range[1] + 1))
    nbds = json.loads(nbds) if nbds else [default_nbd_id]
    df_nbh = df[df["nbhid"].isin(nbds)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1])
                    & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh = df_nbh[(df_nbh['CREATION MONTH'] <= months_range[1])
                    & (df_nbh['CREATION MONTH'] >= months_range[0])]
    y = df_nbh.groupby(['CREATION YEAR'])['CASE ID'].count().tolist()
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
    [Input('year_slider', 'value'), Input('month_slider', 'value'), State('nbd-selected', 'children')])
def update_departments_graph(years_range, months_range, nbds):
    years = list(range(years_range[0], years_range[1] + 1))
    nbds = json.loads(nbds) if nbds else [default_nbd_id]
    df_nbh = df[df["nbhid"].isin(nbds)]  # filter chosen states
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1])
                    & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh = df_nbh[(df_nbh['CREATION MONTH'] <= months_range[1])
                    & (df_nbh['CREATION MONTH'] >= months_range[0])]
    df_nbh_deps = df_nbh.groupby(['DEPARTMENT', 'CREATION YEAR'])[
        ['CASE ID']].count()
    df_nbh_deps.rename(columns={'CASE ID': 'count'}, inplace=True)
    dep_counts = df_nbh_deps.groupby(level=0).apply(
        lambda df: df.xs(df.name).to_dict()).to_dict()
    fig = []
    max_count = 0
    for ind, dep in enumerate(dep_counts):
        counts = list(dep_counts[dep]['count'].values())
        max_count = max(max_count, max(counts))
        fig.append(
            go.Scatter(
                x=years,
                y=counts,
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
            xaxis=dict(title="Year", range=[years[0], years[-1]]),
            yaxis=dict(title="Call Volume", range=[0, max_count + 10]),
            hovermode="closest"
        )
    }


@app.callback(
    Output('311-calls-types', 'figure'),
    [Input('year_slider', 'value'), Input('month_slider', 'value'), State('nbd-selected', 'children')])
def update_types_graph(years_range, months_range, nbds):
    years = list(range(years_range[0], years_range[1] + 1))
    nbds = json.loads(nbds) if nbds else [default_nbd_id]
    df_nbh = df[df["nbhid"].isin(nbds)]  # pick chosen states
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1])
                    & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh = df_nbh[(df_nbh['CREATION MONTH'] <= months_range[1])
                    & (df_nbh['CREATION MONTH'] >= months_range[0])]
    bins = [2007, 2011, 2016, 2020]
    types_df = df_nbh.groupby(['CATEGORY', pd.cut(df_nbh['CREATION YEAR'], bins)])[
        ['CASE ID']].count().unstack().fillna(0).astype(int)
    types_df = types_df.rename(columns=str).reset_index().set_index('CATEGORY')
    types_df['total'] = types_df.sum(axis=1)
    types_df = types_df.nlargest(10, 'total')
    max_count = types_df['total'].max()
    types_df.drop('total', axis=1, inplace=True)
    types_df.columns = ['2007 - 2010', '2011 - 2015', '2016 - 2020']
    type_counts = types_df.groupby(level=0).apply(
        lambda df: df.xs(df.name).to_dict()).to_dict()
    fig = go.Figure()
    count_percentages = [[type_counts[req_type][year_bin]
                          for year_bin in types_df.columns] for req_type in type_counts]
    for i in range(len(type_counts)):
        counts_sum = sum(count_percentages[i])
        count_percentages[i] = [count_percentages[i][j] * 100 /
                                (counts_sum + 1) for j in range(len(count_percentages[i]))]

    for ind, year_bin in enumerate(types_df.columns):
        fig.add_trace(go.Bar(
            x=[count_percentages[j][ind] for j in range(len(type_counts))],
            y=list(type_counts.keys()),
            name=year_bin,
            orientation='h',
            marker=dict(
                color=geo_colors[ind],
                line=dict(color=geo_colors[ind], width=3)
            )
        ))

    fig.update_layout(barmode='stack',
                      title=dict(text="Top Request Types - Composition"),
                      #  yanchor="bottom", y=0.2),
                      xaxis=dict(title="Percentage of requests(%)", side='bottom',
                                 range=[0, 100]),
                      yaxis=dict(title="Request Types"),
                      showlegend=True,
                      #   legend=dict(
                      #       yanchor="bottom",
                      #       y=-0.99,
                      #       xanchor="right",
                      #       x=0.99
                      #   ),
                      #   margin=dict(l=0, t=10, b=0, r=0)
                      )
    return fig


@app.callback([Output("geojson", "hideout"), Output("geojson", "data"), Output("colorbar", "colorscale"),
               Output("colorbar", "min"), Output("colorbar", "max"),
               Output("outlines", "hideout"), Output("outlines", "data"), Output('nbd-selected', 'children')],
              #    Output("outline_colorbar", "categories")],
              [Input('year_slider', 'value'), Input('outlines', 'click_feature'), State('nbd-selected', 'children')])
def update_map(year_slider, nbd_feature, nbds):
    nbds = list(map(int, json.loads(nbds))) if nbds else [default_nbd_id]
    if nbd_feature:
        nbds.append(int(nbd_feature['properties']['nbhid']))
    else:
        nbds = [default_nbd_id]
    csc, data, mm = csc_map[default_csc], get_data(
        nbds, year_slider), get_minmax(nbds)
    outline_data, outline_min, outline_max = get_outline_data(year_slider)
    classes = list(range(outline_min, outline_max,
                         (outline_max - outline_min) // 5))
    hideout = dict(colorscale=csc, colorProp=color_prop, **mm)
    outline_hideout = dict(colorscale=colorscale,
                           classes=classes, style=style, colorProp="volume")
    # ctg =  ["{}+".format(cl, classes[i + 1]) for i, cl in enumerate(classes[:-1])] + ["{}+".format(classes[-1])]
    return hideout, data, csc, mm["min"], mm["max"], outline_hideout, outline_data, json.dumps(nbds)


@app.callback(Output("info", "children"), [Input("outlines", "hover_feature")])
def info_hover(feature):
    return get_info(feature)


@app.callback(Output("nbh_radar", "figure"),
              [Input('year_slider', 'value'), State('nbd-selected', 'children')])
def update_radar_hours(years_range, nbds):
    nbds = json.loads(nbds) if nbds else [default_nbd_id]
    df_nbh = df[df["nbhid"].isin(nbds)]  # pick one state
    df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1])
                    & (df_nbh['CREATION YEAR'] >= years_range[0])]
    df_nbh['hour'] = df_nbh['CREATION TIME'].map(
        lambda d: datetime.strptime(d, '%I:%M %p').hour)
    frequencies = df_nbh.groupby(['hour'])['CASE ID'].count().tolist()
    fig = go.Figure(data=go.Scatterpolar(
        r=frequencies,
        theta=list(map(str, range(24))),
        mode='lines',
        fill='toself',
        name='Calls by Hour',
    ))

    fig.update_layout(
        title='Calls round the clock',
        polar=dict(
            radialaxis_angle=90,
            radialaxis=dict(
                visible=True
            ),
            angularaxis=dict(
                rotation=90,  # start position of angular axis
                direction="clockwise"
            )
        ),
        template="plotly_dark"
    )

    return fig


@app.callback(Output("download", "data"), [Input("download_btn", "n_clicks"), State('year_slider', 'value'), State('nbd-selected', 'children')])
def download(n_clicks, years_range, nbds):
    if n_clicks:
        nbds = json.loads(nbds) if nbds else [default_nbd_id]
        df_nbh = df[df["nbhid"].isin(nbds)]  # filter chosen states
        nbhname = df_nbh['nbh_name'].iloc[0]
        df_nbh = df_nbh[(df_nbh['CREATION YEAR'] <= years_range[1]) & (
            df_nbh['CREATION YEAR'] >= years_range[0])]
        return send_data_frame(df_nbh.to_csv, "".join(["kc311_", "_".join(nbds), '_', nbhname, '_',
                                                       str(years_range[0]), '-', str(years_range[1]), ".csv"]), index=False)


if __name__ == '__main__':
    # app.run_server(debug=True, threaded=True, use_reloader=True)
    app.run_server(port=8000, host="0.0.0.0")
