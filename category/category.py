import os
import pandas as pd
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
API_KEY_CMC = os.getenv("CMC_API_KEY")

if not API_KEY_CMC:
    print("API_KEY_CMC not found. Please set it in the .env file.")
    exit()

# API headers
headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": API_KEY_CMC}

# Function to fetch categories data
def fetch_categories():
    categories_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/categories"
    response = requests.get(categories_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching categories: {response.status_code}, {response.text}")
    return response.json().get("data", [])

# Function to fetch coins in a specific category
def fetch_coins_in_category(category_id):
    coins_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/category"
    params = {"id": category_id}
    response = requests.get(coins_url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Error fetching coins: {response.status_code}, {response.text}")
    return response.json().get("data", {}).get("coins", [])

# Function to get top coin for a specific date
def get_top_coin():
    categories_data = fetch_categories()
    if not categories_data:
        raise Exception("No categories data available.")

    # Convert categories to DataFrame
    categories_df = pd.DataFrame(categories_data)
    categories_df["market_cap_change"] = pd.to_numeric(categories_df["market_cap_change"], errors="coerce")
    categories_df["volume_change"] = pd.to_numeric(categories_df["volume_change"], errors="coerce")

    # Rank and sort categories
    categories_df["market_cap_rank"] = categories_df["market_cap_change"].abs().rank(ascending=False) # from highest to lowest
    categories_df["volume_rank"] = categories_df["volume_change"].rank(ascending=False) # from highest to lowest
    categories_df["combined_rank"] = categories_df["market_cap_rank"] + categories_df["volume_rank"]
    categories_df = categories_df.sort_values(by="combined_rank")

    # Get top category
    top_category = categories_df.iloc[0]
    category_id = top_category["id"]
    category_name = top_category["name"]

    # Fetch coins in the top category
    coins_data = fetch_coins_in_category(category_id)
    if not coins_data:
        raise Exception(f"No coins found in category '{category_name}'.")

    # Convert coins to DataFrame and find the top coin by market cap
    coins_df = pd.DataFrame(coins_data)
    if "quote" in coins_df.columns:
        coins_df["market_cap"] = coins_df["quote"].apply(
            lambda x: x.get("USD", {}).get("market_cap") if isinstance(x, dict) else None
        )
    coins_df["market_cap"] = pd.to_numeric(coins_df["market_cap"], errors="coerce")
    coins_df = coins_df.sort_values(by="market_cap", ascending=False)

    top_coin = coins_df.iloc[0]
    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "name": top_coin["name"],
        "symbol": top_coin["symbol"],
        "market_cap": top_coin["market_cap"]
    }

# Main script to iterate over 2024 and save results
def main():
    start_date = datetime(2025, 1, 6)
    end_date = datetime(2025, 1, 7)
    current_date = start_date
    results = []

    while current_date <= end_date:
        print(f"Fetching top coin for {current_date.strftime('%Y-%m-%d')}...")
        try:
            top_coin = get_top_coin()
            top_coin["date"] = current_date.strftime("%Y-%m-%d")
            results.append(top_coin)
        except Exception as e:
            print(f"Error on {current_date.strftime('%Y-%m-%d')}: {e}")
        current_date += timedelta(days=1)

    # Save results to a txt file
    with open("top_coins_2024.txt", "w") as f:
        for result in results:
            f.write(f"{result['date']}, {result['name']}, {result['symbol']}, {result['market_cap']}\n")

    print("Top coins for 2024 saved to top_coins_2024.txt.")

if __name__ == "__main__":
    main()
