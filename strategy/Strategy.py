import json
import pandas as pd
from datetime import datetime, timedelta
from market_condition import market_prediction
from Martingale import martingale

def main():
    print("Start testing the strategy...")

    # Load parsed data from JSON file
    with open('result/top_coin_results.json', 'r') as file:
        parsed_data = json.load(file)

    market_type = []
    end_values = []
    sharpe_ratios = []

    # Loop through each entry in the JSON data
    for start_date, symbol in parsed_data.items():
        target_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        result_date = (target_datetime + timedelta(days=31)).strftime('%Y-%m-%d')
        starting_date = (target_datetime + timedelta(days=1)).strftime('%Y-%m-%d')

        # Predict market condition
        market = market_prediction(symbol, start_date)

        # Run the martingale strategy
        capital = 1000
        end_value, sharpe_ratio = martingale(symbol, starting_date, result_date, market, capital)
        print(f"Market prediction for {symbol} starting on {start_date}: {market}, End Value = {end_value}, Sharpe Ratio = {sharpe_ratio}")

        # Append results
        market_type.append(market)
        end_values.append(end_value)
        sharpe_ratios.append(sharpe_ratio)

    # Save results to CSV file
    output_file = 'result/strategy_results.csv'
    results = {
        'symbol': list(parsed_data.values()),
        'start_date': list(parsed_data.keys()),
        'market_prediction': market_type,
        'end_value': end_values,
        'sharpe_ratio': sharpe_ratios
    }
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    
    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    main()
