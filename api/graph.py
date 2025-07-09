from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import datetime
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc

router = APIRouter()

# Ticker mapping
TICKER_MAP = {
    'Apple': 'AAPL', 'Adobe': 'ADBE', 'AMD': 'AMD', 'Uber Technologies Inc': 'UBER',
    'Amazon': 'AMZN', 'American Express': 'AXP', 'Boeing': 'BA', 'Bank of America': 'BAC',
    'BlackRock': 'BLK', 'Caterpillar': 'CAT', 'Comcast': 'CMCSA', 'Abbot Laboratories': 'ABT',
    'Salesforce': 'CRM', 'Cisco': 'CSCO', 'Chevron': 'CVX', 'Disney': 'DIS',
    'General Electric': 'GE', 'Alphabet': 'GOOGL', 'Goldman Sachs': 'GS', 'Home Depot': 'HD',
    'Honeywell': 'HON', 'IBM': 'IBM', 'Intel': 'INTC', 'Johnson & Johnson': 'JNJ',
    'JPMorgan Chase': 'JPM', 'Coca-cola': 'KO', 'Mastercard': 'MA', "McDonald's": 'MCD',
    'PepsiCo Inc': 'PEP', 'Meta Platforms': 'META', 'Merck': 'MRK', 'Nvidia Corp': 'NVDA',
    'Microsoft': 'MSFT', 'Netflix': 'NFLX', 'Nike': 'NKE', 'Oracle': 'ORCL',
    'Pfizer': 'PFE', 'Procter Gamble': 'PG', 'Philip Morris': 'PM', 'Qualcomm': 'QCOM',
    'Starbucks': 'SBUX', 'Eli Lilly and Co': 'LLY', 'AT&T': 'T', 'Airbnb Inc': 'ABNB',
    'Tesla Inc': 'TSLA', 'Visa': 'V', 'Verizon': 'VZ', 'Wells Fargo': 'WFC',
    'Walmart': 'WMT', 'Exxon': 'XOM'
}

tickers = list(TICKER_MAP.values())
end_date = datetime.datetime.today().strftime('%Y-%m-%d')

# === Step 1: Download and preprocess data ===
prices = yf.download(tickers, start="2003-01-01", end=end_date, auto_adjust=True)["Close"]
yearly_prices = prices.resample('YE').last()
annual_returns = yearly_prices.pct_change().dropna(how='all')

# === Step 2: Portfolio Simulation ===
initial_value = 10000
top_portfolio = [initial_value]
bottom_portfolio = [initial_value]
years = [annual_returns.index[0].year]  # e.g., 2004

detailed_records = []

for i in range(len(annual_returns) - 1):
    current_year = annual_returns.index[i].year
    next_year = annual_returns.index[i + 1].year
    current_returns = annual_returns.iloc[i].dropna()
    next_returns = annual_returns.iloc[i + 1].dropna()
    valid_stocks = current_returns.index.intersection(next_returns.index)

    top10 = current_returns[valid_stocks].sort_values(ascending=False).head(10)
    bottom10 = current_returns[valid_stocks].sort_values().head(10)

    top_avg = next_returns[top10.index].mean()
    bottom_avg = next_returns[bottom10.index].mean()

    top_value = top_portfolio[-1] * (1 + top_avg)
    bottom_value = bottom_portfolio[-1] * (1 + bottom_avg)

    top_portfolio.append(top_value)
    bottom_portfolio.append(bottom_value)
    years.append(next_year)

    for stock, ret in top10.items():
        detailed_records.append({
            "Year": next_year,
            "Category": "Top 10",
            "Stock": stock,
            "Return %": round(ret * 100, 2)
        })
    for stock, ret in bottom10.items():
        detailed_records.append({
            "Year": next_year,
            "Category": "Bottom 10",
            "Stock": stock,
            "Return %": round(ret * 100, 2)
        })

summary_rows = []
for i in range(1, len(years)):
    year = years[i]
    top_start = top_portfolio[i - 1]
    top_end = top_portfolio[i]
    bottom_start = bottom_portfolio[i - 1]
    bottom_end = bottom_portfolio[i]

    top_return = (top_end - top_start) / top_start
    bottom_return = (bottom_end - bottom_start) / bottom_start

    summary_rows.append({
        "Year": year,
        "Top 10 Return %": round(top_return * 100, 2),
        "Bottom 10 Return %": round(bottom_return * 100, 2),
        "Top 10 End Value": round(top_end, 2),
        "Bottom 10 End Value": round(bottom_end, 2),
        "Top 10 Cumulative Return %": round((top_end / initial_value - 1) * 100, 2),
        "Bottom 10 Cumulative Return %": round((bottom_end / initial_value - 1) * 100, 2)
    })

summary_df = pd.DataFrame(summary_rows)
detailed_df = pd.DataFrame(detailed_records)

df = pd.DataFrame({
    "Year": years,
    "Top 10 Portfolio": top_portfolio,
    "Bottom 10 Portfolio": bottom_portfolio
})

preloaded_data = {}
for ticker in tickers:
    series = prices[ticker].dropna()
    if not series.empty:
        preloaded_data[ticker] = series / series.iloc[0] * 100

# === Step 6: Dash App Layout ===
app_dash = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], requests_pathname_prefix='/dash-layout/')
app_dash.layout = html.Div([
    html.H1("Winner vs Loser Portfolio Strategy"),

    dcc.Graph(
        id='portfolio-chart',
        figure={
            'data': [
                dict(x=df["Year"], y=df["Top 10 Portfolio"], type='scatter', mode='lines+markers',
                     name='Top 10 Strategy', line=dict(color='green')),
                dict(x=df["Year"], y=df["Bottom 10 Portfolio"], type='scatter', mode='lines+markers',
                     name='Bottom 10 Strategy', line=dict(color='red')),
            ],
            'layout': dict(
                title='Cumulative Portfolio Value',
                xaxis={'title': 'Year'},
                yaxis={'title': 'Portfolio Value ($)'},
                hovermode='x unified'
            )
        }
    ),

    html.H2("Summary Table (Portfolio Stats)"),
    dash_table.DataTable(
        id='summary-table',
        data=summary_df.to_dict("records"),
        columns=[{"name": i, "id": i} for i in summary_df.columns],
        style_table={'marginBottom': '40px', 'overflowX': 'auto'}
    ),

    html.H2("Top & Bottom 10 Stocks by Year"),
    html.Label("Select Year:"),
    dcc.Dropdown(
        id='year-dropdown',
        options=[{"label": str(year), "value": year} for year in sorted(detailed_df["Year"].unique())],
        value=sorted(detailed_df["Year"].unique())[0],
        style={'width': '200px', 'marginBottom': '20px'}
    ),
    dash_table.DataTable(
        id='yearly-detail-table',
        columns=[
            {"name": "Category", "id": "Category"},
            {"name": "Stock", "id": "Stock"},
            {"name": "Return (%)", "id": "Return %"}
        ],
        style_table={'overflowX': 'auto'},
        style_cell={'padding': '5px'},
    ),

    html.H2("Individual Stock Analysis"),
    html.Label("Select a Stock:"),
    dcc.Dropdown(
        id='stock-dropdown',
        options=[{"label": name, "value": ticker} for name, ticker in TICKER_MAP.items()],
        value='AAPL',
        style={'width': '300px', 'marginBottom': '20px'}
    ),
    dcc.Graph(id='stock-performance')
])

# === Callback for Yearly Detail Table ===
@app_dash.callback(
    Output('yearly-detail-table', 'data'),
    Input('year-dropdown', 'value')
)
def update_yearly_detail_table(selected_year):
    filtered = detailed_df[detailed_df["Year"] == selected_year]
    return filtered[["Category", "Stock", "Return %"]].to_dict("records")

# === Callback for Stock Chart ===
@app_dash.callback(
    Output('stock-performance', 'figure'),
    Input('stock-dropdown', 'value')
)
def update_stock_chart(ticker):
    if ticker not in preloaded_data or preloaded_data[ticker].empty:
        return go.Figure(layout={"title": f"No data available for {ticker}"})

    normalized = preloaded_data[ticker]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=normalized.index, y=normalized, mode='lines', name=ticker))
    fig.update_layout(
        title=f"{ticker} Normalized Price Performance",
        xaxis_title="Date",
        yaxis_title="Normalized Price (100 = start)",
        template="plotly_white"
    )
    return fig