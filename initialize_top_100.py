import json
import requests
from datetime import datetime, timedelta
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta



def fetch_top_100_symbols_cmc(api_key, log_file):
    url_cmc = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }
    params = {
        "start": "1",         # Start from the top-ranked coin
        "limit": "100",       # Limit to the top 100 coins
        "convert": "USD"      # Convert market cap and price to USD
    }

    log_file.write("Fetching top 100 cryptocurrencies from CoinMarketCap.\n")
    response = requests.get(url_cmc, headers=headers, params=params)

    if response.status_code != 200:
        log_file.write(f"Error fetching data from CoinMarketCap: {response.status_code}, {response.text}\n")
        raise Exception(f"Error fetching data from CoinMarketCap: {response.status_code}, {response.text}")

    data = response.json()
    cryptocurrencies = data.get("data", [])
    
    if not cryptocurrencies:
        log_file.write("No data returned from CoinMarketCap.\n")
        raise Exception("No data returned from CoinMarketCap.")

    # Process and save top 100 cryptocurrencies
    top_100 = []
    for crypto in cryptocurrencies:
        symbol = crypto["symbol"]
        circulating_supply = crypto.get("circulating_supply", 0)
        price = crypto["quote"]["USD"]["price"]
        market_cap = circulating_supply * price

        top_100.append({
            "symbol": symbol,
            "circulating_supply": circulating_supply,
            "price": price,
            "market_cap": market_cap
        })
        log_file.write(f"Processed {symbol}: circulating_supply={circulating_supply}, price={price}, market_cap={market_cap}\n")

    # Sort by market cap and save top 100
    sorted_top_100 = sorted(top_100, key=lambda x: x["market_cap"], reverse=True)
    
    with open("log/top_100_symbols.log", "w") as f:
        for crypto in sorted_top_100:
            f.write(f"{crypto['symbol']}: market_cap={crypto['market_cap']:.6e}, "
                    f"circulating_supply={crypto['circulating_supply']:.6e}, price={crypto['price']:.6f}\n")
            
    # Save top_100_symbols.json, only the symbols, add "USDT" after each symbol
    symbols = [crypto["symbol"] + "USDT" for crypto in sorted_top_100]
    with open("result/top_100_symbols.json", "w") as f:
        json.dump(symbols, f)

    log_file.write("Top 100 symbols initialized and saved to top_100_symbols.log\n")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    API_KEY_CMC = os.getenv("CMC_API_KEY")
    with open("log/initialize_log.log", "w") as log_file:
        fetch_top_100_symbols_cmc(API_KEY_CMC, log_file)
