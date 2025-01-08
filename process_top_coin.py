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


def save_progress(top_coin_results, excluded_symbols, last_date):
    with open("result/top_coin_results.json", "w") as f:
        json.dump(top_coin_results, f, indent=4)
    with open("result/excluded_symbols.json", "w") as f:
        json.dump(list(excluded_symbols), f)
    with open("result/last_processed_date.txt", "w") as f:
        f.write(last_date)


def load_progress():
    try:
        with open("result/top_coin_results.json", "r") as f:
            top_coin_results = json.load(f)
    except FileNotFoundError:
        top_coin_results = {}

    try:
        with open("result/excluded_symbols.json", "r") as f:
            excluded_symbols = set(json.load(f))
    except FileNotFoundError:
        excluded_symbols = set()

    try:
        with open("result/last_processed_date.txt", "r") as f:
            last_date = datetime.strptime(f.read().strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except FileNotFoundError:
        last_date = None

    return top_coin_results, excluded_symbols, last_date


def process_top_100_symbols(start_date, end_date):
    symbols = load_top_100_symbols()
    top_coin_results, excluded_symbols, last_processed_date = load_progress()

    current_date = last_processed_date + timedelta(days=1) if last_processed_date else start_date
    total_days = (end_date - start_date).days + 1

    with tqdm(total=total_days, desc="Processing Days") as pbar:
        if last_processed_date:
            pbar.update((last_processed_date - start_date).days + 1)

        while current_date <= end_date:
            start_time = int(current_date.replace(tzinfo=timezone.utc).timestamp() * 1000)
            end_time = int((current_date + timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp() * 1000)
            prev_start_time = int((current_date - timedelta(days=1)).replace(tzinfo=timezone.utc).timestamp() * 1000)

            results = []

            for symbol in symbols:
                if symbol in excluded_symbols:
                    continue

                try:
                    data = fetch_binance_historical_data(symbol, "1d", start_time, end_time)
                    prev_data = fetch_binance_historical_data(symbol, "1d", prev_start_time, start_time)

                    if not data or not prev_data:
                        continue

                    kline = data[0]
                    prev_kline = prev_data[0]
                    open_price = float(kline[1])
                    close_price = float(kline[4])
                    quote_volume = float(kline[7])
                    prev_quote_volume = float(prev_kline[7])

                    if quote_volume <= 0 or prev_quote_volume <= 0:
                        continue

                    market_cap_change = (close_price - open_price) / open_price * 100
                    volume_change = ((quote_volume - prev_quote_volume) / prev_quote_volume * 100)

                    results.append({
                        "symbol": symbol,
                        "market_cap_change": market_cap_change,
                        "volume_change": volume_change
                    })
                except Exception:
                    excluded_symbols.add(symbol)

            if results:
                df = pd.DataFrame(results)
                df["volume_rank"] = df["volume_change"].rank(ascending=False)
                df["market_cap_rank"] = df["market_cap_change"].abs().rank(ascending=False)
                df["combined_rank"] = df["volume_rank"] + df["market_cap_rank"]
                top_coin = df.sort_values(by="combined_rank").iloc[0]
                top_coin_results[current_date.strftime('%Y-%m-%d')] = top_coin["symbol"]

            save_progress(top_coin_results, excluded_symbols, current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
            pbar.update(1)


if __name__ == "__main__":
    start_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    process_top_100_symbols(start_date, end_date)
