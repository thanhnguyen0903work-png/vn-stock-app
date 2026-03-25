import time
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from vnstock import stock_historical_data


# 0. Page setup
st.set_page_config(page_title="Vietnam Stock Dashboard", layout="wide")
st.title("Vietnam Stock Dashboard")

# 1. User inputs
symbol = st.text_input("Enter stock code", "VNM").strip().upper()
range_label = st.selectbox(
    "Select Time Range",
    ["1 Week", "1 Month", "3 Months", "1 Year"],
    index=2,
)
# Toggles for overlays
show_ma20 = st.checkbox("Show MA20", value=True)
show_ma50 = st.checkbox("Show MA50", value=True)
show_pred = st.checkbox("Show Predicted", value=True)

# 2. Map UI choice to dates (view window + extended context window)
today = datetime.today()
range_days = {"1 Week": 7, "1 Month": 30, "3 Months": 90, "1 Year": 365}[range_label]
# Use longer context to keep indicators/ML stable even on short views
context_days = max(range_days, 120)
context_start = (today - timedelta(days=context_days)).strftime("%Y-%m-%d")
end_date = today.strftime("%Y-%m-%d")
view_start = today - timedelta(days=range_days)


# 3. Fetch price data (cached)
@st.cache_data(show_spinner=False)
def load_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    return stock_historical_data(symbol=symbol, start_date=start_date, end_date=end_date)


# 4. ML model with adaptive windows (survives short histories)
def run_ml_model(df: pd.DataFrame):
    df = df.copy()
    n = len(df)
    if n < 15:
        raise ValueError("Too little price history (<15 bars). Please choose a longer range.")

    #  Choose adaptive window suitable for short data range
    lag1 = 1
    lag3 = min(3, max(1, n // 10))
    ma_short = min(10, max(3, n // 3))  # 3–10 
    ma_long = min(20, max(6, n // 2))   # 6–20 

    df["lag1"] = df["close"].shift(lag1)
    df["lag3"] = df["close"].shift(lag3)
    df["ma_short"] = df["close"].rolling(ma_short, min_periods=1).mean()
    df["ma_long"] = df["close"].rolling(ma_long, min_periods=1).mean()
    df = df.dropna()

    if len(df) < 10:
        raise ValueError("Model features left <10 rows after rolling windows—need a few more bars.")

    X = df[["lag1", "lag3", "ma_short", "ma_long"]]
    y = df["close"]

    # Keep a small test slice so MSE still appear
    test_len = min(5, max(1, len(df) // 5))
    split = len(df) - test_len
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    if len(X_test) == 0:
        X_test, y_test = X_train, y_train

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)

    df_pred = df.iloc[split:].copy()
    df_pred["predicted"] = y_pred
    return df_pred, mse


def generate_insights(df_view: pd.DataFrame, mse_value: float | None):
    """Create simple, human-friendly insights based on price, MAs, volume, and model error."""
    insights = []
    if len(df_view) >= 2:
        ret = (df_view["close"].iloc[-1] / df_view["close"].iloc[0] - 1) * 100
        if ret > 3:
            insights.append(f"Price up {ret:.1f}% over this view window -> short-term momentum is positive.")
        elif ret < -3:
            insights.append(f"Price down {abs(ret):.1f}% over this view window -> short-term momentum is negative.")
        else:
            insights.append("Price is relatively flat in this view window -> no strong momentum signal.")

    if len(df_view) >= 1:
        if df_view["signal"].iloc[-1] == 1:
            insights.append("MA20 is above MA50 -> short-term trend supports a BUY bias.")
        else:
            insights.append("MA20 is below MA50 -> short-term trend favors caution/SELL bias.")

    if "volume" in df_view.columns and len(df_view) > 5:
        if df_view["volume"].iloc[-1] > df_view["volume"].mean() * 1.2:
            insights.append("Latest volume is >20% above average -> potential strong move or news.")

    if len(df_view) > 5:
        vol = df_view["close"].pct_change().std() * 100
        if vol > 3:
            insights.append(f"Volatility is elevated (~{vol:.1f}% daily std) -> size positions conservatively.")

    if mse_value is not None and len(df_view):
        rmse = mse_value ** 0.5
        price = df_view["close"].iloc[-1]
        if price:
            rel = (rmse / price) * 100
            insights.append(f"Model RMSE ≈ {rmse:,.0f} VND (~{rel:.1f}% of price) -> treat predictions as coarse guidance.")
    else:
        insights.append("Model not run (data too short) -> rely on price/MA signals only.")

    return insights


# 5. Load + pre-clean
with st.spinner("Loading data..."):
    try:
        df_raw = load_data(symbol, context_start, end_date)
    except Exception as e:
        st.error(f"Failed to load data for {symbol}: {e}")
        st.stop()

if df_raw.empty:
    st.warning("No data returned for that symbol/time range.")
    st.stop()

df = df_raw.sort_values("time")
df["time"] = pd.to_datetime(df["time"])
view_start = pd.to_datetime(view_start)

# 6. Indicators on full context (before trimming view)
win20 = min(20, len(df))
win50 = min(50, len(df))
df["MA20"] = df["close"].rolling(win20, min_periods=1).mean()
df["MA50"] = df["close"].rolling(win50, min_periods=1).mean()

# Filter outlier nhẹ (1% thấp nhất)
df = df[df["close"] > df["close"].quantile(0.01)]
df["volume_m"] = df["volume"] / 1_000_000


# 7. Run ML (non-blocking on short data)
try:
    df_pred, mse = run_ml_model(df)
    df = df.merge(df_pred[["time", "predicted"]], on="time", how="left")
except ValueError as e:
    st.info(str(e))
    mse = None


# 8. Signals on context, then cut to user view
df["signal"] = (df["MA20"] > df["MA50"]).astype(int)
df["position"] = df["signal"].diff().fillna(0)
df_view = df[df["time"] >= view_start]

if df_view.empty:
    st.warning("View window is empty after filtering. Try a longer range.")
    st.stop()

# Metrics based on view window
latest_price = df_view["close"].iloc[-1]
prev_price = df_view["close"].iloc[-2] if len(df_view) > 1 else df_view["close"].iloc[-1]
change = latest_price - prev_price
pct_change = (change / prev_price) * 100 if prev_price != 0 else 0


# 9. Quick metrics
c1, c2 = st.columns(2)
c1.metric("Latest Price", f"{latest_price:,.0f}", f"{change:+.0f}")
c2.metric("% Change", f"{pct_change:.2f}%")


# 10. Price chart (view window)
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_view["time"], y=df_view["close"],
    name="Price", line=dict(color="blue"),
    hovertemplate="Date: %{x}<br>Price: %{y:,.0f}<extra></extra>",
))
if show_ma20:
    fig.add_trace(go.Scatter(
        x=df_view["time"], y=df_view["MA20"],
        name="MA20", line=dict(color="red"),
        hovertemplate="MA20: %{y:,.0f}<extra></extra>",
    ))
if show_ma50:
    fig.add_trace(go.Scatter(
        x=df_view["time"], y=df_view["MA50"],
        name="MA50", line=dict(color="green"),
        hovertemplate="MA50: %{y:,.0f}<extra></extra>",
    ))

if show_pred and "predicted" in df_view:
    fig.add_trace(go.Scatter(
        x=df_view["time"], y=df_view["predicted"],
        name="Predicted", line=dict(color="orange", dash="dot"),
        hovertemplate="Predicted: %{y:,.0f}<extra></extra>",
    ))

buy = df_view[df_view["position"] == 1]
sell = df_view[df_view["position"] == -1]
fig.add_trace(go.Scatter(
    x=buy["time"], y=buy["close"], mode="markers",
    marker=dict(symbol="triangle-up", color="green", size=9),
    name="BUY",
    hovertemplate="BUY<br>Date: %{x}<br>Price: %{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=sell["time"], y=sell["close"], mode="markers",
    marker=dict(symbol="triangle-down", color="red", size=9),
    name="SELL",
    hovertemplate="SELL<br>Date: %{x}<br>Price: %{y:,.0f}<extra></extra>",
))

fig.update_layout(
    title=f"{symbol} Price with Signals",
    xaxis_title="Date",
    yaxis_title="Price",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)


# 11. Volume chart (view window)
fig_volume = go.Figure()
fig_volume.add_trace(go.Bar(x=df_view["time"], y=df_view["volume_m"], name="Volume"))
fig_volume.update_layout(
    title="Volume (Millions)",
    xaxis_title="Date",
    yaxis_title="Volume (M)",
)
st.plotly_chart(fig_volume, use_container_width=True)


# 12. Latest signal (view window)
latest_signal = int(df_view["signal"].iloc[-1])
if latest_signal == 1:
    st.success("Current Trend: BUY (MA20 above MA50)")
else:
    st.error("Current Trend: SELL (MA20 below MA50)")


# 13. Model metric & info
st.subheader("Metrics")
if mse is not None:
    st.metric("Model Error (MSE)", f"{mse:.2f}")
else:
    st.info("Model not run: insufficient data.")

if df["volume"].iloc[-1] > df["volume"].mean():
    st.info("Volume spike detected -> possible strong movement")


# 14. Recommendations / Insights
st.subheader("Recommendations / Insights")
for line in generate_insights(df_view, mse):
    st.markdown(f"- {line}")
