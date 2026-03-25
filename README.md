# VN Stock Dashboard

Streamlit dashboard for Vietnam equities with moving-average signals, lightweight forecasting, and user-friendly insights. It always fetches an extended context (>=120 days) so indicators and predictions stay stable even when you only view a short window (1W/1M).

## Features
- View slices: 1W / 1M / 3M / 1Y; training always uses >=120 days of history for stability.
- Toggle overlays: MA20, MA50, Predicted line.
- Signals: BUY/SELL markers from MA20/MA50 crossovers.
- Forecast: simple linear regression with adaptive lags/rolling windows that tolerates short histories; reports MSE.
- Insights: auto bullets for momentum, MA trend bias, volume spike, volatility, and model confidence (RMSE% style).
- Charts: Price + MAs + Predicted + markers; Volume (millions). Quick metrics: Latest Price, % Change, MSE.

## Installation
```bash
pip install -r requirements.txt
```

## Run locally
```bash
streamlit run app.py
```

## How it works (flow)
1) Inputs: stock code + time range + overlay toggles (MA20/MA50/Predicted).  
2) Data: fetches at least 120 days of history (context) even if you only view 7–30 days.  
3) Indicators: MA20/MA50 computed with `min_periods=1` to avoid NaNs on short windows.  
4) Model: adaptive linear regression (lags, short/long MAs), small test slice to report MSE/RMSE; skips prediction if data is too short.  
5) View window: charts/metrics show only the user-selected slice; signals/predictions come from the full context.  
6) Insights: momentum, MA crossover bias, volume spike, volatility, and model confidence bullets.  

## Further expected enhancements
- Add RMSE%/MAPE to Metrics for clearer relative error.
- Switch to Ridge/Lasso (or ElasticNet) with simple CV to stabilize short-window forecasts.
- Optional rolling backtest (e.g., 3-fold walk-forward) to smooth out MSE variability.
- Auto “low confidence” badge when sample <40 bars or RMSE% >10%; hide Predicted in that case.
- Per-ticker saved presets (default overlays, default time range).
- Inline help/tooltips explaining each signal and metric.

## Deploy on Streamlit Cloud
1) Push this repo to GitHub.  
2) On share.streamlit.io, pick the repo/branch, set **Main file** to `app.py`.  
3) It will auto-install from `requirements.txt`. No secrets needed.  

## Screenshot
<img width="2553" height="983" alt="screenshot" src="https://github.com/user-attachments/assets/547aa052-01bf-429b-a14e-1b79534b8f7f" />
<img width="2525" height="927" alt="screenshot2" src="https://github.com/user-attachments/assets/4b363562-8856-47f6-aedc-35445ef9ee61" />


