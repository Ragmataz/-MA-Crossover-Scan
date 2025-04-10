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
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')

# Create directory for charts
if not os.path.exists('charts'):
    os.makedirs('charts')

def test_telegram_connection():
    """Test the Telegram connection."""
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': "🔔 *TEST MESSAGE*\nMA Crossover system is online",
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=payload)
        result = response.json()
        if result.get('ok'):
            logger.info("Test message sent successfully")
            return True
        else:
            logger.error(f"Test message failed: {result.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Telegram test failed: {str(e)}")
        return False

def send_telegram_message(message, photo_path=None):
    """Send a message or photo to Telegram."""
    try:
        if photo_path:
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'caption': message,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, data=payload, files=files)
        else:
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=payload)

        result = response.json()
        if result.get('ok'):
            logger.info("Message sent successfully")
            return True
        else:
            logger.error(f"Failed to send message: {result.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
        return False

def load_nse500_stocks():
    """Load NSE500 stocks from CSV file."""
    try:
        df = pd.read_csv('nse500_stocks.csv')
        logger.info(f"Loaded {len(df)} stocks from CSV file")
        return [stock for stock in df['Symbol'].tolist()]  # Remove .NS
    except Exception as e:
        logger.error(f"Error loading NSE500 stocks: {str(e)}")
        logger.info("Using fallback stock list")
        return ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']

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
    """Generate chart with stock price and SMA."""
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(data.index, data['Close'], label='Close Price')
        plt.plot(sma_50.index, sma_50, label='50 SMA', color='red')

        timeframe_label = "Daily" if timeframe == '1d' else "Weekly" if timeframe == '1wk' else "Monthly"
        plt.title(f'{stock_symbol} {timeframe_label} Chart with 50 SMA')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        filename = f'charts/{stock_symbol.replace(".", "_")}_SMA_{timeframe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename)
        plt.close()

        return filename

    except Exception as e:
        logger.error(f"Error generating chart for {stock_symbol} on {timeframe}: {str(e)}")
        return None

def check_crossovers():
    """Check for MA crossovers."""
    IST = pytz.timezone('Asia/Kolkata')
    timeframes = ['1d', '1wk', '1mo']
    BUY_EMOJI = "🍏"
    SELL_EMOJI = "🔴"
    stock_list = load_nse500_stocks()
    alerts_sent = 0

    send_telegram_message(f"🔍 *MA Crossover Scan Started*\nProcessing {len(stock_list)} stocks across 3 timeframes...")

    for stock in stock_list:
        logger.info(f"processing stock: {stock}")
        if alerts_sent >= 30:
            break
        for timeframe in timeframes:
            buy_signal, sell_signal, data = check_ma_crossover(stock, timeframe)
            if buy_signal is None:
                continue
            if buy_signal or sell_signal:
                sma_50 = calculate_sma(data, 50)
                chart_path = generate_chart(stock, data, sma_50, timeframe)

                if chart_path:
                    timeframe_label = "Daily" if timeframe == '1d' else "Weekly" if timeframe == '1wk' else "Monthly"
                    if buy_signal:
                        message = f"{BUY_EMOJI} *{timeframe_label} BUY*: {stock}\n\n"
                        message += f"📅 Date: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}\n"
                        message += "📈 50 SMA Crossover (Above)"
                    else:
                        message = f"{SELL_EMOJI} *{timeframe_label} SELL*: {stock}\n\n"
                        message += f"📅 Date: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}\n"
                        message += "📉 50 SMA Crossover (Below)"

                    success = send_telegram_message(message, chart_path)
                    if success:
                        logger.info(f"Alert sent for {stock}: {timeframe_label} Crossover")
                        alerts_sent += 1
                    os.remove(chart_path)
            time.sleep(15) # Add a 15-second delay between stocks
    send_telegram_message(f"🔍 *MA Crossover Scan Complete*\nTotal alerts: {alerts_sent}")
    return alerts_sent

if __name__ == "__main__":
    logger.info("Starting MA crossover scan")
    if test_telegram_connection():
        alerts = check_crossovers()
        logger.info(f"Scan complete. {alerts} alerts sent.")
    else:
        logger.error("Telegram connection failed.")
