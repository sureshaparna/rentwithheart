# Importing Libraries
import pandas as pd
import geopandas as gpd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table, Input, Output

plot_config = {"modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d", "hoverClosestCartesian", "hoverCompareCartesian"],
               "staticPlot": False, "displaylogo": False}

# Reading Data File
suburb_df = gpd.read_file("Data/suburb recommendor/VIC_LOC_GDA94/vic_localities.shp")
recommender_data = pd.read_csv(r"Data/suburb recommendor/final_suburb_recommendor_cleaned.csv")
recommender_data = recommender_data.fillna("")

# Webpage HTML
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
app.layout = html.Div(children=[
    html.P("Suburb Recommender", style={"textAlign": "center", "fontSize": "40px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),

    html.Div(children=[
        html.Div(children=[
            html.Div(children=[
                html.P("Select Preferred Housing Type", style={"fontWeight": "bold", "margin": "0px", "padding": "0px"}),
                dcc.Dropdown(id="housing_type_dropdown", searchable=False, value="1 bedroom flat",
                    options=[{"label": val.capitalize(), "value": val}
                             for val in sorted(recommender_data["Housing_Type"].unique())
                             if val != ""], style={"width": "100%"}
                )
            ]),
            html.Div(children=[
                html.P("Select Preferred Weekly Budget ($)", style={"fontWeight": "bold", "margin": "0px", "padding": "0px"}),
                dcc.Dropdown(id="budget_dropdown", searchable=False, value=400,
                    options=[{"label": f"${val} per week", "value": val}
                             for val in range(100, 1050, 100)], style={"width": "100%"}
                )
            ]),
            html.Div(children=[
                html.P("Select Required School Type", style={"fontWeight": "bold", "margin": "0px", "padding": "0px"}),
                dcc.Dropdown(id="school_dropdown", searchable=False, multi=True, value=["Primary", "Secondary", "Pri/Sec"],
                    options=[{"label": val.capitalize(), "value": val}
                             for val in recommender_data["School_Type"].unique()
                             if val != ""], style={"width": "100%"}
                )
            ])
        ], style={"height": "100%", "Width": "20%", "display": "flex", "flexDirection": "column", "justifyContent": "space-between", "gap": "auto"}),

        html.Div(id="filter_table", className="filter_table", style={"flex": "1", "overflow": "auto"})
    ], style={"height": "40vh", "display": "flex", "flexDirection": "row", "gap": "10px"}),

    html.Div(children=[
        dcc.Graph(id="map", config=plot_config, style={"height": "100%", "padding": "0", "margin": "0"})
    ], style={"flex": "1", "minHeight": "0", "width": "100%"})
], style={"display": "flex", "flexDirection": "column", "gap": "10px", "backgroundColor": "#EAE8DC", "height": "100vh", "padding": "0px 10px 10px 10px"})


@app.callback(
    Output("filter_table", "children"),
    [Input("housing_type_dropdown", "value"), Input("budget_dropdown", "value"), Input("school_dropdown", "value")]
)
def update_filter_table(housing_type, budget, school_type):
    df = recommender_data.copy()

    df["Latest_Median"] = pd.to_numeric(df["Latest_Median"])
    df = df[(df["Housing_Type"] == housing_type) & (df["Latest_Median"] <= budget)]
    if len(school_type) > 0:
        df = df[df["School_Type"].isin(list(school_type))]

    df = df[["region", "suburb", "Housing_Type", "School_Type", "school_count", "MODE", "stop_count", "Latest_Median", "Forecasted_Next_Quarter"]]
    df = df.rename(columns={"region": "Region", "suburb": "Suburb",
        "Housing_Type": "Housing Type", "School_Type": "School Type", "school_count": "No. of Schools",
        "MODE": "Mode of Transport", "stop_count": "No. of Stops",
        "Latest_Median": "Median Rent", "Forecasted_Next_Quarter": "Forecasted Rent"
    })
    df["Median Rent"] = "$" + df["Median Rent"].astype(int).astype(str)
    df["Forecasted Rent"] = "$" + df["Forecasted Rent"].astype(int).astype(str)

    fig = dash_table.DataTable(fixed_rows={"headers": True}, page_action="none",
            columns=[{"name": i, "id": i} for i in df.columns], data=df.to_dict("records"),
            style_table={"width": "100%", "maxHeight": "40vh", "overflowY": "auto", "overflowX": "auto"},
            style_header={"whiteSpace": "normal", "fontWeight": "bold", "fontSize": "14px", "textAlign": "center", "backgroundColor": "#2F4858", "color": "white"},
            style_cell={"minWidth": "150px", "width": "150px", "maxWidth": "180px", "whiteSpace": "normal", "height": "auto", "fontSize": "10px", "textAlign": "center"}
        )

    return fig


@app.callback(
    Output("map", "figure"),
    Input("housing_type_dropdown", "value")
)
def update_map(housing_type):
    df = recommender_data.copy()
    df = df[df["Housing_Type"] == housing_type]
    df = df[["suburb", "Latest_Median", "Forecasted_Next_Quarter"]]
    df = df.rename(columns={"suburb": "Suburb", "Latest_Median": "Median Rent", "Forecasted_Next_Quarter": "Forecasted Rent"})
    df = df.drop_duplicates()

    merged_df = suburb_df.merge(df, left_on="LOC_NAME", right_on="Suburb", how="inner")
    merged_df["Median Rent"] = pd.to_numeric(merged_df["Median Rent"])
    merged_df["Forecasted Rent"] = pd.to_numeric(merged_df["Forecasted Rent"])
    merged_df["id"] = merged_df.index.astype(str)

    fig = px.choropleth_map(merged_df, geojson=merged_df.__geo_interface__, locations="id", center={"lat": -37.8136, "lon": 144.9631},
        color="Median Rent", color_continuous_scale="Viridis", range_color=(merged_df["Median Rent"].min(), merged_df["Median Rent"].max()),
        hover_name="Suburb", hover_data={"Median Rent": True, "Forecasted Rent": True}, zoom=9
    )
    fig.update_coloraxes(colorbar=dict(tickprefix="$"))
    fig.update_traces(
        customdata=merged_df[["Median Rent", "Forecasted Rent"]],
        hovertemplate="<b>%{hovertext}</b><br>" +
                      "Median rent: $%{customdata[0]}/week<br>" +
                      "Forecasted rent: $%{customdata[1]}/week<extra></extra>"
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            title=dict(text="<b>Weekly Rent</b>", side="top", font=dict(color="black", size=12)),
            x=0.9, y=0.5, bgcolor="rgba(0,0,0,0)"
        )
    )
    return fig


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
