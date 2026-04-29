# Importing Libraries
import math
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from statsmodels.tsa.statespace.sarimax import SARIMAX

plot_config = {"modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d", "hoverClosestCartesian", "hoverCompareCartesian"],
               "staticPlot": False, "displaylogo": False}

# Reading Data File
historical_data = pd.read_csv(r"data/historical forcast/historical_forcast_cleaned.csv")
historical_data["Median"] = pd.to_numeric(historical_data["Median"])
historical_data["Count"] = pd.to_numeric(historical_data["Count"])
historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"])


# Webpage HTML
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
app.layout = html.Div(children=[
    html.P("Historical Trends & Forecast", style={"textAlign": "center", "fontSize": "40px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),

    html.Div(children=[
        html.Div([
            html.P("Select Preferred Suburb", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="suburb_dropdown", searchable=True, value="Clayton",
                options=[{'label': val.capitalize(), 'value': val} for val in sorted(historical_data["suburb"].unique())]),
        ], style={"width": "100%"}),
        html.Div([
            html.P("Select Housing Type", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="housing_type_dropdown", searchable=False, value=historical_data["type"].unique()[0],
                options=[{'label': val.capitalize(), 'value': val} for val in sorted(historical_data["type"].unique())]
            )
        ], style={"width": "100%"}),
        html.Div([
            html.P("Select Victorian Region", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="region_dropdown", searchable=False, value="Inner Eastern Melbourne",
                options=[{'label': val.capitalize(), 'value': val} for val in historical_data["region"].unique()]
            )
        ], style={"width": "100%"})
    ], style={"display": "flex", "flexDirection": "row", "alignItems": "center", "justifyContent": "space-around", "gap": "30px", "margin": "10px 30px"}),

    html.Div(children=[
        dcc.Graph(id="historical_trend_graph", config=plot_config, style={"height": "100%", "width": "100%", "flex": 2}),
        dcc.Graph(id="forcasted_graph", config=plot_config, style={"height": "100%", "width": "100%", "flex": 1})
    ], style={
        "height": "calc(100% - 10px)", "flex": 1, "display": "flex", "flexDirection": "row", "alignItems": "stretch",
        "justifyContent": "space-around", "gap": "15px", "margin": "10px 15px"
    })

], style={"display": "flex", "flexDirection": "column", "backgroundColor": "#EAE8DC", "height": "100vh", "paddingBottom": "10px", "overflow": "hidden"})


@app.callback(
    Output("historical_trend_graph", "figure"),
    [Input("housing_type_dropdown", "value"), Input("suburb_dropdown", "value")]
)
def update_historical_trend(housing_type_value, suburb_value):
    df = historical_data[(historical_data["type"] == housing_type_value) & (historical_data["suburb"] == suburb_value)]

    df["DateLabel"] = df["timestamp"].dt.strftime("%b-%Y")
    df = df.sort_values("timestamp")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=df["DateLabel"], y=df["Count"], name="Leases Alloted", opacity=0.7)
    )
    fig.add_trace(
        go.Scatter(x=df["DateLabel"], y=df["Median"], name="Median Rental Yield", mode="lines+markers", yaxis="y2")
    )
    fig.update_layout(
        title=f"How Rental Yield and Lease Activity Have Evolved for <br><b>{housing_type_value.capitalize()}'s</b> in <b>{suburb_value.capitalize()}</b>",
        yaxis=dict(title="Leases Allotted"),
        yaxis2=dict(title="Median Rental Yield", overlaying="y", side="right"),
        template="simple_white",
        legend=dict(orientation="v", x=1.1, y=1.15, xanchor="right", yanchor="top")
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


@app.callback(
    Output("region_dropdown", "value"),
    Input("suburb_dropdown", "value")
)
def update_region_dropdown(suburb_value):
    df = historical_data[historical_data["suburb"] == suburb_value]
    return df["region"].unique()[0]


@app.callback(
    Output("forcasted_graph", "figure"),
    [Input("housing_type_dropdown", "value"), Input("region_dropdown", "value")]
)
def update_forcasted_graph(housing_type_value, region_value):
    df = historical_data[(historical_data["type"] == housing_type_value) & (historical_data["region"] == region_value)]

    results = []
    for suburb in sorted(df["suburb"].unique()):
        sub_df = df[df["suburb"] == suburb]
        sub_df = sub_df.sort_values(["timestamp"])

        y = sub_df["Median"].values

        if len(y) < 6:
            results.append({"suburb": suburb, "forecast_change": 0})
            continue

        model = SARIMAX(y, order=(1, 1, 0), seasonal_order=(0, 0, 0, 0), enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False, maxiter=200)
        forecast = fit.get_forecast(steps=1).predicted_mean

        next_quarter_forecast = forecast[0]
        last_actual = y[-1]
        pct_change = ((next_quarter_forecast - last_actual) / last_actual) * 100

        results.append({"suburb": suburb, "forecast_change": pct_change})

    suburb_df = pd.DataFrame(results)
    suburb_df["plot_value"] = suburb_df["forecast_change"].apply(lambda x: 0.1 if abs(x) < 0.05 else x)

    colors = [
        "green" if change > 0 else
        "red" if change < 0 else
        "gray"
        for change in suburb_df["forecast_change"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=suburb_df["plot_value"],
            y=suburb_df["suburb"],
            orientation="h",
            marker=dict(color=colors, opacity=0.7),
            customdata=suburb_df["forecast_change"],
            hovertemplate="%{y}<br>Change: %{customdata:.2f}%<extra></extra>"
        )
    )

    fig.update_layout(
        title=f"Forecasted Median Rental Price Change of <br><b>{housing_type_value}'s</b> in <br><b>{region_value}</b>",
        xaxis=dict(
            title="Forecasted Change (%) of Rent",
            range=[math.floor(suburb_df["forecast_change"].min()), math.ceil(suburb_df["forecast_change"].max())]
        ),
        yaxis=dict(title="Suburb"),
        template="simple_white"
    )

    return fig


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0")
