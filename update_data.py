from vnstock import stock_historical_data

print("Fetching data...")

df = stock_historical_data(
    symbol="VNM",
    start_date="2023-01-01",
    end_date="2025-12-31"
)

print(df.head())

df.to_csv("data.csv", index=False)

print("Data updated successfully!")