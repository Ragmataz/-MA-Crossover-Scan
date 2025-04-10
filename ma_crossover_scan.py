import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from datetime import date, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import telegram
import pytz
import os
import logging
import requests
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram setup
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY') #add this line

# Create directory for charts
if not os.path.exists('charts'):
    os.makedirs('charts')

def test_telegram_connection():
    # ... (same as before)

def send_telegram_message(message, photo_path=None):
    # ... (same as before)

def load_nse500_stocks():
    # ... (same as before)

def calculate_sma(data, length):
    """Calculate Simple Moving Average."""
    return data['Close'].rolling(window=length).mean()

def get_alpha_vantage_data(stock_symbol, start_date, end_date, interval='daily'):
    """Fetch stock data from Alpha Vantage."""
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        if interval == 'daily':
            data, meta_data = ts.get_daily(symbol=stock_symbol, outputsize='full')
        elif interval == 'weekly':
            data, meta_data = ts.get_weekly(symbol=stock_symbol)
        elif interval == 'monthly':
            data, meta_data = ts.get_monthly(symbol=stock_symbol)
        else:
            raise ValueError(f"Invalid interval: {interval}")

        data = data.loc[str(start_date):str(end_date)]
        data = data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'})
        return data

    except Exception as e:
        logger.error(f"Error fetching data from Alpha Vantage for {stock_symbol}: {e}")
        return None

def check_ma_crossover(stock_symbol, timeframe='1d'):
    """Check for MA crossover."""
    try:
        today = date.today()
        if timeframe == '1d':
            interval = 'daily'
            lookback_days = 100
        elif timeframe == '1wk':
            interval = 'weekly'
            lookback_days = 200 * 7 // 7  # Convert to weeks
        elif timeframe == '1mo':
            interval = 'monthly'
            lookback_days = 365 * 2 // 30 # Convert to months
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        start_date = today - timedelta(days=lookback_days)
        end_date = today

        data = get_alpha_vantage_data(stock_symbol, start_date, end_date, interval)

        if data is None or data.empty:
            logger.warning(f"No data retrieved for {stock_symbol} on {timeframe}")
            return None, None, None

        logger.info(f"Data retrieved for {stock_symbol} on {timeframe}:\n{data.head()}")
        sma_50 = calculate_sma(data, 50)
        logger.info(f"SMA 50 for {stock_symbol} on {timeframe}:\n{sma_50.head()}")

        if len(data) < 51:
            logger.warning(f"Not enough data for MA calculation: {stock_symbol} on {timeframe}")
            return None, None, None

        current_close = data['Close'].iloc[-1]
        previous_close = data['Close'].iloc[-2]
        current_sma = sma_50.iloc[-1]
        previous_sma = sma_50.iloc[-2]

        buy_signal = previous_close < previous_sma and current_close > current_sma
        sell_signal = previous_close > previous_sma and current_close < current_sma

        logger.info(f"{stock_symbol} {timeframe}: close_prev={previous_close}, close_curr={current_close}, sma_prev={previous_sma}, sma_curr={current_sma}")
        return buy_signal, sell_signal, data

    except Exception as e:
        logger.error(f"Error checking MA crossover for {stock_symbol} on {timeframe}: {str(e)}")
        return None, None, None

def generate_chart(stock_symbol, data, sma_50, timeframe='1d'):
    # ... (same as before)

def check_crossovers():
    # ... (same as before)
        for stock in stock_list:
            logger.info(f"processing stock: {stock}")
            if alerts_sent >= 30:
                break
            for timeframe in timeframes:
                buy_signal, sell_signal, data = check_ma_crossover(stock, timeframe)
                if buy_signal is None:
                    continue
                if buy_signal or sell_signal:
                    # ... (same as before)
            time.sleep(15) # Add a 15-second delay between stocks
    # ... (same as before)

if __name__ == "__main__":
    # ... (same as before)
