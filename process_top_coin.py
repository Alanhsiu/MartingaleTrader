import json
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from tqdm import tqdm

def load_top_100_symbols():
    with open("result/top_100_symbols.json", "r") as f:
        return json.load(f)

def fetch_binance_historical_data(symbol, interval, start_time, end_time):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error fetching K-line data: {response.status_code}, {response.text}")
    return response.json()

def process_top_100_symbols(start_date, end_date):
    symbols = load_top_100_symbols()
    excluded_symbols = set()  # Keep track of symbols that fail
    interval = "1d"
    top_coin_results = {}

    total_days = (end_date - start_date).days + 1  # Total days to process
    current_date = start_date

    with tqdm(total=total_days, desc="Processing Days") as pbar:
        while current_date <= end_date:
            start_time = int(current_date.replace(tzinfo=timezone.utc).timestamp() * 1000)
            end_time = int((current_date + timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp() * 1000)
            prev_start_time = int((current_date - timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp() * 1000)

            results = []

            for symbol in symbols:
                if symbol in excluded_symbols:
                    continue  # Skip excluded symbols

                try:
                    # Fetch current and previous day's data
                    data = fetch_binance_historical_data(symbol, interval, start_time, end_time)
                    prev_data = fetch_binance_historical_data(symbol, interval, prev_start_time, start_time)

                    if not data or not prev_data:
                        continue

                    # Extract K-line data
                    kline = data[0]
                    prev_kline = prev_data[0]
                    open_price = float(kline[1])
                    close_price = float(kline[4])
                    quote_volume = float(kline[7])  # Volume in quote asset (e.g., USDT)
                    prev_quote_volume = float(prev_kline[7])

                    # Skip invalid data
                    if quote_volume <= 0 or prev_quote_volume <= 0:
                        continue

                    # Calculate changes
                    market_cap_change = (close_price - open_price) / open_price * 100
                    volume_change = ((quote_volume - prev_quote_volume) / prev_quote_volume * 100)

                    results.append({
                        "symbol": symbol,
                        "market_cap_change": market_cap_change,
                        "volume_change": volume_change
                    })
                except Exception:
                    excluded_symbols.add(symbol)  # Add to excluded list if API fails

            # Determine top coin for the day
            if results:
                df = pd.DataFrame(results)
                df["volume_rank"] = df["volume_change"].rank(ascending=False)
                df["market_cap_rank"] = df["market_cap_change"].abs().rank(ascending=False)
                df["combined_rank"] = df["volume_rank"] + df["market_cap_rank"]
                top_coin = df.sort_values(by="combined_rank").iloc[0]
                top_coin_results[current_date.strftime('%Y-%m-%d')] = top_coin["symbol"]

            current_date += timedelta(days=1)
            pbar.update(1)

    # Save top coin results to JSON
    with open("result/top_coin_results.json", "w") as f:
        json.dump(top_coin_results, f, indent=4)

    # Save excluded symbols
    with open("result/excluded_symbols.json", "w") as f:
        json.dump(list(excluded_symbols), f)


if __name__ == "__main__":
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 1, 3, tzinfo=timezone.utc)
    process_top_100_symbols(start_date, end_date)
