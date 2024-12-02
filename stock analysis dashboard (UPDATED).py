import dash
from dash import dcc, html, Input, Output
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import cachetools.func  # For caching

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Interactive Stock Performance Dashboard"

# Cache for stock data to avoid redundant API calls
@cachetools.func.ttl_cache(maxsize=100, ttl=300)
def fetch_stock_data(ticker, start_date, end_date):
    """Fetch stock data from Yahoo Finance with caching."""
    data = yf.Ticker(ticker)
    hist = data.history(start=start_date, end=end_date)
    return hist, data.info

# Layout of the Dashboard
app.layout = html.Div([
    html.H1("Interactive Stock Performance Dashboard"),
    
    # User Inputs
    html.Div([
        html.Label("Stock Ticker:"),
        dcc.Input(id="stock-ticker", type="text", value="AAPL", placeholder="Enter stock ticker"),
        
        html.Label("Comparison Index:"),
        dcc.Dropdown(
            id="comparison-index",
            options=[
                {"label": "S&P 500 (^GSPC)", "value": "^GSPC"},
                {"label": "NASDAQ (^IXIC)", "value": "^IXIC"}
            ],
            value="^GSPC",  # Default is S&P 500
            placeholder="Select a market index"
        ),
        
        html.Label("Start Date:"),
        dcc.Input(id="start-date", type="text", value="2022-01-01", placeholder="YYYY-MM-DD"),
        
        html.Label("End Date:"),
        dcc.Input(id="end-date", type="text", value="2023-01-01", placeholder="YYYY-MM-DD"),
        
        html.Button("Update", id="update-button"),
    ], style={"margin-bottom": "20px"}),
    
    # Graphs
    dcc.Graph(id="stock-price-chart"),
    dcc.Graph(id="comparison-chart"),
    dcc.Graph(id="financial-metrics-chart"),
    
    # Export Button
    html.Button("Export Data to CSV", id="export-button"),
    dcc.Download(id="download-dataframe-csv")
])

# Callbacks for updating graphs
@app.callback(
    [Output("stock-price-chart", "figure"),
     Output("comparison-chart", "figure"),
     Output("financial-metrics-chart", "figure")],
    [Input("update-button", "n_clicks")],
    [Input("stock-ticker", "value"), Input("comparison-index", "value"),
     Input("start-date", "value"), Input("end-date", "value")]
)
def update_dashboard(n_clicks, stock_ticker, comparison_index, start_date, end_date):
    # Fetch stock and comparison data
    stock_data, stock_info = fetch_stock_data(stock_ticker, start_date, end_date)
    comparison_data, _ = fetch_stock_data(comparison_index, start_date, end_date)
    
    # Stock price chart
    fig_stock = go.Figure()
    fig_stock.add_trace(go.Scatter(x=stock_data.index, y=stock_data["Close"], name=f"{stock_ticker} Price"))
    fig_stock.update_layout(title=f"{stock_ticker} Stock Price", xaxis_title="Date", yaxis_title="Price (USD)")

    # Comparison chart (cumulative returns)
    stock_returns = stock_data["Close"].pct_change().cumsum()
    comparison_returns = comparison_data["Close"].pct_change().cumsum()
    fig_comparison = go.Figure()
    fig_comparison.add_trace(go.Scatter(x=stock_data.index, y=stock_returns, name=f"{stock_ticker} Returns"))
    fig_comparison.add_trace(go.Scatter(x=comparison_data.index, y=comparison_returns, name=f"{comparison_index} Returns"))
    fig_comparison.update_layout(title="Performance Comparison", xaxis_title="Date", yaxis_title="Cumulative Returns")

    # Financial metrics chart
    metrics = {
        "P/E Ratio": stock_info.get("trailingPE", None),
        "Dividend Yield (%)": stock_info.get("dividendYield", None) * 100 if stock_info.get("dividendYield") else None,
        "EPS (USD)": stock_info.get("trailingEps", None),
    }

    # Check for missing metrics and handle gracefully
    metric_names = list(metrics.keys())
    metric_values = [value if value is not None else 0 for value in metrics.values()]
    
    # Add annotations for actual values
    fig_metrics = go.Figure(
        data=[go.Bar(x=metric_names, y=metric_values, text=[f"{val:.2f}" for val in metric_values],
                     textposition='auto')]
    )
    fig_metrics.update_layout(
        title="Key Financial Metrics",
        xaxis_title="Metric",
        yaxis_title="Value",
        colorway=px.colors.qualitative.Pastel,
        showlegend=False
    )
    
    return fig_stock, fig_comparison, fig_metrics

@app.callback(
    Output("download-dataframe-csv", "data"),
    [Input("export-button", "n_clicks")],
    [Input("stock-ticker", "value"), Input("start-date", "value"), Input("end-date", "value")]
)
def export_data(n_clicks, stock_ticker, start_date, end_date):
    if n_clicks is None:
        return dash.no_update
    stock_data, _ = fetch_stock_data(stock_ticker, start_date, end_date)
    return dcc.send_data_frame(stock_data.to_csv, f"{stock_ticker}_data.csv")

# Run app
if __name__ == "__main__":
    app.run_server(debug=True)
