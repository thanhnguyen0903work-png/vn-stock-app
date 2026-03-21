from vnstock import stock_historical_data

# Lấy data
df = stock_historical_data(
    symbol="VNM",
    start_date="2023-01-01",
    end_date="2025-12-31"
)

# Save file
df.to_csv("data.csv", index=False)

print("Data updated!")