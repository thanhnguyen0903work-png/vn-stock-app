import plotly.graph_objects as go
from vnstock import stock_historical_data

# MA function
def add_moving_average(df):
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA50'] = df['close'].rolling(window=50).mean()
    return df

# Load data
df = stock_historical_data(
    symbol="VCB",
    start_date="2025-01-01",
    end_date="2025-12-31"
)

# Add MA
df = add_moving_average(df)

# Create chart
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['time'],
    y=df['close'],
    mode='lines',
    name='Price'
))

fig.add_trace(go.Scatter(
    x=df['time'],
    y=df['MA20'],
    mode='lines',
    name='MA20'
))

fig.add_trace(go.Scatter(
    x=df['time'],
    y=df['MA50'],
    mode='lines',
    name='MA50'
))

# Show chart
fig.show()

