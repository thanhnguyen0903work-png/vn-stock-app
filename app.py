import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from vnstock import stock_historical_data
import time
from datetime import date

st.title(" Vietnam Stock Dashboard")


# ===== Input =====
symbol = st.text_input("Enter stock code", "VNM")
start_date = st.date_input("Start Date", date(2023, 1, 1))
end_date = st.date_input("End Date", date(2023, 12, 31))
start_date = start_date.strftime("%Y-%m-%d")
end_date = end_date.strftime("%Y-%m-%d")
# cache data
@st.cache_data
def load_data(symbol, start_date, end_date):
    return stock_historical_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date)

# ===== Load data =====
with st.spinner("Loading data..."):
    time.sleep(2)
    df = load_data(symbol, start_date, end_date)

df = df.sort_values('time')

# ===== Clean data (fix spike) =====
df = df[df['close'] > df['close'].quantile(0.01)]

#  
df['volume_m'] = df['volume'] / 1_000_000

# ===== Moving Average =====
df['MA20'] = df['close'].rolling(20).mean()
df['MA50'] = df['close'].rolling(50).mean()
# % change in price
latest_price = df['close'].iloc[-1]
prev_price = df['close'].iloc[-2]

change = latest_price - prev_price
pct_change = (change / prev_price) * 100

col1, col2 = st.columns(2)

col1.metric("Latest Price", f"{latest_price:,.0f}", f"{change:+.0f}")
col2.metric("% Change", f"{pct_change:.2f}%")

# ===== Generate Signal =====
df['Signal'] = 0
df.loc[df['MA20'] > df['MA50'], 'Signal'] = 1
df['Position'] = df['Signal'].diff()

# ===== Plot =====
fig = go.Figure()

# Price
fig.add_trace(go.Scatter(
    x=df['time'], y=df['close'],
    name='Price', line=dict(color='blue'),
     hovertemplate="Date: %{x}<br>Price: %{y:,.0f}<extra></extra>"))


# MA20
fig.add_trace(go.Scatter(
    x=df['time'], y=df['MA20'],
    name='MA20', line=dict(color='red'),
    hovertemplate="MA20: %{y:,.0f}<extra></extra>"
))

# MA50
fig.add_trace(go.Scatter(
    x=df['time'], y=df['MA50'],
    name='MA50', line=dict(color='green'), hovertemplate="MA50: %{y:,.0f}<extra></extra>"
))

# === BUY signals =
buy = df[df['Position'] == 1]
fig.add_trace(go.Scatter(
    x=buy['time'], y=buy['close'],
    mode='markers',
    marker=dict(symbol='triangle-up', color='green', size=10),
    name='BUY',hovertemplate="BUY<br>Date: %{x}<br>Price: %{y:,.0f}<extra></extra>"
))

# ===== SELL signals =====
sell = df[df['Position'] == -1]
fig.add_trace(go.Scatter(
    x=sell['time'], y=sell['close'],
    mode='markers',
    marker=dict(symbol='triangle-down', color='red', size=10),
    name='SELL'
))

fig.update_layout(
    title=f"{symbol} Price with Trading Signals",
    xaxis_title="Date",
    yaxis_title="Price"
)

st.plotly_chart(fig)
# volume 
st.subheader("📊 Volume")

fig_volume = go.Figure()

fig_volume.add_trace(go.Bar(
    x=df['time'],
    y=df['volume_m'],
    name='Volume'
))
fig_volume.update_layout(yaxis_title="Volume (Millions)")
fig.update_traces(
    hovertemplate="Date: %{x}<br>Price: %{y:,.0f}"
)
st.plotly_chart(fig_volume)

# ===== Show latest signal =====
latest_signal = df.iloc[-1]['Signal']

if latest_signal == 1:
    st.success("📢 Current Trend: BUY (Uptrend)")
else:
    st.error("📢 Current Trend: SELL (Downtrend)")

st.subheader("📈 Analysis")
# 
if df['MA20'].iloc[-1] > df['MA50'].iloc[-1]:
    st.success("📈 Uptrend: Short-term momentum is strong")
else:
    st.error("📉 Downtrend: Price is below moving averages")

if df['volume'].iloc[-1] > df['volume'].mean():
    st.info("🔥 Volume spike detected → possible strong movement")