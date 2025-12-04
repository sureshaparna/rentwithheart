#Importing Libraries
import pandas as pd
import geopandas as gpd
import plotly.express as px
from plotly.express import data
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, dash_table, Input, Output
from flask import Flask, render_template
from statsmodels.tsa.statespace.sarimax import SARIMAX


plot_config = {"modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d", "hoverClosestCartesian", "hoverCompareCartesian"],
               "staticPlot": False, "displaylogo": False}

#Reading Data File
suburb_df = gpd.read_file("data/suburb recommendor/VIC_LOC_GDA94/vic_localities.shp")
recommender_data = pd.read_csv(r"data/suburb recommendor/final_suburb_recommendor_cleaned.csv")
recommender_data = recommender_data.fillna("")

historical_data = pd.read_csv(r"data/historical forcast/historical_forcast_cleaned.csv")
data = pd.read_csv(r"data/support_charity.csv")
data["inside_vic"] = data["State"].apply(lambda x: "Only Victorian support organisations" if x in ['Victoria', 'VIC','Vic', 'victoria', 'St Helena Victoria', 'VICTORIA', 'Benalla Victoria', 'vic' 'Victoria,', 'VIC ', 'Victora'] else "Support organisations that operate across Australia including Victoria")


# MAIN APP
main_app = Flask(__name__, template_folder='templates', static_folder='static')

@main_app.route('/')
def home():
    return render_template('home.html')

@main_app.route('/recommender')
def recommender():
    return render_template('recommender.html')

@main_app.route('/procedure')
def procedure():
    return render_template('procedure.html')

@main_app.route('/suburb/<int:Number>')
def suburb_historicaldata(Number):
    if (Number > 0) and (Number <= 7):
        return render_template(f'historical_trends/subdat{str(Number)}.html')
    else:
        return render_template('suburb_forecast.html')

@main_app.route('/support')
def support():
    return render_template('support.html')


# Suburb Recommender APP
suburb_recommender_app = Dash(__name__, server=main_app, url_base_pathname='/suburb_recommender/', external_stylesheets=[dbc.themes.FLATLY])
suburb_recommender_app.layout = html.Div(children=[
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
        ], style={"height": "100%", "maxWidth": "20%", "minWidth": "20%", "display": "flex", "flexDirection": "column", "justifyContent": "space-between", "gap": "auto"}),

        html.Div(children=[
            dash_table.DataTable(id="filter_table", fixed_rows={"headers": True}, page_action="none",
                style_table={"width": "100%", "overflowY": "scroll"},
                style_header={"whiteSpace": "normal", "fontWeight": "bold", "fontSize": "14px", "textAlign": "center"},
                style_cell={"minWidth": "150px", "width": "150px", "maxWidth": "180px",
                            "whiteSpace": "normal", "height": "auto", "fontSize": "10px", "textAlign": "center"}
            )
        ], style={"flex": "1", "height": "100%", "overflow": "hidden"})
    ], style={"height": "calc(100vh - 50vh - 40px - 50px)", "display": "flex", "flexDirection": "row", "gap": "10px"}),

    html.Div(children=[
        dcc.Graph(id="map", config=plot_config, style={"height": "50vh", "width": "100%", "padding": "0", "margin": "0"})
    ], style={"width": "100%"})
], style={"display": "flex", "flexDirection": "column", "gap": "10px", "backgroundColor": "#EAE8DC", "minHeight": "100vh", "padding": "0px 10px 10px 10px"})

@suburb_recommender_app.callback(
    [Output("filter_table", "columns"), Output("filter_table", "data")],
    [Input("housing_type_dropdown", "value"), Input("budget_dropdown", "value"), Input("school_dropdown", "value")]
)
def update_filter_table(housing_type, budget, school_type):
    df = recommender_data.copy()
    df["Latest_Median"] = pd.to_numeric(df["Latest_Median"])

    df = df[(df["Housing_Type"] == housing_type) & (df["Latest_Median"] <= budget) & (df["School_Type"].isin(list(school_type)))]
    df = df[["region", "suburb", "Housing_Type", "School_Type", "school_count", "MODE", "stop_count", "Latest_Median", "Forecasted_Next_Quarter"]]
    df = df.rename(columns={"region": "Region", "suburb": "Suburb",
        "Housing_Type": "Housing Type", "School_Type": "School Type", "school_count": "No. of Schools",
        "MODE": "Mode of Transport", "stop_count": "No. of Stops",
        "Latest_Median": "Median Rent", "Forecasted_Next_Quarter": "Forecasted Rent"
    })

    return [{"name": i, "id": i} for i in df.columns], df.to_dict("records")

@suburb_recommender_app.callback(
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


# Forcast APP
forecast_app = Dash(__name__, server=main_app, url_base_pathname='/historical_forecast/', external_stylesheets=[dbc.themes.FLATLY])
forecast_app.layout = html.Div(children=[
    html.P("Historical Trends & Forecast", style={"textAlign": "center", "fontSize": "40px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),

    html.Div(children=[
        html.Div([
            html.P("Select Housing Type", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="housing_type_dropdown", searchable=False, value=historical_data["type"].unique()[0],
                options=[{'label': val.capitalize(), 'value': val} for val in sorted(historical_data["type"].unique())]
            )
        ], style={"width": "100%"}),
        html.Div([
            html.P("Select Preferred Suburb", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="suburb_dropdown", searchable=True, value="Clayton",
                options=[{'label': val.capitalize(), 'value': val} for val in sorted(historical_data["suburb"].unique())]),
        ], style={"width": "100%"}),
        html.Div([
            html.P("Select Victorian Region", style={"fontSize": "16px", "fontWeight": "bold", "margin": "0px", "padding": "0px"}),
            dcc.Dropdown(id="region_dropdown", searchable=False, value="Inner Eastern Melbourne",
                options=[{'label': val.capitalize(), 'value': val} for val in historical_data["region"].unique()]
            )
        ], style={"width": "100%"}),
    ], style={"display": "flex", "flexDirection": "row", "alignItems": "center", "justifyContent": "space-around", "gap": "30px", "margin": "10px 30px"}),

    html.Div(children=[
        dcc.Graph(id="historical_trend_graph", config=plot_config, style={"height": "100%", "width": "100%", "flex": 2}),
        dcc.Graph(id="forcasted_graph", config=plot_config, style={"height": "100%", "width": "100%", "flex": 1})
    ], style={
        "height": "calc(100% - 10px)", "flex": 1, "display": "flex", "flexDirection": "row", "alignItems": "stretch",
        "justifyContent": "space-around", "gap": "15px", "margin": "10px 15px"
    })

], style={"display": "flex", "flexDirection": "column", "backgroundColor": "#EAE8DC", "height": "100vh", "paddingBottom": "10px", "overflow": "hidden"})

@forecast_app.callback(
    Output("historical_trend_graph", "figure"),
    [Input("housing_type_dropdown", "value"), Input("suburb_dropdown", "value")]
)
def update_historical_trend(housing_type_value, suburb_value):
    df = historical_data.copy()
    df = df[(df["type"] == housing_type_value) & (df["suburb"] == suburb_value)]

    df["Count"] = pd.to_numeric(df["Count"])
    df["Median"] = pd.to_numeric(df["Median"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
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

@forecast_app.callback(
    Output("region_dropdown", "value"),
    Input("suburb_dropdown", "value")
)
def update_region_dropdown(suburb_value):
    df = historical_data.copy()
    df = df[df["suburb"] == suburb_value]
    return df["region"].unique()[0]

@forecast_app.callback(
    Output("forcasted_graph", "figure"),
    [Input("housing_type_dropdown", "value"), Input("region_dropdown", "value")]
)
def update_forcasted_graph(housing_type_value, region_value):
    df = historical_data.copy()
    df = df[(df["type"] == housing_type_value) & (df["region"] == region_value)]

    df["Median"] = pd.to_numeric(df["Median"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    results = []
    for suburb in sorted(df["suburb"].unique()):
        sub_df = df[df["suburb"] == suburb]
        sub_df = sub_df.sort_values(["timestamp"])

        y = sub_df["Median"].values
        model = SARIMAX(y, order=(1, 1, 1), seasonal_order=(1, 1, 1, 4), enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False)
        forecast = fit.get_forecast(steps=1).predicted_mean

        next_quarter_forecast = forecast[0]
        last_actual = y[-1]
        pct_change = ((next_quarter_forecast - last_actual) / last_actual) * 100

        results.append({"suburb": suburb, "forecast_change": pct_change})

    suburb_df = pd.DataFrame(results)
    colors = ["green" if change >= 0 else "red" for change in suburb_df["forecast_change"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=suburb_df["forecast_change"], y=suburb_df["suburb"], orientation="h", marker=dict(color=colors, opacity=0.7))
    )
    fig.update_layout(
        title=f"Forecasted Median Rental Price Change of <br><b>{housing_type_value}'s</b> in <br><b>{region_value}, Victoria</b>",
        xaxis=dict(title="Forecasted Change (%) of Rent", range=[suburb_df["forecast_change"].min()-3, suburb_df["forecast_change"].max()+3]),
        yaxis=dict(title="Suburb"),
        template="simple_white"
    )
    return fig


# SUPPORT APP
support_app = Dash(__name__, server=main_app, url_base_pathname='/support_dash/', external_stylesheets=[dbc.themes.FLATLY])
support_app.layout = html.Div(children=[
    html.Br(),
    html.H3('Select your location preference for the Support organisation', style={'textAlign': 'center'}),
    html.P('''Please note that all the organisations given below operate in Victoria. 
           There are some support service organisations that are based on the other states of Australia, 
           but all of them operate in Victoria remotely. All the organisation details that you see, operate in 
           Victoria, Australia.''', style={'margin-left': '10%', 'width': '80%', 'textAlign': 'center'}),

    html.Br(),
    html.H4('Please enter your preferred support organisation:', style={'textAlign': 'center'}),

    dcc.RadioItems(
        id='radio-filter',
        options=[{'label': i, 'value': i} for i in data['inside_vic'].unique()],
        value=data['inside_vic'].unique()[0],
        labelStyle={'display': 'inline-block', 'margin-right': '20px'},
        inputStyle={'margin-right': '10px'},
        style={'textAlign': 'center'}
    ),

    html.Br(),
    html.H4('Select from the given Suburbs:', style={'textAlign': 'center'}),
    dcc.Dropdown(
        id='dropdown-filtered',
        options=[],
        value=None,
        multi=True,
        style={'margin-left': '15%', 'width': '70%'}
    ),

    html.Br(),
    html.Div(id='output',
             style={'width': '90%', 'border': 'solid', 'border-width': '2px', 'border-collapse': 'separate',
                    'margin-left': '5%'}),
    html.Br(),
    html.Br()
], style={'backgroundColor': '#EAE8DC', 'minHeight': '100vh', 'height': '100%'})

@support_app.callback(
    Output('dropdown-filtered', 'options'),
    Input('radio-filter', 'value')
)
def update_dropdown(value):
    if (value == "Only Victorian organisations"):
        filtered_data = data[data['inside_vic'] == value]
    else:
        filtered_data = data
    list_of_suburbs = sorted([str(suburb) for suburb in filtered_data["Town_City"].unique()])
    options = [{'label': str(suburb), 'value': str(suburb)} for suburb in list_of_suburbs]
    return options

@support_app.callback(
    Output('output', 'children'),
    Input('dropdown-filtered', 'value')
)
def update_table(value):
    final_df = pd.DataFrame(columns=["Name", "Website", "Type", "E-mail", "Phone number"])

    if ((value is not None) and (len(value) != 0)):
        filtered_df = data[data["Town_City"].isin(value)]
        filtered_df = filtered_df[
            ['Charity_Legal_Name', 'Charity_Website', 'Advancing_Education', 'Promoting_or_protecting_human_rights',
             'Advancing_social_or_public_welfare', 'Children', 'Families', 'Females', 'Financially_Disadvantaged',
             'Males', 'People_at_risk_of_homelessness', 'email', 'contact']]

        for index, row in filtered_df.iterrows():
            charity_type = [col for col, value in row.items() if str(value).strip() == "Y"]
            final_df = final_df._append({"Name": row['Charity_Legal_Name'], "Website": row['Charity_Website'],
                                         "Type": str(charity_type).replace("[", "").replace("]", ""),
                                         "E-mail": row['email'], "Phone number": row['contact']}, ignore_index=True)

    table_data = [html.Tr(
        [html.Th(col, style={'width': '27%', 'padding': '10px', 'border-bottom': '2px solid black'}) for col in
         final_df.columns])] + \
                 [html.Tr([html.Td(final_df.iloc[i][col], style={'padding': '10px'}) if col != "Website" else html.Td(
                     html.A(final_df.iloc[i][col], href=final_df.iloc[i][col])) for col in final_df.columns])
                  for i in range(len(final_df))]
    return table_data


if __name__ == '__main__':
    main_app.run(debug=False, host="0.0.0.0", port=8003)