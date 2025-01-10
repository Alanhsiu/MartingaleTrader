import backtrader as bt
import datetime
import pandas as pd
from binance.client import Client
import pytz

import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

def fetch_binance_data(symbol, interval, start_date, end_date, timezone):
    client = Client(API_KEY, API_SECRET)
    klines = client.get_historical_klines(
        symbol=symbol,
        interval=interval,
        start_str=start_date,
        end_str=end_date
    )
    data = []
    for kline in klines:
        utc_time = datetime.datetime.fromtimestamp(kline[0] / 1000, tz=pytz.utc)
        local_time = utc_time.astimezone(pytz.timezone(timezone))
        data.append({
            'datetime': local_time,
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5]),
        })
    
    df = pd.DataFrame(data)
    if df.isnull().values.any() or (df[['open', 'high', 'low', 'close']] == 0).any().any():
        raise ValueError("Data contains null or zero values, which is invalid for backtesting")
    return df.to_dict('records')

import backtrader as bt

class ReverseMartingaleStrategy(bt.Strategy):
    params = (
        ('fixed_position_size_bool', False),  # Use fixed position size or dynamic size
        ('start_position_size', 1),          # Initial position size as a percentage of total capital
        ('reverse_mult', 2),                 # Multiplier for position size on each profit threshold
        ('profit_threshold', 1.0),           # Profit percentage required to add to the position
    )

    def __init__(self):
        # Technical indicators
        self.atr = bt.indicators.ATR(self.data, period=5)  # Average True Range for volatility measurement
        self.macd = bt.indicators.MACD(self.data.close)    # MACD for trend signals
        self.current_unit_size = None                      # Current position size to trade
        self.add_position_count = 0                        # Number of times a position was added
        self.entry_price = None                            # Entry price for the position
        self.exited = False  # Flag to prevent re-entry after exiting

    def next(self):
        # Calculate position size
        if self.params.fixed_position_size_bool:
            self.current_unit_size = self.params.start_position_size
        else:
            self.current_unit_size = (self.broker.getvalue() * (self.params.start_position_size / 100)) / self.data.close[0]

        # Entry condition: MACD bullish crossover
        if self.macd.macd[0] > self.macd.signal[0] and self.position.size <= 0 and not self.exited:
            # Enter the initial position
            self.buy(size=self.current_unit_size)
            self.add_position_count = 0
            self.entry_price = self.data.close[0]

        # If a position is already open
        if self.position.size > 0:
            entry_price = self.position.price
            price_change_percent = (self.data.close[0] - entry_price) / entry_price * 100

            # Add to position if profit threshold is met and within the max add position limit
            if price_change_percent >= self.params.profit_threshold:
                new_unit_size = self.position.size * self.params.reverse_mult
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1

            # exit only if cash <= 0
            if self.broker.getcash() <= 0:
                self.close()
                self.exited = True

class MultifactorMartingaleStrategy(bt.Strategy):
    params = (
        ('start_position_size', 1),  # Initial position size as a percentage of total capital
        ('loss_threshold', 2.0),     # Percentage drop to trigger additional positions
        ('reverse_mult', 2.0),       # Multiplier for each additional position
    )

    def __init__(self):
        # Indicators
        self.macd = bt.indicators.MACD(self.data.close)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.atr = bt.indicators.ATR(self.data, period=5)  # ATR for volatility-based stop loss
        self.entry_price = None
        self.add_position_count = 0
        self.exited = False  # Flag to prevent re-entry after exiting

    def next(self):
        # Entry logic
        if self.position.size == 0:  
            if self.macd.macd[0] > self.macd.signal[0] and self.rsi[0] < 40 and not self.exited:
                current_unit_size = (self.broker.getvalue() * (self.params.start_position_size / 100)) / self.data.close[0]
                self.buy(size=current_unit_size)
                self.entry_price = self.data.close[0]
                self.add_position_count = 0

        elif self.position.size > 0:  # Position management logic
            profit_percent = (self.data.close[0] - self.entry_price) / self.entry_price * 100

            # Add position logic when loss threshold is met
            if profit_percent <= -self.params.loss_threshold:
                new_unit_size = self.position.size * self.params.reverse_mult
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1

            # exit only if cash <= 0
            if self.broker.getcash() <= 0:
                self.close()
                self.exited = True
                    
class TimeLimitedMartingaleStrategy(bt.Strategy):
    params = (
        ('macd_fast', 12),               # Fast EMA period
        ('macd_slow', 26),               # Slow EMA period
        ('macd_signal', 9),              # Signal line period
        ('initial_risk_percent', 1.0),   # Initial position as a percentage of total capital
        ('martingale_factor', 2.0),      # Multiplier for additional positions
        ('add_threshold_percent', 2.0),  # Price drop percentage to trigger additional positions
    )

    def __init__(self):
        # MACD Indicator for entry signals
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        self.current_unit_size = None     # Size of the current position
        self.entry_price = None           # Entry price for the position
        self.add_position_count = 0       # Tracks the number of additional positions added
        self.exited = False  # Flag to prevent re-entry after exiting

    def next(self):
        # Entry logic: MACD bullish crossover
        if not self.position and self.macd.macd[0] > self.macd.signal[0] and not self.exited:
            self.current_unit_size = (self.broker.getvalue() * (self.params.initial_risk_percent / 100)) / self.data.close[0]
            self.buy(size=self.current_unit_size)
            self.entry_price = self.data.close[0]
            self.add_position_count = 0  # Reset position count

        # Manage existing position
        elif self.position.size > 0:
            # Calculate price change percentages
            price_drop = (self.entry_price - self.data.close[0]) / self.entry_price * 100
            price_gain = (self.data.close[0] - self.entry_price) / self.entry_price * 100

            # Add position logic
            if price_drop >= self.params.add_threshold_percent:
                new_unit_size = self.position.size * self.params.martingale_factor
                if self.broker.getcash() > new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1

            # exit only if cash <= 0
            if self.broker.getcash() <= 0:
                self.close()
                self.exited = True
                    
class RiskLimitedMartingaleStrategy(bt.Strategy):
    params = (
        ('fixed_position_size', False),  # Use fixed position size or dynamic size
        ('start_position_size', 1),      # Initial position size as a percentage of total capital
        ('initial_risk_percent', 1.0),   # Initial position risk as a percentage of capital
        ('martingale_factor', 2.0),      # Multiplier for additional positions
        ('add_threshold_percent', 2.0),  # Price drop percentage to trigger additional positions
    )

    def __init__(self):
        self.current_unit_size = None    # Current position size for trades
        self.add_position_count = 0     # Number of additional positions taken
        self.macd = bt.indicators.MACD(self.data.close)  # MACD indicator for entry signals
        self.entry_price = None         # Initial entry price for the position
        self.exited = False  # Flag to prevent re-entry after exiting

    def next(self):
        # Entry logic: MACD crossover signal
        if not self.position and not self.exited:  # No current position
            if self.macd.macd[0] > self.macd.signal[0]:  # Bullish MACD crossover
                if self.params.fixed_position_size:
                    self.current_unit_size = self.params.start_position_size
                else:
                    self.current_unit_size = (self.broker.getvalue() * (self.params.initial_risk_percent / 100)) / self.data.close[0]
                self.buy(size=self.current_unit_size)
                self.entry_price = self.data.close[0]
                self.add_position_count = 0

        # Manage existing position
        elif self.position.size > 0:
            # Calculate price drop and gain percentages
            price_drop = (self.entry_price - self.data.close[0]) / self.entry_price * 100
            price_gain = (self.data.close[0] - self.entry_price) / self.entry_price * 100

            # Add position logic
            if price_drop >= self.params.add_threshold_percent:
                new_unit_size = self.position.size * self.params.martingale_factor
                if self.broker.getcash() >= new_unit_size * self.data.close[0]:
                    self.buy(size=new_unit_size)
                    self.add_position_count += 1

            # exit only if cash <= 0
            if self.broker.getcash() <= 0:
                self.close()
                self.exited = True

strategies = {
    "reverse": ReverseMartingaleStrategy,
    "multifactor": MultifactorMartingaleStrategy,
    "time_limited": TimeLimitedMartingaleStrategy,
    "risk_limited": RiskLimitedMartingaleStrategy,
}

market_strategies = {
    "Uptrend": ReverseMartingaleStrategy,
    "Ranging": MultifactorMartingaleStrategy,
    "High Volatility": TimeLimitedMartingaleStrategy,
    "Downtrend": RiskLimitedMartingaleStrategy,
}

def martingale(symbol, start_date, end_date, market_condition, capital):

    timezone = 'UTC'
    interval = Client.KLINE_INTERVAL_1MINUTE

    # Fetch Binance data
    raw_data = fetch_binance_data(symbol, interval, start_date, end_date, timezone)

    # Load data into backtrader
    class BinanceData(bt.feeds.PandasData):
        params = (
            ('datetime', 'datetime'),
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'volume')
        )

    df = pd.DataFrame(raw_data)
    data = BinanceData(dataname=df)

    # Create backtesting engine
    cerebro = bt.Cerebro()

    # Add chosen strategy
    strategy = market_strategies[market_condition]
    cerebro.addstrategy(strategy)

    # Add data
    cerebro.adddata(data)

    # Configure initial capital
    cerebro.broker.set_cash(capital)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Minutes, annualize=True)

    # Run backtest
    results = cerebro.run()

    sharpe_analyzer = results[0].analyzers.sharpe
    return cerebro.broker.getvalue(), sharpe_analyzer.get_analysis().get('sharperatio', 'N/A')